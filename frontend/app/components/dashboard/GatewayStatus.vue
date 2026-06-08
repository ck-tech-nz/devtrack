<template>
  <div class="section-card">
    <!-- 头部:标题 + 过期角标 + 更新时间 -->
    <div class="section-header">
      <h3 class="section-title">
        电话线路状态
        <span v-if="stale" class="gw-stale" title="上游暂时不可达,展示的是上次数据">⚠ 数据可能过期</span>
      </h3>
      <span v-if="updatedText" class="gw-updated">{{ updatedText }}</span>
    </div>

    <!-- 未配置 -->
    <p v-if="!configured" class="gw-muted">未配置网关状态接口</p>

    <!-- 首拉加载中 -->
    <p v-else-if="loading && !lines.length" class="gw-muted">加载中…</p>

    <!-- 拉不到任何线路 -->
    <p v-else-if="!lines.length" class="gw-muted">暂时无法获取线路状态</p>

    <template v-else>
      <!-- 汇总条 -->
      <div class="gw-summary">
        <span><b :class="summary.offline ? 'gw-warn' : 'gw-ok'">{{ summary.online }}</b>/{{ summary.total }} 在线</span>
        <span>平均延迟 {{ summary.avgLatency }}ms</span>
        <span>今日呼叫 {{ summary.todayCalls }}</span>
        <span>接通率 {{ summary.answerRate }}%</span>
        <span>并发 {{ summary.activeCalls }}</span>
      </div>

      <!-- 离线/异常:始终展开高亮 -->
      <div v-if="offlineLines.length" class="gw-block">
        <div class="gw-block-label gw-warn">⚠ 离线 ({{ offlineLines.length }})</div>
        <ul class="gw-list">
          <li v-for="l in offlineLines" :key="l.name" class="gw-row gw-row--down">
            <span class="gw-dot gw-dot--down" />
            <span class="gw-name">{{ l.name }}</span>
            <span class="gw-addr">{{ l.proxy_ip_list }}:{{ l.port }}</span>
            <span class="gw-err">{{ l.ping_error || '无响应' }}</span>
            <span class="gw-time">{{ timeAgo(l.last_ping_at) }}</span>
          </li>
        </ul>
      </div>

      <!-- 正常线路:默认折叠 -->
      <div v-if="onlineLines.length" class="gw-block">
        <button type="button" class="gw-toggle" @click="showOnline = !showOnline">
          <UIcon :name="showOnline ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-right'" class="w-4 h-4" />
          正常线路 ({{ onlineLines.length }})
        </button>
        <ul v-if="showOnline" class="gw-list">
          <li v-for="l in onlineLines" :key="l.name" class="gw-row">
            <span class="gw-dot gw-dot--up" />
            <span class="gw-name">{{ l.name }}</span>
            <span class="gw-lat">{{ l.ping_latency_ms }}ms</span>
            <span class="gw-calls">今日 {{ l.today_calls }} · 接通 {{ Math.round(l.today_answer_rate) }}%</span>
            <span v-if="l.active_calls > 0" class="gw-active">并发 {{ l.active_calls }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { timeAgo } from '~/utils/timeAgo'

const { lines, configured, stale, fetchedAt, loading } = useGatewayStatus()
const showOnline = ref(false)

const updatedText = computed(() => {
  if (!fetchedAt.value) return ''
  const t = timeAgo(fetchedAt.value)
  return t ? `更新于 ${t}` : ''
})

// 离线置顶按名称排序;在线按今日呼叫量降序(忙线优先)
const offlineLines = computed(() =>
  lines.value.filter(l => !l.online).slice().sort((a, b) => a.name.localeCompare(b.name)),
)
const onlineLines = computed(() =>
  lines.value.filter(l => l.online).slice().sort((a, b) => b.today_calls - a.today_calls),
)

const summary = computed(() => {
  const all = lines.value
  const ups = onlineLines.value
  const total = all.length
  const online = ups.length
  const offline = offlineLines.value.length
  const avgLatency = ups.length
    ? Math.round(ups.reduce((s, l) => s + (l.ping_latency_ms || 0), 0) / ups.length)
    : 0
  const todayCalls = all.reduce((s, l) => s + (l.today_calls || 0), 0)
  const todayAnswered = all.reduce((s, l) => s + (l.today_answered || 0), 0)
  const activeCalls = all.reduce((s, l) => s + (l.active_calls || 0), 0)
  const answerRate = todayCalls ? Math.round((todayAnswered / todayCalls) * 100) : 0
  return { total, online, offline, avgLatency, todayCalls, answerRate, activeCalls }
})
</script>

<style scoped>
/* 卡片/标题样式与 ServerResource.vue 保持一致(scoped,故本组件内自带一份) */
.section-card {
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.25rem;
}
:root.dark .section-card { background-color: #1f2937; border-color: #374151; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.section-title { font-size: 0.875rem; font-weight: 600; color: #111827; display: flex; align-items: center; gap: 0.5rem; }
:root.dark .section-title { color: #f3f4f6; }
.gw-stale { font-size: 0.6875rem; font-weight: 500; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 0.375rem; padding: 0.0625rem 0.375rem; }
:root.dark .gw-stale { color: #fbbf24; background: rgba(251, 191, 36, 0.1); border-color: rgba(251, 191, 36, 0.3); }
.gw-updated { font-size: 0.75rem; color: #9ca3af; }
.gw-muted { font-size: 0.8125rem; color: #9ca3af; padding: 0.25rem 0; }

.gw-summary { display: flex; flex-wrap: wrap; gap: 0.25rem 1.25rem; font-size: 0.8125rem; color: #4b5563; margin-bottom: 0.875rem; }
:root.dark .gw-summary { color: #d1d5db; }
.gw-ok { color: #059669; }
.gw-warn { color: #dc2626; }
:root.dark .gw-ok { color: #34d399; }
:root.dark .gw-warn { color: #f87171; }

.gw-block { margin-top: 0.75rem; }
.gw-block-label { font-size: 0.75rem; font-weight: 600; margin-bottom: 0.375rem; }
.gw-toggle { display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.8125rem; font-weight: 500; color: #4b5563; background: transparent; border: 0; cursor: pointer; padding: 0.25rem 0; }
:root.dark .gw-toggle { color: #d1d5db; }
.gw-toggle:hover { color: #7c3aed; }
:root.dark .gw-toggle:hover { color: #c4b5fd; }

.gw-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.25rem; }
.gw-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: #374151; padding: 0.25rem 0.5rem; border-radius: 0.375rem; }
:root.dark .gw-row { color: #d1d5db; }
.gw-row--down { background: #fef2f2; }
:root.dark .gw-row--down { background: rgba(220, 38, 38, 0.1); }
.gw-dot { width: 0.5rem; height: 0.5rem; border-radius: 9999px; flex-shrink: 0; }
.gw-dot--up { background: #10b981; }
.gw-dot--down { background: #ef4444; }
.gw-name { font-weight: 500; }
.gw-addr, .gw-time { color: #9ca3af; font-size: 0.75rem; }
.gw-err { color: #dc2626; font-size: 0.75rem; }
:root.dark .gw-err { color: #f87171; }
.gw-lat, .gw-calls { color: #6b7280; font-size: 0.75rem; }
:root.dark .gw-lat, :root.dark .gw-calls { color: #9ca3af; }
.gw-active { color: #7c3aed; font-size: 0.75rem; font-weight: 500; margin-left: auto; }
:root.dark .gw-active { color: #c4b5fd; }
</style>
