# Broadcast popup on app entry

## Problem

Broadcast-type notifications (`Notification.Type.BROADCAST`, e.g. release notes, important announcements) currently surface only through the notification bell in the header. Users can miss them until they happen to open the bell. We want broadcasts to be visually intrusive enough that users see them at least once.

## Goal

When a user enters the authenticated app shell, if they have any unread broadcasts, show each one as a popup (one at a time). Clicking `知道了` marks that broadcast as read. Once read, it does not pop again. Non-broadcast notifications (mention, system) are unaffected and continue to use the bell as today.

## Non-goals

- Real-time delivery while the user is mid-session. The check fires once per app load — a broadcast that arrives while they are using the app surfaces on their next entry, not immediately.
- Replacing the notification bell. The bell still shows all unread items including broadcasts.
- Cross-tab coordination. Two open tabs may both pop the same broadcast; `markRead` is idempotent so the second one is harmless. Acceptable for v1.
- Rewriting the project-wide markdown-rendering inconsistency (the notification detail page already loads `useMentionMarkdown` but lacks visible styles for `.markdown-body`). The popup will include its own scoped styles; lifting them into a shared rule is out of scope here.

## User flow

1. User logs in or returns to a tab where they are already authenticated and lands on any `/app/*` route.
2. The default layout mounts. `useBroadcastPopup().start()` runs.
3. Frontend calls `GET /api/notifications/?notification_type=broadcast&is_read=false&page_size=20`.
4. For each returned broadcast (newest first), in order:
   - `useDialog().alert({ title, htmlBody: md.render(content), persistent: true, confirmText: '知道了' })` opens a centered modal.
   - User reads it, clicks `知道了`.
   - `POST /api/notifications/{id}/read/` fires.
   - Next broadcast pops, or the queue ends.
5. If the user closes the browser before clicking `知道了`, the broadcast remains unread and pops again on their next entry to `/app/*`.

## Architecture

### Backend — one-line filter add

`NotificationListView.get_queryset` in `backend/apps/notifications/views.py` already supports `?is_read=...`. Add the same shape for `?notification_type=...`:

```python
notif_type = self.request.query_params.get("notification_type")
if notif_type:
    qs = qs.filter(notification_type=notif_type)
```

No new endpoint needed. The existing list-and-filter pattern is reused.

### Frontend — `useDialog()` API extension

The existing `alert()` returns `Promise<void>` and accepts `{title, message, confirmText, color, icon}`. Two optional fields are added:

```ts
export type AlertOptions = {
  title?: string
  message?: string             // becomes optional when htmlBody is supplied
  htmlBody?: string            // when set, renders via v-html instead of message
  persistent?: boolean         // when true, backdrop click + Esc are no-ops
  confirmText?: string
  color?: DialogColor
  icon?: string
}
```

Internal `DialogState` adds matching fields and a default `persistent: false` so existing callers keep their current behavior. The `confirm()` API is untouched.

### Frontend — `AppDialog.vue` extension

Three changes:
1. Template branches the body: if `state.htmlBody`, render `<div class="dialog-markdown" v-html="state.htmlBody" />`; otherwise the existing `<p class="dialog-message">{{ state.message }}</p>`.
2. `onOverlayClick` and `onEsc` early-return when `state.persistent` is true.
3. The panel gets `max-height: min(80vh, 720px); overflow-y: auto` so long Markdown bodies (with images, bullet lists, headings) scroll inside the dialog rather than pushing it off-screen.
4. New scoped styles for `.dialog-markdown` cover the typography users will see in broadcasts: h1/h2/h3, p, ul/ol, strong/em, code, a, img (with `max-width: 100%; border-radius: 6px`), blockquote, and `hr`. Light + dark variants. These rules mirror the existing `.markdown-body` styles in `MarkdownEditor.vue` so the visual language is consistent.

### Frontend — new composable `useBroadcastPopup.ts`

```ts
// Single-fire guard lives in useState so SSR/HMR doesn't re-trigger
// and navigation within /app/* doesn't re-run it.
export function useBroadcastPopup() {
  const { api } = useApi()
  const { alert } = useDialog()
  const { markRead } = useNotifications()
  const { md } = useMentionMarkdown()
  const started = useState<boolean>('broadcast_popup_started', () => false)

  async function start() {
    if (started.value) return
    started.value = true
    try {
      const res = await api<{ results: NotificationItem[] }>(
        '/api/notifications/?notification_type=broadcast&is_read=false&page_size=20',
      )
      for (const n of res.results || []) {
        await alert({
          title: n.title,
          htmlBody: md.render(n.content || ''),
          persistent: true,
          confirmText: '知道了',
        })
        try { await markRead(n.id) } catch { /* keep queue running */ }
      }
    } catch {
      // silent: no popup on API failure, bell still surfaces unread state
    }
  }
  return { start }
}
```

Notes:
- The guard uses `useState` (Nuxt's reactive ref shared across the SSR/CSR boundary) so identity is stable per app load. It is intentionally NOT persisted across page reloads — if the user reloads the tab they get the popup again, which is the desired safety net.
- We process broadcasts newest-first (the API's default ordering). The user sees the most recent broadcast first, which is the one most likely to be relevant.
- `markRead` errors are caught per-iteration so a single transient failure doesn't break the queue.

### Frontend — trigger in `layouts/default.vue`

```ts
onMounted(() => {
  useBroadcastPopup().start()
})
```

The default layout wraps every `/app/*` route. The `auth.vue` layout (used by login/register) does not import it, so the popup does not fire on unauthenticated pages. The `useState` guard ensures the popup runs once per app load, not once per route navigation within `/app/*`.

## Edge cases

| Case | Behavior |
|---|---|
| Zero unread broadcasts | No popup, no UI noise. |
| List API fails | Caught silently. Bell still surfaces unread count. |
| `markRead` fails mid-queue | Per-iteration catch; queue continues. The unread broadcast pops again next session. |
| Two tabs open simultaneously | Both fetch and pop independently. `markRead` is idempotent (just sets `is_read=true`), so the second tab's call is a no-op. Worst case: same popup seen twice. |
| User closes tab without clicking `知道了` | Broadcast remains unread; pops next entry. |
| Broadcast content has `<script>` or other HTML | `markdown-it` defaults to `html: false`, so raw HTML in the source is escaped. XSS surface is bounded to admin-authored content. |
| Tall content with images | Dialog panel caps at `min(80vh, 720px)` with internal scroll; images use `max-width: 100%`. |
| `htmlBody` empty (broadcast has no content) | The dialog still renders title + an empty body region + the `知道了` button. Acceptable — a title-only broadcast is valid. |

## Testing

**Backend** (`backend/tests/test_notifications.py`, append):
- `test_list_filters_by_notification_type` — create a mention, a system, and a broadcast, query `?notification_type=broadcast`, assert exactly the broadcast is returned.

**Frontend**: manual verification (no Vue test infra for this layout). Steps:
1. Publish a broadcast via admin or the existing `/api/notifications/manage/create/` endpoint with `target_type=all`.
2. Log in as a user who hasn't read it. Lands on `/app/home`.
3. Popup appears with the broadcast title + markdown-rendered body. Backdrop click and Esc do nothing.
4. Click `知道了`. Popup closes. `POST /api/notifications/{id}/read/` fires (verify in network tab).
5. Navigate around `/app/*`. Popup does not re-fire.
6. Reload the page. Popup does not fire (the broadcast is now read).
7. Publish a second broadcast. Reload. New popup appears.
8. Publish two broadcasts. Reload. First popup → click 知道了 → second popup → click 知道了 → done.

## Files touched

- `backend/apps/notifications/views.py` — add `notification_type` filter (3 lines).
- `backend/tests/test_notifications.py` — append one test.
- `frontend/app/composables/useDialog.ts` — extend `AlertOptions` + `DialogState`.
- `frontend/app/components/AppDialog.vue` — handle `htmlBody`, `persistent`, scrollable panel, markdown styles.
- `frontend/app/composables/useBroadcastPopup.ts` — new file.
- `frontend/app/layouts/default.vue` — wire `onMounted(() => useBroadcastPopup().start())`.
