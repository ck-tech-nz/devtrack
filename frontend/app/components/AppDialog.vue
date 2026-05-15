<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div v-if="state.open" class="dialog-overlay" @click.self="onOverlayClick" @keydown.esc="onEsc">
        <div class="dialog-panel" role="dialog" aria-modal="true" :aria-labelledby="state.title ? 'dialog-title' : undefined">
          <div class="dialog-body">
            <div v-if="state.icon" class="dialog-icon" :class="iconClass">
              <UIcon :name="state.icon" class="w-6 h-6" />
            </div>
            <div class="dialog-text">
              <h3 v-if="state.title" id="dialog-title" class="dialog-title">{{ state.title }}</h3>
              <p class="dialog-message">{{ state.message }}</p>
            </div>
          </div>
          <div class="dialog-footer">
            <UButton v-if="state.mode === 'confirm'" variant="outline" color="neutral" @click="cancel">
              {{ state.cancelText }}
            </UButton>
            <UButton ref="confirmBtnRef" :color="state.color" @click="ok">{{ state.confirmText }}</UButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const { state, _respond } = useDialog()

const iconClass = computed(() => `dialog-icon--${state.value.color}`)
const confirmBtnRef = ref<any>(null)

function ok() { _respond(true) }
function cancel() { _respond(false) }
function onOverlayClick() {
  // Mirror native confirm: clicking outside is treated as cancel for confirm,
  // and as confirm for alert (since alert has only one action).
  if (state.value.mode === 'alert') ok()
  else cancel()
}
function onEsc() {
  if (state.value.mode === 'alert') ok()
  else cancel()
}

// Global Esc listener (overlay only catches when focused)
function handleKey(e: KeyboardEvent) {
  if (!state.value.open) return
  if (e.key === 'Escape') {
    e.stopPropagation()
    onEsc()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKey, { capture: true })
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKey, { capture: true })
})

// Autofocus the confirm button when the dialog opens
watch(() => state.value.open, async (open) => {
  if (!open) return
  await nextTick()
  confirmBtnRef.value?.$el?.focus?.()
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background-color: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(2px);
}
:root.dark .dialog-overlay {
  background-color: rgba(0, 0, 0, 0.65);
}
.dialog-panel {
  width: 100%;
  max-width: 440px;
  background-color: #ffffff;
  border-radius: 0.875rem;
  box-shadow: 0 20px 50px -10px rgba(15, 23, 42, 0.35), 0 8px 16px -8px rgba(15, 23, 42, 0.2);
  padding: 1.5rem 1.75rem 1.25rem;
  outline: none;
}
:root.dark .dialog-panel {
  background-color: #1f2937;
  box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.6), 0 8px 16px -8px rgba(0, 0, 0, 0.4);
}
.dialog-body {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}
.dialog-icon {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dialog-icon--primary { background-color: #ede9fe; color: #7c3aed; }
.dialog-icon--error { background-color: #fee2e2; color: #dc2626; }
.dialog-icon--warning { background-color: #fef3c7; color: #d97706; }
.dialog-icon--success { background-color: #d1fae5; color: #059669; }
.dialog-icon--info { background-color: #dbeafe; color: #2563eb; }
.dialog-icon--neutral { background-color: #f3f4f6; color: #4b5563; }
:root.dark .dialog-icon--primary { background-color: rgba(124, 58, 237, 0.18); color: #a78bfa; }
:root.dark .dialog-icon--error { background-color: rgba(220, 38, 38, 0.18); color: #f87171; }
:root.dark .dialog-icon--warning { background-color: rgba(217, 119, 6, 0.18); color: #fbbf24; }
:root.dark .dialog-icon--success { background-color: rgba(5, 150, 105, 0.18); color: #34d399; }
:root.dark .dialog-icon--info { background-color: rgba(37, 99, 235, 0.18); color: #60a5fa; }
:root.dark .dialog-icon--neutral { background-color: rgba(75, 85, 99, 0.25); color: #d1d5db; }
.dialog-text {
  flex: 1;
  min-width: 0;
  padding-top: 0.125rem;
}
.dialog-title {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.375rem;
}
:root.dark .dialog-title {
  color: #f3f4f6;
}
.dialog-message {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #4b5563;
  white-space: pre-line;
}
:root.dark .dialog-message {
  color: #9ca3af;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.625rem;
  margin-top: 1.25rem;
}

.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.15s ease;
}
.dialog-enter-active .dialog-panel,
.dialog-leave-active .dialog-panel {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}
.dialog-enter-from .dialog-panel,
.dialog-leave-to .dialog-panel {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}
</style>
