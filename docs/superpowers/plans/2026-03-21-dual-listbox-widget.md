# DualListbox Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the checkbox tag grid in the "组-权限" tab with a Django admin-style dual-listbox widget, keeping the old view as a fallback toggle.

**Architecture:** A reusable `DualListbox.vue` component handles the two-panel UI with filtering, selection, and transfer logic. The permissions page integrates it via v-model, converting between `Set<string>` and `string[]` at the boundary. No backend changes.

**Tech Stack:** Vue 3 Composition API, Tailwind CSS, Nuxt 4

**Spec:** `docs/superpowers/specs/2026-03-21-dual-listbox-widget-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/app/components/DualListbox.vue` | Create | Reusable dual-listbox component with filter, select, transfer |
| `frontend/app/pages/app/permissions.vue` | Modify (lines 83-112) | Integrate DualListbox + view mode toggle in groups tab |

---

## Task 1: Create DualListbox component — core structure and rendering

**Files:**
- Create: `frontend/app/components/DualListbox.vue`

- [ ] **Step 1: Create the component with props, emits, and computed lists**

```vue
<script setup lang="ts">
const props = defineProps<{
  items: string[]
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const leftFilter = ref('')
const rightFilter = ref('')
const leftHighlighted = ref<Set<string>>(new Set())
const rightHighlighted = ref<Set<string>>(new Set())
// Track last clicked index for shift-click range select
const leftLastClicked = ref<number>(-1)
const rightLastClicked = ref<number>(-1)

const selectedSet = computed(() => new Set(props.modelValue))

const availableItems = computed(() =>
  props.items.filter(i => !selectedSet.value.has(i)).sort()
)

const selectedItems = computed(() =>
  [...props.modelValue].sort()
)

const filteredAvailable = computed(() => {
  if (!leftFilter.value) return availableItems.value
  const q = leftFilter.value.toLowerCase()
  return availableItems.value.filter(i => i.toLowerCase().includes(q))
})

const filteredSelected = computed(() => {
  if (!rightFilter.value) return selectedItems.value
  const q = rightFilter.value.toLowerCase()
  return selectedItems.value.filter(i => i.toLowerCase().includes(q))
})
</script>
```

- [ ] **Step 2: Add the template with two panels, filter inputs, and item lists**

The template structure:
- Outer `div` with `flex` layout
- Left panel: header "可用权限", filter input, scrollable item list, "全部选择 N ⇨" link
- Center: two arrow buttons (→ ←)
- Right panel: header "选中的权限", filter input, scrollable item list, "⇦ 全部移除 N" link
- Items rendered as `<div>` elements with click/dblclick handlers
- Highlighted items get a blue background class
- Empty/no-match states show muted placeholder text

```html
<template>
  <div class="flex items-start gap-2">
    <!-- Left Panel: Available -->
    <div class="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
      <div class="bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300">
        可用权限
      </div>
      <div class="p-2">
        <input
          v-model="leftFilter"
          type="text"
          placeholder="过滤..."
          class="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded
                 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100
                 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div class="h-[250px] overflow-y-auto border-t border-gray-200 dark:border-gray-700">
        <div
          v-for="(item, index) in filteredAvailable"
          :key="item"
          class="px-3 py-1 text-xs font-mono cursor-pointer select-none"
          :class="leftHighlighted.has(item)
            ? 'bg-blue-600 text-white'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
          @click="handleItemClick('left', item, index, $event)"
          @dblclick="transferItems('right', [item])"
        >
          {{ item }}
        </div>
        <div v-if="leftFilter && filteredAvailable.length === 0" class="px-3 py-4 text-xs text-gray-400 text-center">
          无匹配项
        </div>
      </div>
      <div class="border-t border-gray-200 dark:border-gray-700 px-3 py-1.5">
        <button
          class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          @click="transferItems('right', filteredAvailable)"
        >
          全部选择 {{ filteredAvailable.length }} ⇨
        </button>
      </div>
    </div>

    <!-- Center Arrows -->
    <div class="flex flex-col items-center justify-center gap-2 pt-20">
      <button
        class="p-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100
               dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
        title="添加选中项"
        @click="transferItems('right', [...leftHighlighted])"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <button
        class="p-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100
               dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
        title="移除选中项"
        @click="transferItems('left', [...rightHighlighted])"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </div>

    <!-- Right Panel: Selected -->
    <div class="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
      <div class="bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300">
        选中的权限
      </div>
      <div class="p-2">
        <input
          v-model="rightFilter"
          type="text"
          placeholder="过滤..."
          class="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded
                 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100
                 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div class="h-[250px] overflow-y-auto border-t border-gray-200 dark:border-gray-700">
        <div
          v-for="(item, index) in filteredSelected"
          :key="item"
          class="px-3 py-1 text-xs font-mono cursor-pointer select-none"
          :class="rightHighlighted.has(item)
            ? 'bg-blue-600 text-white'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
          @click="handleItemClick('right', item, index, $event)"
          @dblclick="transferItems('left', [item])"
        >
          {{ item }}
        </div>
        <div v-if="rightFilter && filteredSelected.length === 0" class="px-3 py-4 text-xs text-gray-400 text-center">
          无匹配项
        </div>
      </div>
      <div class="border-t border-gray-200 dark:border-gray-700 px-3 py-1.5">
        <button
          class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          @click="transferItems('left', filteredSelected)"
        >
          ⇦ 全部移除 {{ filteredSelected.length }}
        </button>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Add interaction logic — click, shift-click, transfer**

```ts
function handleItemClick(side: 'left' | 'right', item: string, index: number, event: MouseEvent) {
  const highlighted = side === 'left' ? leftHighlighted : rightHighlighted
  const lastClicked = side === 'left' ? leftLastClicked : rightLastClicked
  const list = side === 'left' ? filteredAvailable.value : filteredSelected.value

  if (event.shiftKey && lastClicked.value >= 0) {
    // Range select
    const start = Math.min(lastClicked.value, index)
    const end = Math.max(lastClicked.value, index)
    const range = list.slice(start, end + 1)
    if (event.metaKey || event.ctrlKey) {
      range.forEach(i => highlighted.value.add(i))
    } else {
      highlighted.value = new Set(range)
    }
  } else if (event.metaKey || event.ctrlKey) {
    // Toggle single item
    if (highlighted.value.has(item)) {
      highlighted.value.delete(item)
    } else {
      highlighted.value.add(item)
    }
  } else {
    // Single select
    highlighted.value = new Set([item])
  }
  lastClicked.value = index
}

function transferItems(direction: 'left' | 'right', items: string[]) {
  if (items.length === 0) return
  const current = new Set(props.modelValue)
  if (direction === 'right') {
    // Move to selected
    items.forEach(i => current.add(i))
    leftHighlighted.value.clear()
  } else {
    // Move to available
    items.forEach(i => current.delete(i))
    rightHighlighted.value.clear()
  }
  emit('update:modelValue', [...current])
}
```

- [ ] **Step 4: Verify in browser**

Run: `cd frontend && npm run dev`
Open http://localhost:3004 — the component isn't integrated yet, but verify no build errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/components/DualListbox.vue
git commit -m "feat: add DualListbox component with filter, select, transfer"
```

---

## Task 2: Integrate DualListbox into permissions.vue groups tab

**Files:**
- Modify: `frontend/app/pages/app/permissions.vue` (lines 83-112 for template, lines 412-421 for script)

- [ ] **Step 1: Add view mode toggle ref and computed allPermissionNames**

In the `<script setup>` section, after the existing `activeTab` ref (around line 265), add:

```ts
const groupViewMode = ref<'listbox' | 'tags'>('listbox')
```

After the `permSelectOptions` computed (around line 299), add:

```ts
const allPermissionNames = computed(() =>
  allPermissions.value.map(p => p.full_codename)
)
```

- [ ] **Step 2: Add helper functions for Set/Array conversion**

Add this function near `toggleGroupPerm` (around line 415):

```ts
function updateGroupPerms(group: any, perms: string[]) {
  group._selectedPerms = new Set(perms)
}
```

- [ ] **Step 3: Replace the groups tab template**

Replace lines 83-112 (the `<!-- Tab 2: Group Permissions -->` section) with:

```html
<!-- Tab 2: Group Permissions -->
<div v-if="activeTab === 'groups'">
  <div class="flex items-center justify-between mb-4">
    <span class="text-sm text-gray-500 dark:text-gray-400">共 {{ groups.length }} 个组</span>
    <div class="flex items-center bg-gray-100 dark:bg-gray-800 rounded-md p-0.5">
      <button
        class="px-2.5 py-1 text-xs rounded transition-colors"
        :class="groupViewMode === 'listbox' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400'"
        @click="groupViewMode = 'listbox'"
      >
        列表模式
      </button>
      <button
        class="px-2.5 py-1 text-xs rounded transition-colors"
        :class="groupViewMode === 'tags' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400'"
        @click="groupViewMode = 'tags'"
      >
        标签模式
      </button>
    </div>
  </div>

  <div class="space-y-4">
    <div
      v-for="group in groups"
      :key="group.id"
      class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
    >
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ group.name }}</h3>
        <UButton size="xs" variant="outline" color="neutral" :loading="savingGroup === group.id" @click="saveGroup(group)">保存</UButton>
      </div>

      <!-- Listbox mode -->
      <DualListbox
        v-if="groupViewMode === 'listbox'"
        :items="allPermissionNames"
        :model-value="Array.from(group._selectedPerms)"
        @update:model-value="updateGroupPerms(group, $event)"
      />

      <!-- Tags mode (original) -->
      <div v-else class="flex flex-wrap gap-2">
        <label
          v-for="perm in allPermissions"
          :key="perm.full_codename"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs cursor-pointer transition-colors"
          :class="group._selectedPerms.has(perm.full_codename) ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800' : 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700'"
        >
          <input
            type="checkbox"
            class="sr-only"
            :checked="group._selectedPerms.has(perm.full_codename)"
            @change="toggleGroupPerm(group, perm.full_codename)"
          />
          {{ perm.full_codename }}
        </label>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Verify in browser**

Run: `cd frontend && npm run dev`
1. Open http://localhost:3004/app/permissions
2. Switch to "组-权限" tab
3. Verify DualListbox renders for each group with correct available/selected items
4. Test: click, ctrl+click, shift+click, double-click, arrow buttons, choose all, remove all
5. Test: filter inputs on both panels
6. Test: toggle to "标签模式" and back — old checkbox view still works
7. Test: save button still works
8. Test: dark mode

- [ ] **Step 5: Run typecheck**

```bash
cd frontend && npx nuxi typecheck
```

Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/pages/app/permissions.vue
git commit -m "feat: integrate DualListbox in groups tab with view mode toggle"
```
