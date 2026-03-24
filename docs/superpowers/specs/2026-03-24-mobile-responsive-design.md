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

### Breakpoint Strategy

- **Desktop (>=768px):** Current layout unchanged — sidebar + header + content
- **Mobile (<768px):** Sidebar hidden, bottom tab bar shown, card-based content

### New Components

#### `AppBottomTabBar.vue`
- Rendered only on mobile (`md:hidden`)
- Fixed to bottom of viewport
- 4 tab items: Issues, 概览, GitHub, 更多
- Liquid glass visual: `backdrop-filter: blur(20px) saturate(180%)`, `background: rgba(255,255,255,0.55)`, subtle top border with `border-top: 1px solid rgba(255,255,255,0.6)`
- Active tab: tinted icon background with brand color (`crystal-600`)
- Highlights current route via `useRoute()`
- Dark mode: `background: rgba(15,23,42,0.65)` with adjusted border

#### `MobileMoreSheet.vue`
- Slide-up bottom sheet triggered by "更多" tab
- Lists remaining nav items: AI 洞察, 项目管理, 用户管理, 权限管理
- Permission-filtered using existing `useNavigation()` composable's `can()` checks
- Each item is a navigation link that closes the sheet on tap
- Uses Nuxt UI `USlideover` or custom sheet with glass styling

#### `IssueCard.vue`
- Reusable card component for issue list items on mobile
- Displays: title, priority badge, status badge, assignee name, creation date
- Glass card style: `background: rgba(255,255,255,0.7)`, `backdrop-filter: blur(8px)`, rounded corners
- Entire card is tappable, navigates to `/app/issues/:id`
- Compact layout: title + priority on first row, status + assignee + date on second row

### Modified Components

#### `AppSidebar.vue`
- Add `hidden md:flex` to root `<aside>` element
- No other changes — desktop behavior unchanged

#### `default.vue` (layout)
- Add `<AppBottomTabBar />` inside the layout
- Add `pb-[68px] md:pb-0` to `<main>` to prevent content hiding behind tab bar on mobile
- Existing flex layout remains for desktop

#### `AppHeader.vue`
- Hide breadcrumbs on mobile: `hidden md:flex` on breadcrumb container
- Show only page title and essential actions (user avatar, notifications)
- Optionally add "+" button for quick issue creation on mobile

#### `issues/index.vue`
- Detect mobile via composable or media query (`useMediaQuery` or `window.matchMedia`)
- **List view (mobile):** Render `<IssueCard>` components instead of `<UTable>`
- **Kanban view (mobile):** Keep existing `SharedKanbanBoard` but cards are more compact
- **View toggle:** Replace button group with segmented control styling on mobile
- **Batch actions:** Hidden on mobile (`hidden md:flex`) — not practical on touch
- **"新建问题" button:** Remains visible, positioned in header area

#### Other pages with tables
- `projects/[id].vue` — same card-list treatment for issues within projects
- Dashboard/概览 — grid already responsive, just needs spacing adjustments

### No Backend Changes

This is purely frontend work. No API or model changes required.

## Visual Specifications

### Liquid Glass Effect

```css
/* Light mode */
.glass {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.05);
}

/* Dark mode */
.dark .glass {
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.3);
}
```

### Tab Bar Dimensions
- Height: 68px (includes safe area padding for notched devices)
- Icon size: 24px
- Label font: 10px
- Active indicator: tinted background on icon (crystal-600 at 12% opacity)

### Issue Cards
- Border radius: 12px
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
- Desktop layout remains completely unchanged
