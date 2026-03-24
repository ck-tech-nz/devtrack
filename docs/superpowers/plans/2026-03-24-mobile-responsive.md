# Mobile Responsive Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DevTrack fully usable on mobile devices (<768px) with a bottom tab bar, card-based content, and Apple Liquid Glass styling.

**Architecture:** Hide the sidebar on mobile, add a fixed bottom tab bar with 4 tabs (Issues, 概览, GitHub, 更多), replace the issues table with a card list view, and make forms stack to single column. All changes are CSS-breakpoint-driven using Tailwind's `md` (768px) breakpoint. No backend changes.

**Tech Stack:** Nuxt 4, Nuxt UI 3, Tailwind CSS 4, Vue 3 composables

**Spec:** `docs/superpowers/specs/2026-03-24-mobile-responsive-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/nuxt.config.ts` | Modify | Add viewport meta tag |
| `frontend/app/composables/useMobile.ts` | Create | Reactive `isMobile` composable using `matchMedia` |
| `frontend/app/components/AppBottomTabBar.vue` | Create | Bottom tab bar with liquid glass styling |
| `frontend/app/components/MobileMoreSheet.vue` | Create | Slide-up sheet for "更多" tab overflow nav items |
| `frontend/app/components/IssueCard.vue` | Create | Glass card component for issue list items |
| `frontend/app/components/AppSidebar.vue` | Modify | Hide on mobile |
| `frontend/app/layouts/default.vue` | Modify | Add tab bar, adjust padding |
| `frontend/app/components/AppHeader.vue` | Modify | Hide breadcrumbs on mobile |
| `frontend/app/pages/app/issues/index.vue` | Modify | Card view on mobile, responsive form grid |
| `frontend/app/pages/app/issues/[id].vue` | Modify | Responsive form grid |
| `frontend/app/pages/app/projects/[id].vue` | Modify | Responsive form grid (if applicable) |

---

### Task 1: Viewport Meta Tag & Mobile Composable

**Files:**
- Modify: `frontend/nuxt.config.ts:11-18`
- Create: `frontend/app/composables/useMobile.ts`

- [ ] **Step 1: Add viewport meta tag to nuxt.config.ts**

In `frontend/nuxt.config.ts`, add a `meta` array inside `app.head`:

```ts
app: {
  baseURL: '/',
  head: {
    title: 'DevTrakr - 项目管理平台',
    meta: [
      { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
    ],
    link: [
      { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
    ],
  },
},
```

`viewport-fit=cover` enables `env(safe-area-inset-bottom)` for notched iPhones.

- [ ] **Step 2: Create useMobile composable**

Create `frontend/app/composables/useMobile.ts`:

```ts
export const useMobile = () => {
  const isMobile = ref(false)

  if (import.meta.client) {
    const mql = window.matchMedia('(max-width: 767px)')
    isMobile.value = mql.matches
    const handler = (e: MediaQueryListEvent) => { isMobile.value = e.matches }
    mql.addEventListener('change', handler)
    onScopeDispose(() => mql.removeEventListener('change', handler))
  }

  return { isMobile }
}
```

This avoids adding VueUse as a dependency (not currently installed). Uses `import.meta.client` guard since Nuxt is SPA-only but the guard is good practice.

- [ ] **Step 3: Verify dev server still starts**

Run: `cd frontend && npm run dev`

Expected: Dev server starts on :3000 without errors. Check browser console for no warnings about viewport.

- [ ] **Step 4: Commit**

```bash
git add frontend/nuxt.config.ts frontend/app/composables/useMobile.ts
git commit -m "feat(mobile): add viewport meta tag and useMobile composable"
```

---

### Task 2: Hide Sidebar on Mobile & Adjust Layout

**Files:**
- Modify: `frontend/app/components/AppSidebar.vue:2-4`
- Modify: `frontend/app/layouts/default.vue:2-6`

- [ ] **Step 1: Hide sidebar on mobile**

In `frontend/app/components/AppSidebar.vue`, change the root `<aside>` opening tag from:

```html
<aside
  class="h-screen bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col transition-all duration-300 ease-in-out flex-shrink-0 relative z-30"
```

to:

```html
<aside
  class="h-screen bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 hidden md:flex flex-col transition-all duration-300 ease-in-out flex-shrink-0 relative z-30"
```

The `hidden md:flex` hides the sidebar below 768px and shows it as flexbox above. `hidden` removes it from flow entirely — no layout adjustments needed in the parent.

- [ ] **Step 2: Adjust layout main padding**

In `frontend/app/layouts/default.vue`, change the `<main>` element from:

```html
<main class="flex-1 overflow-y-auto overscroll-contain p-6 lg:p-8">
```

to:

```html
<main class="flex-1 overflow-y-auto overscroll-contain p-3 md:p-6 lg:p-8 pb-20 md:pb-6 lg:pb-8">
```

- `p-3` on mobile gives more content width (was `p-6` = 48px total, now `p-3` = 24px total)
- `pb-20` reserves space for the bottom tab bar on mobile (52px bar + safe area + breathing room)
- `md:pb-6` restores normal bottom padding on desktop

- [ ] **Step 3: Verify on desktop**

Open the app at http://localhost:3000/app/issues in a full-width browser window. Confirm the sidebar and layout look exactly the same as before. The sidebar should be visible, padding should be the same.

- [ ] **Step 4: Verify on mobile**

In Chrome DevTools, toggle device toolbar (iPhone 12 Pro, 390px). Confirm:
- Sidebar is completely gone
- Content takes full width
- Extra padding at bottom is visible (for future tab bar)

- [ ] **Step 5: Commit**

```bash
git add frontend/app/components/AppSidebar.vue frontend/app/layouts/default.vue
git commit -m "feat(mobile): hide sidebar on mobile, adjust layout padding"
```

---

### Task 3: Bottom Tab Bar Component

**Files:**
- Create: `frontend/app/components/AppBottomTabBar.vue`
- Modify: `frontend/app/layouts/default.vue`

- [ ] **Step 1: Create AppBottomTabBar.vue**

Create `frontend/app/components/AppBottomTabBar.vue`:

```vue
<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-40 md:hidden
           bg-white/55 dark:bg-slate-900/65
           backdrop-blur-[20px] backdrop-saturate-[180%]
           border-t border-white/60 dark:border-white/[0.08]
           shadow-[0_-2px_20px_rgba(0,0,0,0.05)] dark:shadow-[0_-2px_20px_rgba(0,0,0,0.3)]"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <div class="flex items-center justify-around h-[52px]">
      <NuxtLink
        v-for="tab in primaryTabs"
        :key="tab.to"
        :to="tab.to"
        class="flex flex-col items-center justify-center min-w-[64px] h-[44px] gap-0.5"
        :class="isActive(tab.to) ? 'text-crystal-600 dark:text-crystal-400' : 'text-gray-400 dark:text-gray-500'"
      >
        <div
          class="w-7 h-7 flex items-center justify-center rounded-lg transition-colors"
          :class="isActive(tab.to) ? 'bg-crystal-600/12' : ''"
        >
          <UIcon :name="tab.icon" class="w-6 h-6" />
        </div>
        <span class="text-[10px] leading-tight">{{ tab.label }}</span>
      </NuxtLink>

      <button
        class="flex flex-col items-center justify-center min-w-[64px] h-[44px] gap-0.5"
        :class="moreOpen ? 'text-crystal-600 dark:text-crystal-400' : 'text-gray-400 dark:text-gray-500'"
        @click="moreOpen = true"
      >
        <div
          class="w-7 h-7 flex items-center justify-center rounded-lg transition-colors"
          :class="moreOpen ? 'bg-crystal-600/12' : ''"
        >
          <UIcon name="i-heroicons-ellipsis-horizontal" class="w-6 h-6" />
        </div>
        <span class="text-[10px] leading-tight">更多</span>
      </button>
    </div>

    <MobileMoreSheet v-model:open="moreOpen" :items="moreItems" />
  </nav>
</template>

<script setup lang="ts">
import type { NavItem } from '~/composables/useNavigation'

const { filteredNavItems, currentPath } = useNavigation()

const primaryRoutes = ['/app/issues', '/app/dashboard', '/app/repos']

const primaryTabs = computed(() => {
  const tabs: NavItem[] = []
  for (const route of primaryRoutes) {
    const item = filteredNavItems.value.find(i => i.to === route)
    if (item) tabs.push(item)
  }
  return tabs
})

const moreItems = computed(() =>
  filteredNavItems.value.filter(item => item.to && !primaryRoutes.includes(item.to))
)

const moreOpen = ref(false)

function isActive(to: string) {
  return currentPath.value === to || currentPath.value.startsWith(to + '/')
}
</script>
```

Key design points:
- `md:hidden` — only visible on mobile
- Tab items derived dynamically from `filteredNavItems` (permission-filtered)
- Primary routes hardcoded as ordered constants, matched against dynamic items
- `env(safe-area-inset-bottom)` handles iPhone notch/home indicator
- Touch targets: each tab is `min-w-[64px] h-[44px]` (meets Apple HIG 44pt minimum)

- [ ] **Step 2: Add tab bar to layout**

In `frontend/app/layouts/default.vue`, add `<AppBottomTabBar />` after the closing `</div>` of the flex container, before `</template>`:

```vue
<template>
  <div class="flex h-screen bg-gray-50/50 dark:bg-gray-950">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-y-auto overscroll-contain p-3 md:p-6 lg:p-8 pb-20 md:pb-6 lg:pb-8">
        <slot />
      </main>
    </div>
  </div>
  <AppBottomTabBar />
</template>
```

Note: `AppBottomTabBar` is placed outside the flex container since it's `position: fixed`.

- [ ] **Step 3: Verify tab bar shows on mobile only**

In Chrome DevTools mobile view (390px):
- Tab bar should appear at bottom with 4 items
- Tab bar should have frosted glass effect
- Tapping "Issues" / "概览" / "GitHub" navigates correctly
- Active tab is highlighted with crystal color

In full-width desktop:
- Tab bar should NOT be visible

- [ ] **Step 4: Commit**

```bash
git add frontend/app/components/AppBottomTabBar.vue frontend/app/layouts/default.vue
git commit -m "feat(mobile): add bottom tab bar with liquid glass styling"
```

---

### Task 4: More Sheet Component

**Files:**
- Create: `frontend/app/components/MobileMoreSheet.vue`

- [ ] **Step 1: Create MobileMoreSheet.vue**

Create `frontend/app/components/MobileMoreSheet.vue`:

```vue
<template>
  <UDrawer
    :open="open"
    :ui="{
      content: 'bg-white/80 dark:bg-slate-900/80 backdrop-blur-[20px] backdrop-saturate-[180%]',
      overlay: 'bg-black/30',
    }"
    @update:open="$emit('update:open', $event)"
  >
    <template #content>
      <div class="px-4 pb-2">
        <nav class="space-y-1">
          <NuxtLink
            v-for="item in items"
            :key="item.to"
            :to="item.to!"
            class="flex items-center h-12 px-3 rounded-xl transition-colors"
            :class="currentPath === item.to || (item.to && currentPath.startsWith(item.to + '/'))
              ? 'bg-crystal-50 dark:bg-crystal-950 text-crystal-600 dark:text-crystal-400'
              : 'text-gray-600 dark:text-gray-300 active:bg-gray-100 dark:active:bg-gray-800'"
            @click="$emit('update:open', false)"
          >
            <UIcon :name="item.icon" class="w-5 h-5 mr-3" />
            <span class="text-sm font-medium">{{ item.label }}</span>
          </NuxtLink>
        </nav>
      </div>
      <div style="height: env(safe-area-inset-bottom)" />
    </template>
  </UDrawer>
</template>

<script setup lang="ts">
import type { NavItem } from '~/composables/useNavigation'

defineProps<{
  open: boolean
  items: NavItem[]
}>()
defineEmits<{
  'update:open': [value: boolean]
}>()

const { currentPath } = useNavigation()
</script>
```

`UDrawer` exists in Nuxt UI 3 and defaults to `direction="bottom"` with `handle: true` (built-in drag handle) and `dismissible: true`. This gives native mobile sheet behavior with drag-to-dismiss — no custom handle markup needed.

- [ ] **Step 2: Verify the more sheet**

In Chrome DevTools mobile view:
- Tap "更多" tab in the bottom bar
- Sheet should slide up from bottom (or right as fallback)
- Should show remaining nav items (AI 洞察, 项目管理, 用户管理, 权限管理 — varies by user permissions)
- Tapping an item navigates and closes the sheet
- Tapping the overlay closes the sheet

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/MobileMoreSheet.vue
git commit -m "feat(mobile): add more sheet for overflow navigation items"
```

---

### Task 5: Simplify Header on Mobile

**Files:**
- Modify: `frontend/app/components/AppHeader.vue:2-11`

- [ ] **Step 1: Hide breadcrumbs on mobile**

In `frontend/app/components/AppHeader.vue`, change the `<nav>` breadcrumb container from:

```html
<nav class="flex items-center space-x-2 text-sm">
```

to:

```html
<nav class="hidden md:flex items-center space-x-2 text-sm">
```

And add a mobile-only page title after the `</nav>`:

```html
<nav class="hidden md:flex items-center space-x-2 text-sm">
  <!-- existing breadcrumb content unchanged -->
</nav>
<span class="md:hidden text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
  {{ breadcrumbs[breadcrumbs.length - 1]?.label || '' }}
</span>
```

Also reduce horizontal padding on mobile. Change the `<header>` from:

```html
<header class="h-16 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between px-6 lg:px-8 flex-shrink-0">
```

to:

```html
<header class="h-16 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between px-3 md:px-6 lg:px-8 flex-shrink-0">
```

- [ ] **Step 2: Verify header on mobile vs desktop**

Mobile: Shows only page title (e.g. "问题跟踪"), user avatar, theme toggle, notification bell.
Desktop: Shows full breadcrumb navigation (unchanged).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/AppHeader.vue
git commit -m "feat(mobile): simplify header - show page title instead of breadcrumbs"
```

---

### Task 6: Issue Card Component

**Files:**
- Create: `frontend/app/components/IssueCard.vue`

- [ ] **Step 1: Create IssueCard.vue**

Create `frontend/app/components/IssueCard.vue`:

```vue
<template>
  <NuxtLink
    :to="`/app/issues/${issue.id}`"
    class="block bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border border-white/85 dark:border-gray-700/50 rounded-xl p-3 active:scale-[0.98] transition-transform"
  >
    <div class="flex items-start justify-between gap-2">
      <p class="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2 flex-1">
        {{ issue.title }}
      </p>
      <UBadge
        :color="issue.priority === 'P0' ? 'error' : issue.priority === 'P1' ? 'warning' : issue.priority === 'P2' ? 'warning' : 'neutral'"
        variant="subtle"
        size="xs"
        class="flex-shrink-0"
      >
        {{ issue.priority }}
      </UBadge>
    </div>
    <div class="mt-2 flex items-center gap-2 text-[11px] text-gray-400 dark:text-gray-500">
      <UBadge
        :color="issue.status === '待处理' ? 'warning' : issue.status === '进行中' ? 'info' : issue.status === '已解决' ? 'success' : 'neutral'"
        variant="subtle"
        size="xs"
      >
        {{ issue.status }}
      </UBadge>
      <span>{{ issue.assignee_name || '-' }}</span>
      <span v-if="issue.created_at">{{ issue.created_at.slice(5, 10) }}</span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
defineProps<{
  issue: {
    id: string | number
    title: string
    priority: string
    status: string
    assignee_name?: string
    created_at?: string
  }
}>()
</script>
```

Key design:
- Glass card: `bg-white/70 backdrop-blur-sm border border-white/85 rounded-xl`
- Touch feedback: `active:scale-[0.98]` gives a press-in feel
- Two rows: title + priority on top, status + assignee + date below
- Entire card is a `<NuxtLink>` for navigation

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/IssueCard.vue
git commit -m "feat(mobile): add IssueCard component with glass styling"
```

---

### Task 7: Issues Page Mobile Adaptation

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

This is the largest task. It modifies the issues page to show cards on mobile instead of the table, and makes the create modal responsive.

- [ ] **Step 1: Add mobile detection and update view toggle**

In the `<script setup>` section of `frontend/app/pages/app/issues/index.vue`, add after the existing imports:

```ts
const { isMobile } = useMobile()
```

- [ ] **Step 2: Make the page header responsive**

Replace the current header section (lines 4-24) to stack on mobile:

```html
<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
  <h1 class="text-xl md:text-2xl font-semibold text-gray-900 dark:text-gray-100">问题跟踪</h1>
  <div class="flex items-center justify-between md:justify-end space-x-3">
    <div class="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
      <button
        class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
        :class="viewMode === 'kanban' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
        @click="viewMode = 'kanban'"
      >
        看板
      </button>
      <button
        class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
        :class="viewMode === 'table' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
        @click="viewMode = 'table'"
      >
        列表
      </button>
    </div>
    <UButton icon="i-heroicons-plus" size="sm" @click="showCreateModal = true">
      <span class="hidden md:inline">新建问题</span>
    </UButton>
  </div>
</div>
```

Changes: flex-col on mobile, text-xl on mobile (smaller), button hides text on mobile (icon-only).

- [ ] **Step 3: Hide batch actions on mobile**

Change the batch actions wrapper (line 79) from:

```html
<div v-if="selectedRowsData.length > 0" class="bg-crystal-50 ...">
```

to:

```html
<div v-if="selectedRowsData.length > 0" class="hidden md:flex bg-crystal-50 dark:bg-crystal-950 rounded-xl border border-crystal-100 dark:border-crystal-800 p-3 items-center justify-between">
```

- [ ] **Step 4: Add mobile card list view**

Between the loading state and the kanban view (after line 94), add the mobile card list:

```html
<!-- Mobile Card List -->
<div v-else-if="isMobile && viewMode === 'table'" class="space-y-2">
  <IssueCard v-for="issue in issues" :key="issue.id" :issue="issue" />
  <div class="flex items-center justify-between pt-2">
    <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ totalCount }} 条</span>
    <div class="flex items-center space-x-2">
      <UButton size="xs" variant="ghost" color="neutral" :disabled="page <= 1" @click="page--">上一页</UButton>
      <span class="text-xs text-gray-500 dark:text-gray-400">{{ page }} / {{ totalPages }}</span>
      <UButton size="xs" variant="ghost" color="neutral" :disabled="page >= totalPages" @click="page++">下一页</UButton>
    </div>
  </div>
</div>
```

The v-else chain becomes:
1. `v-if="loading"` — loading state
2. `v-else-if="isMobile && viewMode === 'table'"` — mobile card list
3. `v-else-if="viewMode === 'kanban'"` — kanban view (works on both mobile and desktop)
4. `v-else` — desktop table view

- [ ] **Step 5: Make the create modal form responsive**

In the `<style scoped>` section, change `.form-grid-2` from:

```css
.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
```

to:

```css
.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@media (min-width: 768px) {
  .form-grid-2 {
    grid-template-columns: 1fr 1fr;
  }
}
```

- [ ] **Step 6: Hide MyPendingTasks on mobile (optional, if it's too wide)**

If `MyPendingTasks` renders a wide grid, wrap it:

```html
<div class="hidden md:block">
  <MyPendingTasks />
</div>
```

Or keep it if it's already responsive. Check its output first — if it uses `grid-cols-1 sm:grid-cols-2` it's fine to keep.

- [ ] **Step 7: Verify mobile issues page**

In Chrome DevTools mobile view (390px):
- **List mode:** Shows glass cards instead of table. Each card shows title, priority, status, assignee, date. Tapping navigates to detail.
- **Kanban mode:** Shows columns, horizontally scrollable.
- **View toggle:** Works, switches between card list and kanban.
- **Create button:** Shows as icon-only on mobile, opens modal.
- **Create modal:** Form fields stack to single column.
- **Pagination:** Shows at bottom of card list.

Desktop: Everything looks the same as before.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/pages/app/issues/index.vue
git commit -m "feat(mobile): issues page card list, responsive header and form"
```

---

### Task 8: Issues Detail Page Responsive Fixes

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

Note: `projects/[id].vue` does not use `.form-grid-2` — no changes needed there. Card-list treatment for project issue lists is deferred to a follow-up (the project detail page already uses responsive grids).

- [ ] **Step 1: Make issues detail form responsive**

In `frontend/app/pages/app/issues/[id].vue`, find `.form-grid-2` in the `<style scoped>` section and apply the same responsive fix as Task 7 Step 5:

```css
.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@media (min-width: 768px) {
  .form-grid-2 {
    grid-template-columns: 1fr 1fr;
  }
}
```

- [ ] **Step 2: Verify detail page on mobile**

In Chrome DevTools mobile view:
- Issue detail: form fields stack to single column, all content readable
- GitHub issue linking modals render at full width on mobile (Nuxt UI modals already handle this via `sm:max-w-*` classes)

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/issues/\[id\].vue
git commit -m "feat(mobile): make issue detail page forms responsive"
```

---

### Task 9: Final Verification & Cleanup

- [ ] **Step 1: Full mobile walkthrough**

In Chrome DevTools mobile view (iPhone 12 Pro, 390x844), walk through:

1. Login page (should already be responsive — `auth.vue` layout is centered)
2. Issues list — card view, kanban view, create modal
3. Issue detail — form fields stacked
4. Dashboard — grid should be responsive already
5. Tab bar — tap each tab, verify navigation
6. More sheet — verify all overflow items appear
7. Dark mode — toggle theme, verify glass effects look good in dark

- [ ] **Step 2: Full desktop regression check**

In full-width browser:

1. Sidebar visible and working (hover expand/collapse)
2. No bottom tab bar visible
3. Issues table view with all columns
4. Breadcrumbs visible in header
5. All existing functionality unchanged

- [ ] **Step 3: Build check**

Run: `cd frontend && npm run build`

Expected: Build succeeds with no errors.

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(mobile): address issues found during verification"
```

- [ ] **Step 5: Push to env/test**

```bash
git push origin main
git push origin main:env/test
```
