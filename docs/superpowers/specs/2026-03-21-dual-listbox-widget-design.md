# DualListbox Widget for Group Permissions

**Date:** 2026-03-21
**Scope:** Frontend-only change — no backend modifications

## Problem

The "组-权限" tab on `/app/permissions` displays group permissions as a flat grid of checkbox tags. With many permissions, this is hard to scan and manage. The user wants a Django admin `filter_horizontal`-style dual-listbox widget instead.

## Design

### New Component: `DualListbox.vue`

**Location:** `frontend/app/components/DualListbox.vue`

**Interface:**
```ts
// Props
items: string[]         // All available items
modelValue: string[]    // Currently selected items (v-model)

// Emits
'update:modelValue'     // Array of selected items
```

**Layout:**
```
┌─ 可用 权限 ─────────────┐       ┌─ 选中的 权限 ────────────┐
│ 🔍 [过滤...]            │       │ 🔍 [过滤...]             │
│ ┌──────────────────────┐ │  [⇨]  │ ┌──────────────────────┐ │
│ │ issues.add_issue     │ │  [⇦]  │ │ issues.view_issue    │ │
│ │ issues.change_issue  │ │       │ │ projects.view_项目   │ │
│ │ projects.add_project │ │       │ │                      │ │
│ └──────────────────────┘ │       │ └──────────────────────┘ │
│   Choose all ⇨           │       │   ⇦ Remove all           │
└──────────────────────────┘       └──────────────────────────┘
```

**Behavior:**
- Left panel: `items` minus `modelValue` (available), sorted alphabetically
- Right panel: `modelValue` (selected), sorted alphabetically
- Each panel has a text filter input at top — substring match, case-insensitive
- Items are rendered in a scrollable list (fixed height ~250px)
- Click to select an item (highlight). Ctrl/Cmd+click for multi-select. Shift+click for range select.
- Center buttons:
  - `→` moves highlighted available items to selected
  - `←` moves highlighted selected items to available
- Bottom actions:
  - "Choose all →" under left panel: moves all currently **filtered** available items to selected
  - "← Remove all" under right panel: moves all currently **filtered** selected items back to available
- Emits `update:modelValue` on every change (arrow click or choose/remove all)

**Styling:**
- Bordered panels with light header bars matching Django admin aesthetic
- Dark mode via Tailwind `dark:` classes, consistent with existing app style
- Items use monospace-ish text for permission codenames

### Integration in `permissions.vue`

**View mode toggle:**
- Add a small toggle in the groups tab header to switch between:
  - "列表模式" (DualListbox) — **default**
  - "标签模式" (current checkbox tags)
- Toggle state stored in a local `ref`, not persisted

**Data adaptation:**
- `group._selectedPerms` is currently a `Set<string>`. Convert to/from array at the DualListbox boundary:
  - Pass `Array.from(group._selectedPerms)` as `modelValue`
  - On `update:modelValue`, replace the Set: `group._selectedPerms = new Set(newValue)`
- `allPermissions.value.map(p => p.full_codename)` provides the `items` prop

**What stays unchanged:**
- Group card layout (title + save button in header)
- `saveGroup()` function and all API calls
- Current checkbox tag mode preserved as alternate view
- All other tabs (routes, permissions list)

## Files Changed

| File | Change |
|------|--------|
| `frontend/app/components/DualListbox.vue` | **New** — reusable dual-listbox component |
| `frontend/app/pages/app/permissions.vue` | Replace groups tab content with DualListbox + view toggle |

## Out of Scope

- Backend API changes
- Drag-and-drop reordering
- Persisting view mode preference
