# Release Notification

Generate a release note with screenshots and publish as a notification to all DevTrakr users.

## Arguments

- `$ARGUMENTS` — (optional) Brief description of what changed in this release. If omitted, check `git log` for recent commits since last release notification.

## Credentials

- Login user: `test`
- Login password: `password123`
- App URL: `http://localhost:3000`

If login fails, ask the user for correct credentials.

## Steps

Execute these steps in order. Do NOT skip any step.

### 1. Determine Release Content

If `$ARGUMENTS` is provided, use it as the release description.

If not, run:
```bash
git log --oneline -20
```
Summarize the user-facing changes (skip docs/chore commits). Ask the user to confirm what to include.

### 2. Setup Browse

```bash
B=~/.claude/skills/gstack/browse/dist/browse
```

If browse binary is not available, tell the user to run `/browse` first to set it up.

### 3. Screenshot — Landing Page (logged out)

```bash
$B goto http://localhost:3000/
$B js "localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token')"
$B goto http://localhost:3000/
$B wait --networkidle
$B screenshot /tmp/release-landing.png
```

Read `/tmp/release-landing.png` to verify it looks right. If it shows the login form instead of a landing page, the landing page feature may not exist — skip this screenshot.

### 4. Screenshot — Key Feature Pages (logged in)

Login:
```bash
$B goto http://localhost:3000/login
$B wait --networkidle
$B snapshot -i
$B fill @e1 "test"
$B fill @e2 "password123"
$B click @e3
$B wait --networkidle
```

Verify login succeeded by checking `$B url` — should be `/app/home` or an `/app/` page.

Then screenshot each page relevant to the release:
```bash
$B goto http://localhost:3000/app/{page}
$B wait --networkidle
$B screenshot /tmp/release-{page}.png
```

Read each screenshot to verify it looks correct.

### 5. Get Auth Token

```bash
TOKEN=$($B js "localStorage.getItem('access_token')")
```

### 6. Upload Screenshots

For each screenshot taken:
```bash
RESP=$(curl -s -X POST http://localhost:3000/api/tools/upload/image/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/release-{name}.png;type=image/png")
echo "$RESP"
```

Save each returned `url` value (format: `/uploads/YYYY/MM/DD/{hash}.png`).

### 7. Compose Release Note

Write the notification content in **Markdown** (Chinese). Follow this structure:

```markdown
## 新功能

### 1. {Feature Name}

{1-2 sentence description of what users can now do.}

![{caption}]({uploaded_url})

**亮点：**
- Bullet point 1
- Bullet point 2

---

### 2. {Next Feature}
...
```

Rules:
- Write in Chinese — this is the project UI language
- Lead with user benefit, not technical detail
- Include uploaded screenshot URLs as `![caption](url)`
- Use `---` between sections
- Add `> ` blockquote for role-specific tips (e.g. tester features)
- Keep it concise

### 8. Publish Notification

```bash
curl -s -X POST http://localhost:3000/api/notifications/manage/create/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg title "{TITLE}" \
    --arg content "{MARKDOWN_CONTENT}" \
    '{title: $title, content: $content, target_type: "all", is_draft: false}')"
```

The title should be short and descriptive, e.g. "DevTrakr 更新：{feature summary}".

### 9. Verify

```bash
$B viewport 1280x2400
$B goto http://localhost:3000/app/notifications/{NOTIFICATION_ID}
$B wait --networkidle
$B screenshot /tmp/release-note-verify.png
```

Read the verification screenshot and show it to the user.

Report: "Release note 已发送给 {N} 位用户。"

## API Reference

### Image Upload
- **POST** `/api/tools/upload/image/`
- Auth: `Authorization: Bearer {token}`
- Body: `multipart/form-data` with `file` field
- Response: `{"url": "/uploads/...", "filename": "...", "id": "..."}`

### Create Notification
- **POST** `/api/notifications/manage/create/`
- Auth: `Authorization: Bearer {token}`
- Body JSON: `{title, content, target_type: "all", is_draft: false}`
- Response: `{"id": "...", "recipients": N}`
- `target_type` options: `"all"`, `"group"` (+ `target_group` ID), `"user"` (+ `target_user_ids` list)
