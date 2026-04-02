import MarkdownIt from 'markdown-it'
import taskLists from 'markdown-it-task-lists'

function mentionPlugin(md: MarkdownIt) {
  md.inline.ruler.push('mention_user', (state, silent) => {
    if (state.src.charCodeAt(state.pos) !== 0x40) return false
    if (state.src.charCodeAt(state.pos + 1) !== 0x5B) return false
    const match = state.src.slice(state.pos).match(/^@\[([^\]]+)\]\(user:(\d+)\)/)
    if (!match) return false
    if (!silent) {
      const token = state.push('mention_user', '', 0)
      token.content = match[1]
      token.meta = { id: match[2] }
    }
    state.pos += match[0].length
    return true
  })

  md.renderer.rules.mention_user = (tokens, idx) => {
    return `<span class="mention-user">@${tokens[idx].content}</span>`
  }

  md.inline.ruler.push('mention_issue', (state, silent) => {
    if (state.src.charCodeAt(state.pos) !== 0x23) return false
    if (state.src.charCodeAt(state.pos + 1) !== 0x5B) return false
    const match = state.src.slice(state.pos).match(/^#\[([^\]]+)\]\(issue:(\d+)\)/)
    if (!match) return false
    if (!silent) {
      const token = state.push('mention_issue', '', 0)
      token.content = match[1]
      token.meta = { id: match[2] }
    }
    state.pos += match[0].length
    return true
  })

  md.renderer.rules.mention_issue = (tokens, idx) => {
    const id = tokens[idx].meta.id
    const label = `#问题-${String(id).padStart(3, '0')}`
    return `<a href="/app/issues/${id}" class="mention-issue">${label}</a>`
  }
}

export function useMentionMarkdown() {
  const md = new MarkdownIt({ html: false, linkify: true })
    .use(taskLists, { enabled: true })
    .use(mentionPlugin)

  return { md, mentionPlugin }
}
