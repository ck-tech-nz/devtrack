<template>
  <div class="markdown-view" v-html="html" />
</template>

<script setup lang="ts">
const props = defineProps<{ text?: string }>()

const { md } = useMentionMarkdown()

const html = computed(() => {
  if (!props.text) return ''
  return md.render(props.text)
    .replace(/<input class="task-list-item-checkbox" checked=""type="checkbox">/g, '<span class="md-checkbox md-checked"></span>')
    .replace(/<input class="task-list-item-checkbox"type="checkbox">/g, '<span class="md-checkbox"></span>')
})
</script>

<style>
/* 只读 Markdown 渲染（与 MarkdownEditor 预览风格一致；自带样式，随本组件按需加载） */
.markdown-view { font-size: 0.875rem; line-height: 1.6; color: #374151; }
:root.dark .markdown-view { color: #d1d5db; }
.markdown-view > :first-child { margin-top: 0; }
.markdown-view > :last-child { margin-bottom: 0; }
.markdown-view h1 { font-size: 1.4em; font-weight: 700; margin: 0.67em 0; }
.markdown-view h2 { font-size: 1.2em; font-weight: 600; margin: 0.75em 0; }
.markdown-view h3 { font-size: 1.05em; font-weight: 600; margin: 0.9em 0 0.4em; }
.markdown-view h4 { font-size: 1em; font-weight: 600; margin: 0.8em 0 0.3em; }
.markdown-view p { margin: 0.5em 0; }
.markdown-view ul { margin: 0.4em 0; padding-left: 1.5em; list-style-type: disc; }
.markdown-view ol { margin: 0.4em 0; padding-left: 1.5em; list-style-type: decimal; }
.markdown-view li { margin: 0.2em 0; }
.markdown-view strong { font-weight: 600; color: #111827; }
:root.dark .markdown-view strong { color: #f3f4f6; }
.markdown-view em { font-style: italic; }
.markdown-view code { background: #f3f4f6; padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.875em; }
:root.dark .markdown-view code { background: #1f2937; }
.markdown-view pre { background: #f3f4f6; padding: 0.85em; border-radius: 6px; overflow-x: auto; margin: 0.5em 0; }
:root.dark .markdown-view pre { background: #1f2937; }
.markdown-view pre code { background: none; padding: 0; }
.markdown-view blockquote { border-left: 3px solid #d1d5db; padding-left: 0.85em; color: #6b7280; margin: 0.5em 0; }
:root.dark .markdown-view blockquote { border-left-color: #4b5563; color: #9ca3af; }
.markdown-view a { color: #2563eb; text-decoration: none; }
.markdown-view a:hover { text-decoration: underline; }
:root.dark .markdown-view a { color: #60a5fa; }
.markdown-view hr { border: none; border-top: 1px solid #e5e7eb; margin: 1em 0; }
:root.dark .markdown-view hr { border-top-color: #374151; }
.markdown-view table { border-collapse: collapse; margin: 0.5em 0; }
.markdown-view th, .markdown-view td { border: 1px solid #d1d5db; padding: 0.4em 0.6em; }
:root.dark .markdown-view th, :root.dark .markdown-view td { border-color: #4b5563; }
.markdown-view img { max-width: 100%; border-radius: 6px; margin: 0.5em 0; }
</style>
