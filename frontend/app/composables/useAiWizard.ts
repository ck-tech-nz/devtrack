type WizardState = 'idle' | 'analyzing' | 'drafting' | 'error'

type StepStatus = 'pending' | 'running' | 'done' | 'error'

type StepProgress = {
  step: 1 | 2 | 3
  label: string
  status: StepStatus
}

export type WizardDraft = {
  title: string
  description: string
  repro_steps: string
  expected_behavior: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  module: string
  labels: string[]
  follow_up_questions: string[]
  inferred_env: string
}

export type AttachmentRef = { id: string; file_name: string; file_url: string }

export type Turn =
  | { id: string; role: 'user'; text: string; attachments: AttachmentRef[] }
  | {
      id: string
      role: 'ai-thinking'
      kind: 'initial' | 'revise'
      steps: StepProgress[]
      errorMessage: string
      /** AI 判定用户意图; submit 时 UI 把 brand status 显示为"已确认,提交中" */
      intent?: 'update' | 'submit'
    }
  | { id: string; role: 'ai-draft'; version: number; draft: WizardDraft; attachmentIds: string[] }

const INITIAL_STEPS_INITIAL: StepProgress[] = [
  { step: 1, label: 'AI 正在理解描述与截图', status: 'pending' },
]
const INITIAL_STEPS_REVISE: StepProgress[] = [
  { step: 1, label: 'AI 正在更新草稿', status: 'pending' },
]

const STORAGE_KEY = 'ai-wizard:turns'
const MAX_TURNS = 60   // 60 个 turn (含 user/thinking/draft) 大约 20 轮对话, 足够多
const STORAGE_CAP_BYTES = 64 * 1024  // 单 key 不超过 64KB; LocalStorage 单域 5MB 配额

async function refreshAccessToken(): Promise<string | null> {
  if (typeof localStorage === 'undefined') return null
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return null
  try {
    const resp = await fetch('/api/auth/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!resp.ok) return null
    const data = await resp.json()
    if (data?.access) {
      localStorage.setItem('access_token', data.access)
      return data.access
    }
  } catch {
    return null
  }
  return null
}

async function getValidAccessToken(): Promise<string | null> {
  if (typeof localStorage === 'undefined') return null
  const token = localStorage.getItem('access_token')
  if (!token) return null
  try {
    const segments = token.split('.')
    if (segments.length >= 2 && segments[1]) {
      const payload = JSON.parse(atob(segments[1]))
      const expMs = payload.exp * 1000
      if (expMs - Date.now() < 60_000) {
        return await refreshAccessToken()
      }
    }
  } catch {
    // 令牌格式异常 — 继续使用,服务端 401 触发再刷新
  }
  return token
}

function genId(): string {
  // 简单单调 ID, 不需要 UUID 强度; thread 内部 :key 用
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

export function useAiWizard() {
  const state = ref<WizardState>('idle')
  const turns = ref<Turn[]>([])
  const errorMessage = ref<string>('')
  // LLM 判定用户在确认时, 递增此 counter; 父组件 watch 它触发 StepDraft.triggerSubmit
  const submitIntentCounter = ref(0)

  let abortController: AbortController | null = null

  // ---------- LocalStorage 持久化 ----------
  // 挂载时 restore (仅在 idle 状态有效, 避免覆盖正在进行的流)
  if (typeof window !== 'undefined') {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
          // 把任何残留的 ai-thinking running 状态降级为 error, 防止 UI 永远转圈
          turns.value = parsed.map((t: any) => {
            if (t?.role === 'ai-thinking' && Array.isArray(t.steps)) {
              return {
                ...t,
                steps: t.steps.map((s: any) =>
                  s.status === 'running' || s.status === 'pending' ? { ...s, status: 'error' } : s,
                ),
                errorMessage: t.errorMessage || (t.steps.some((s: any) => s.status === 'running') ? '页面刷新中断' : ''),
              }
            }
            return t
          })
          if (turns.value.length) state.value = 'drafting'
        }
      }
    } catch {
      // 损坏的 JSON, 静默清除
      try { localStorage.removeItem(STORAGE_KEY) } catch {}
    }

    // 任何 turns 变化都 debounced 写回 (200ms)
    let persistTimer: ReturnType<typeof setTimeout> | null = null
    watch(turns, (v) => {
      if (persistTimer) clearTimeout(persistTimer)
      persistTimer = setTimeout(() => {
        try {
          // 超出上限时截断最早的 turns; 保留最近 MAX_TURNS 个
          let payload = v.slice(-MAX_TURNS)
          let serialized = JSON.stringify(payload)
          // 极端情况下单个 turn 内容过大, 二分截到 cap 以下
          while (serialized.length > STORAGE_CAP_BYTES && payload.length > 1) {
            payload = payload.slice(Math.floor(payload.length / 2))
            serialized = JSON.stringify(payload)
          }
          if (serialized.length <= STORAGE_CAP_BYTES) {
            localStorage.setItem(STORAGE_KEY, serialized)
          }
        } catch {
          // 配额满 / 隐私模式 - 静默
        }
      }, 200)
    }, { deep: true })
  }

  // ---------- 基础 reducers ----------
  function appendTurn(turn: Turn) {
    turns.value.push(turn)
  }

  function reset() {
    state.value = 'idle'
    turns.value = []
    errorMessage.value = ''
    abortController?.abort()
    abortController = null
    if (typeof window !== 'undefined') {
      try { localStorage.removeItem(STORAGE_KEY) } catch {}
    }
  }

  function abort() {
    abortController?.abort()
    abortController = null
  }

  // ---------- 派生 ----------
  const latestDraft = computed<{ turn: Turn & { role: 'ai-draft' }; index: number } | null>(() => {
    for (let i = turns.value.length - 1; i >= 0; i--) {
      const t = turns.value[i]
      if (t && t.role === 'ai-draft') return { turn: t as Turn & { role: 'ai-draft' }, index: i }
    }
    return null
  })
  const draft = computed<WizardDraft | null>(() => latestDraft.value?.turn.draft || null)
  const draftVersion = computed<number>(() => latestDraft.value?.turn.version || 0)

  // ---------- SSE 共享解析 ----------
  type FrameOutcome = { kind: 'draft'; draft: WizardDraft } | { kind: 'submit' } | null

  function applyFrameToThinkingTurn(thinking: Turn & { role: 'ai-thinking' }, event: string, payload: any): FrameOutcome {
    if (event === 'step') {
      const s = thinking.steps.find(x => x.step === payload.step)
      if (s) s.status = (payload.status as StepStatus) || 'done'
      // 若服务端给了新的 label (例如 revise 用 "AI 正在更新草稿"), 同步过来
      if (s && payload.label) s.label = payload.label
    } else if (event === 'draft') {
      thinking.intent = 'update'
      return { kind: 'draft', draft: payload as WizardDraft }
    } else if (event === 'submit') {
      thinking.intent = 'submit'
      // 把 thinking 步骤标完成
      for (const s of thinking.steps) {
        if (s.status === 'running' || s.status === 'pending') s.status = 'done'
      }
      return { kind: 'submit' }
    } else if (event === 'error') {
      const s = thinking.steps.find(x => x.step === payload.step)
      if (s) s.status = 'error'
      thinking.errorMessage = payload.message || 'AI 分析失败'
      state.value = 'error'
      errorMessage.value = thinking.errorMessage
    }
    return null
  }

  async function consumeSseStream(
    resp: Response,
    thinkingTurn: Turn & { role: 'ai-thinking' },
    onDraft: (d: WizardDraft, attachmentIds: string[]) => void,
    attachmentIds: string[],
  ) {
    const reader = resp.body!.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let gotTerminal = false   // draft 或 submit 任一发生即视为已收到终态

    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          // Parse SSE frame
          const lines = frame.split('\n')
          let event = 'message'
          let data = ''
          for (const ln of lines) {
            if (ln.startsWith('event:')) event = ln.slice(6).trim()
            else if (ln.startsWith('data:')) data = ln.slice(5).trim()
          }
          if (!data) continue
          let payload: any
          try { payload = JSON.parse(data) } catch { continue }
          const outcome = applyFrameToThinkingTurn(thinkingTurn, event, payload)
          if (outcome?.kind === 'draft') {
            gotTerminal = true
            onDraft(outcome.draft, attachmentIds)
          } else if (outcome?.kind === 'submit') {
            gotTerminal = true
            state.value = 'drafting'
            submitIntentCounter.value++
          }
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        state.value = 'error'
        errorMessage.value = e?.message || '流读取失败'
        thinkingTurn.errorMessage = errorMessage.value
        const running = thinkingTurn.steps.find(s => s.status === 'running' || s.status === 'pending')
        if (running) running.status = 'error'
      }
    }

    if (!gotTerminal && state.value === 'analyzing') {
      state.value = 'error'
      errorMessage.value = '分析中断，请重试'
      thinkingTurn.errorMessage = errorMessage.value
    }
  }

  // ---------- start (首发或重描述后的第一条) ----------
  async function start(params: { description: string; project: string; attachment_ids?: string[]; attachments?: AttachmentRef[] }) {
    // 首发清空 thread (重描述也会先走 reset 再 start)
    reset()
    state.value = 'analyzing'
    errorMessage.value = ''
    abortController = new AbortController()

    // 1) 追加 user turn
    appendTurn({
      id: genId(),
      role: 'user',
      text: params.description,
      attachments: params.attachments || [],
    })
    // 2) 追加 thinking turn (initial kind)
    const thinking: Turn & { role: 'ai-thinking' } = {
      id: genId(),
      role: 'ai-thinking',
      kind: 'initial',
      steps: structuredClone(INITIAL_STEPS_INITIAL),
      errorMessage: '',
    }
    appendTurn(thinking)

    let token = await getValidAccessToken()
    let resp: Response
    try {
      resp = await doFetch('/api/issues/ai-draft/', token, {
        description: params.description,
        project: params.project,
        attachment_ids: params.attachment_ids || [],
      })
      if (resp.status === 401) {
        token = await refreshAccessToken()
        if (token) {
          resp = await doFetch('/api/issues/ai-draft/', token, {
            description: params.description,
            project: params.project,
            attachment_ids: params.attachment_ids || [],
          })
        }
      }
    } catch (e: any) {
      state.value = 'error'
      errorMessage.value = e?.message || '网络错误，请重试'
      thinking.errorMessage = errorMessage.value
      thinking.steps[0]!.status = 'error'
      return
    }

    if (!resp.ok || !resp.body) {
      state.value = 'error'
      errorMessage.value = `请求失败 (${resp.status})`
      thinking.errorMessage = errorMessage.value
      thinking.steps[0]!.status = 'error'
      return
    }

    await consumeSseStream(resp, thinking, (newDraft, attIds) => {
      appendTurn({
        id: genId(),
        role: 'ai-draft',
        version: 1,
        draft: newDraft,
        attachmentIds: attIds,
      })
      state.value = 'drafting'
    }, params.attachment_ids || [])
  }

  // ---------- revise (基于现有 draft 多轮修订) ----------
  async function revise(params: { instruction: string; project: string; attachment_ids?: string[]; attachments?: AttachmentRef[] }) {
    const last = latestDraft.value
    if (!last) {
      // 没有基础 draft, 不该被调到; 调用方应该走 start
      return start({
        description: params.instruction,
        project: params.project,
        attachment_ids: params.attachment_ids,
        attachments: params.attachments,
      })
    }

    state.value = 'analyzing'
    errorMessage.value = ''
    abortController?.abort()
    abortController = new AbortController()

    // 追加 user + ai-thinking(revise kind)
    appendTurn({
      id: genId(),
      role: 'user',
      text: params.instruction,
      attachments: params.attachments || [],
    })
    const thinking: Turn & { role: 'ai-thinking' } = {
      id: genId(),
      role: 'ai-thinking',
      kind: 'revise',
      steps: structuredClone(INITIAL_STEPS_REVISE),
      errorMessage: '',
    }
    appendTurn(thinking)

    let token = await getValidAccessToken()
    let resp: Response
    const body = {
      current_draft: last.turn.draft,
      instruction: params.instruction,
      project: params.project,
      attachment_ids: params.attachment_ids || [],
    }
    try {
      resp = await doFetch('/api/issues/ai-draft/revise/', token, body)
      if (resp.status === 401) {
        token = await refreshAccessToken()
        if (token) resp = await doFetch('/api/issues/ai-draft/revise/', token, body)
      }
    } catch (e: any) {
      state.value = 'error'
      errorMessage.value = e?.message || '网络错误，请重试'
      thinking.errorMessage = errorMessage.value
      thinking.steps[0]!.status = 'error'
      return
    }

    if (!resp.ok || !resp.body) {
      state.value = 'error'
      errorMessage.value = `请求失败 (${resp.status})`
      thinking.errorMessage = errorMessage.value
      thinking.steps[0]!.status = 'error'
      return
    }

    const prevVersion = last.turn.version
    await consumeSseStream(resp, thinking, (newDraft, attIds) => {
      appendTurn({
        id: genId(),
        role: 'ai-draft',
        version: prevVersion + 1,
        draft: newDraft,
        attachmentIds: attIds,
      })
      state.value = 'drafting'
    }, params.attachment_ids || [])
  }

  // ---------- 通用 doFetch ----------
  async function doFetch(url: string, token: string | null, body: any): Promise<Response> {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal: abortController!.signal,
    })
  }

  // ---------- 局部 mutators (供 UI 在用户编辑草稿时用) ----------
  function updateDraftInPlace(turnId: string, patch: Partial<WizardDraft>) {
    const t = turns.value.find(x => x.id === turnId)
    if (t && t.role === 'ai-draft') {
      t.draft = { ...t.draft, ...patch }
    }
  }

  /** 追加一条 user turn 但不触发 LLM (供 affirmative auto-submit 快捷路径用) */
  function appendUserTurn(text: string, attachments: AttachmentRef[] = []) {
    appendTurn({
      id: genId(),
      role: 'user',
      text,
      attachments,
    })
  }

  return {
    state,
    turns,
    draft,           // 向后兼容: 等同 latestDraft.draft
    draftVersion,
    latestDraft,
    errorMessage,
    start,
    revise,
    reset,
    abort,
    updateDraftInPlace,
    appendUserTurn,
    submitIntentCounter,
  }
}
