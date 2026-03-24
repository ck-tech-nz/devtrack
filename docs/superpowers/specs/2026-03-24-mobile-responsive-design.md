# Mobile Responsive Support for DevTrack

**Date:** 2026-03-24
**Status:** Approved

## Problem

DevTrack's frontend is desktop-only. On mobile devices (<768px), the sidebar consumes most of the viewport, content is squeezed into a narrow strip, and tables with 13+ columns are unusable. The app needs proper mobile support.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Mobile navigation | Bottom tab bar | Native app feel, maximizes content area |
| Tab count | 4 (Issues, 概览, GitHub, 更多) | Larger touch targets, admin pages grouped under "更多" |
| Visual style | Apple Liquid Glass | Frosted translucent backgrounds with blur, modern aesthetic |
| Table adaptation | Card list on mobile | Cards show key fields; tap navigates to detail |
| Kanban on mobile | Keep with horizontal scroll | Allows quick status triage on the go |
| Breakpoint | 768px (md) | Standard tablet/phone boundary; matches Tailwind `md` |

## Architecture

### Prerequisites

#### Viewport Meta Tag
Add to `nuxt.config.ts` `app.head`:
```ts
meta: [
  { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' }
]
```
`viewport-fit=cover` is required for safe area inset support on notched devices.

#### Mobile Detection Composable
Use VueUse's `useMediaQuery` for reactive breakpoint detection:
```ts
const isMobile = useMediaQuery('(max-width: 767px)')
```
This handles SSR gracefully (relevant even in SPA mode for initial render).

### Breakpoint Strategy

- **Desktop (>=768px):** Current layout unchanged — sidebar + header + content
- **Mobile (<768px):** Sidebar hidden, bottom tab bar shown, card-based content

### New Components

#### `AppBottomTabBar.vue`
- Rendered only on mobile (`md:hidden`)
- Fixed to bottom of viewport
- Tab items derived from `useNavigation()` composable's `filteredNavItems`:
  - Primary tabs (first 3 items by route): `/app/issues`, `/app/dashboard`, `/app/repos`
  - 4th tab is "更多" which opens the more sheet with remaining items
  - If nav items change in backend `PAGE_PERMS`, tabs adapt automatically
- Liquid glass visual using Tailwind `dark:` variants for consistency with codebase:
  - Light: `bg-white/55 backdrop-blur-[20px] backdrop-saturate-[180%] border-t border-white/60`
  - Dark: `dark:bg-slate-900/65 dark:border-white/[0.08]`
- Active tab: tinted icon background with brand color (`crystal-600` at 12% opacity)
- Highlights current route via `useRoute()`
- Minimum touch target: 44x44px per tab item (Apple HIG)
- Safe area: `padding-bottom: env(safe-area-inset-bottom)` for notched devices

| Tab | Route | Icon |
|-----|-------|------|
| Issues | /app/issues | i-heroicons-bug-ant |
| 概览 | /app/dashboard | i-heroicons-squares-2x2 |
| GitHub | /app/repos | i-heroicons-code-bracket |
| 更多 | (opens sheet) | i-heroicons-ellipsis-horizontal |

#### `MobileMoreSheet.vue`
- Slide-up bottom sheet triggered by "更多" tab
- Uses Nuxt UI `UDrawer` (bottom drawer variant) for native sheet behavior
- Lists remaining nav items from `filteredNavItems` that are not primary tabs
- Permission-filtered automatically (uses same `useNavigation()` data)
- Each item is a navigation link that closes the sheet on tap
- Glass styling on the sheet background

#### `IssueCard.vue`
- Reusable card component for issue list items on mobile
- Displays: title, priority badge, status badge, assignee name, creation date
- Glass card style: `bg-white/70 backdrop-blur-sm border border-white/85 rounded-xl`
- Entire card is tappable (`<NuxtLink>`), navigates to `/app/issues/:id`
- Compact layout: title + priority on first row, status + assignee + date on second row

### Modified Components

#### `AppSidebar.vue`
- Add `hidden md:flex` to root `<aside>` element
- `hidden` removes the element from flow entirely, so no further adjustment needed in the parent flex container (`default.vue`)
- No other changes — desktop behavior unchanged

#### `default.vue` (layout)
- Add `<AppBottomTabBar />` inside the layout
- Adjust `<main>` padding: `p-3 md:p-6 lg:p-8` (reduced from `p-6` to maximize mobile content width)
- Add `pb-20 md:pb-0` to `<main>` to prevent content hiding behind tab bar + safe area on mobile
- Existing flex layout remains for desktop

#### `AppHeader.vue`
- Hide breadcrumbs on mobile: `hidden md:flex` on breadcrumb container
- Show only page title and essential actions (user avatar, notifications)

#### `issues/index.vue`
- Use `useMediaQuery('(max-width: 767px)')` to detect mobile
- **List view (mobile):** Render `<IssueCard>` components instead of `<UTable>`
- **Kanban view (mobile):** Keep existing `SharedKanbanBoard` but cards are more compact
- **View toggle:** Replace button group with segmented control styling on mobile
- **Batch actions:** Hidden on mobile (`hidden md:flex`) — not practical on touch
- **"新建问题" button:** Remains visible, positioned in header area
- **Create issue modal:** `.form-grid-2` stacks to single column on mobile via `grid-cols-1 md:grid-cols-2`

#### `issues/[id].vue` (detail page)
- Form fields stack to single column on mobile (already mostly single-column, verify `.form-grid-2` usage)
- GitHub issue linking modals go full-width on mobile
- Analysis fields (remark, cause, solution) remain full-width (already are)

#### Other pages
- `projects/[id].vue` — same card-list treatment for issues within projects
- Dashboard/概览 — grid already responsive (`grid-cols-1 sm:grid-cols-2`), just needs padding adjustments

### No Backend Changes

This is purely frontend work. No API or model changes required.

## Visual Specifications

### Liquid Glass Effect (Tailwind classes)

```
Light: bg-white/55 backdrop-blur-[20px] backdrop-saturate-[180%] border-t border-white/60 shadow-[0_-2px_20px_rgba(0,0,0,0.05)]
Dark:  dark:bg-slate-900/65 dark:border-white/[0.08] dark:shadow-[0_-2px_20px_rgba(0,0,0,0.3)]
```

### Tab Bar Dimensions
- Bar own height: 52px + `env(safe-area-inset-bottom)` for notched devices
- Each tab touch target: minimum 44x44px
- Icon size: 24px
- Label font: 10px
- Active indicator: tinted background on icon (crystal-600 at 12% opacity)

### Issue Cards
- Border radius: 12px (`rounded-xl`)
- Padding: 12px
- Gap between cards: 8px
- Title: 14px font-weight-500
- Meta row: 11px, gray-400 color
- Priority/status badges: 10px, colored backgrounds

## Scope Exclusions

- No swipe gestures (can be added later)
- No offline support
- No mobile-specific API optimizations (pagination stays the same)
- No pull-to-refresh (can be added later)
- No infinite scroll (keep standard pagination for now)
- Desktop layout remains completely unchanged
