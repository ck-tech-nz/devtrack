# Notifications App & @mention / #issue 引用

## 概述

为 DevTrack 新增两个功能：

1. **Notification App** — 通用通知系统，支持个人通知、广播通知（全员/分组），通知内容支持 markdown
2. **@mention / #issue 引用** — 在问题描述的 markdown 编辑器中支持 `@用户` 和 `#问题编号` 的自动补全、存储和渲染，被提及的用户会收到通知

两个子系统分开实现，Notification App 先行，mention/reference 依赖它。

---

## 子系统 1：Notification App

### 数据模型

新增 Django App：`notifications`

#### Notification

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUIDField (pk) | 主键 |
| `notification_type` | CharField | 枚举：`mention`、`system`、`broadcast` |
| `title` | CharField | 通知标题 |
| `content` | TextField | 通知正文，支持 markdown |
| `source_user` | FK(User, null) | 触发者（系统通知为空） |
| `source_issue` | FK(Issue, null) | 关联问题（可空） |
| `target_type` | CharField | 目标类型：`user`、`group`、`all` |
| `target_group` | FK(Group, null) | 目标组（target_type=group 时使用） |
| `created_at` | DateTimeField | 创建时间 |

#### NotificationRecipient

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUIDField (pk) | 主键 |
| `notification` | FK(Notification) | 关联通知 |
| `user` | FK(User) | 接收者 |
| `is_read` | BooleanField | 是否已读，默认 False |
| `read_at` | DateTimeField(null) | 阅读时间 |
| `is_deleted` | BooleanField | 软删除，默认 False |

**unique_together**: (`notification`, `user`)

广播通知（target_type=`all` 或 `group`）只有一条 Notification 记录，每个目标用户有各自的 NotificationRecipient 记录来追踪已读/删除状态。

### 广播通知的 Recipient 生成

广播通知在 Django Admin 中创建时，通过 model save 或 signal 自动为目标用户批量创建 NotificationRecipient 记录：
- `target_type=all`：为所有 `is_active=True` 的用户创建
- `target_type=group`：为 `target_group` 中的所有用户创建
- `target_type=user`：由调用方显式创建（如 mention 场景）

### API 端点

所有端点挂载在 `/api/notifications/`，仅返回当前认证用户的通知。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notifications/` | 通知列表（分页，支持 `?is_read=true/false` 筛选） |
| GET | `/api/notifications/unread-count/` | 返回 `{"count": N}`，轮询用，轻量查询 |
| POST | `/api/notifications/{id}/read/` | 标记单条已读 |
| POST | `/api/notifications/read-all/` | 全部标记已读 |
| DELETE | `/api/notifications/{id}/` | 软删除（设置 `is_deleted=True`） |

所有 `{id}` 指 Notification 的 UUID。后端通过当前用户 + notification ID 定位对应的 NotificationRecipient 记录。

列表接口通过 NotificationRecipient 查询，自动过滤 `is_deleted=False`，按 `notification__created_at` 降序排列。

### Django Admin

在 Admin 中注册 Notification 模型，管理员可以：
- 创建广播通知（设置 `target_type` 为 `all` 或 `group`）
- 查看所有通知记录

### 前端

#### 铃铛组件

位于顶部导航栏右侧：
- 铃铛图标 + 未读数角标（红色圆形，数字）
- 每 30 秒轮询 `GET /api/notifications/unread-count/`
- 使用 `useNotifications` composable 管理状态

#### 下拉面板

点击铃铛展开：
- 展示最近 5 条通知（标题 + 时间 + 已读状态）
- 通知内容用 markdown-it 渲染
- 点击单条通知：标记已读，如有关联问题则跳转到问题详情
- "全部已读"按钮
- "查看全部通知"链接 → 跳转到通知页面

#### 通知页面

路由：`/app/notifications`

- 通知列表，分页展示
- 筛选：全部 / 未读 / 已读
- 单条操作：标记已读、删除
- 批量操作：全部已读
- 通知内容支持 markdown 渲染

#### 权限

通知页面不需要特殊权限，所有登录用户可见。需在 `useNavigation.ts` 中添加导航项（可选，也可仅通过铃铛访问）。

---

## 子系统 2：@mention / #issue 引用

### 存储格式

在 markdown 文本中使用类链接语法存储引用：

```
@[张三](user:5)        -- 用户引用，ID 为用户自增主键
#[ISS-061](issue:61)   -- 问题引用，ID 为问题编号（number 字段）
```

编辑时用户看到原始标记文本，预览时渲染为高亮链接。

### 后端

#### API 修改

**用户补全**：`GET /api/users/choices/` 已有接口，返回 `[{id, name}]`，足够 @mention 使用。

**问题补全**：`GET /api/issues/` 已有搜索接口，需扩展 `search_fields` 增加 `number` 字段支持，使 `?search=61` 能匹配问题编号。补全下拉需要的字段：`id`、`number`、`title`。

#### Mention 解析与通知

在 `IssueCreateUpdateSerializer` 的 `create()` 和 `update()` 方法中（或抽取为独立的 service 函数）：

1. 用正则 `r'@\[([^\]]+)\]\(user:(\d+)\)'` 从新描述中提取所有被提及的用户 ID
2. `update()` 时：从旧描述中同样提取，计算差集得到**新增** mention；`create()` 时：所有 mention 均为新增
3. 为每个新增 mention 创建 Notification（type=`mention`，source_user=当前用户，source_issue=当前问题）和对应的 NotificationRecipient
4. 不为 source_user 自己创建通知（避免自己 @自己收到通知）

### 前端 — 自动补全

#### MarkdownEditor 组件改造

在现有 `MarkdownEditor.vue` 的 textarea 上增加自动补全功能：

**触发机制**：
- 监听 `input` 事件，检测光标前的文本
- `@` 字符触发用户补全
- `#` 字符触发问题补全
- 继续输入文字作为搜索关键词筛选列表

**浮动下拉组件** (`MentionDropdown.vue`)：
- 绝对定位，使用 textarea-caret 位置计算库定位在光标附近
- 展示匹配项列表（用户：头像 + 名字；问题：编号 + 标题）
- 键盘交互：↑↓ 选择、Enter 确认、Esc 关闭
- 点击选择

**选中后行为**：
- 用户选中 → 替换触发文本为 `@[张三](user:5)`
- 问题选中 → 替换触发文本为 `#[ISS-061](issue:61)`

**数据获取**：
- `@` 触发时调用 `/api/users/choices/`（可缓存，用户列表变动不频繁）
- `#` 触发时调用 `/api/issues/?search=<keyword>&page_size=10`（按输入关键词搜索）

### 前端 — 渲染

#### markdown-it 自定义插件

为 markdown-it 注册自定义 inline rule：

- `@[显示名](user:ID)` → `<span class="mention-user">@显示名</span>`
- `#[ISS-NNN](issue:ID)` → `<a href="/app/issues/ID" class="mention-issue">#ISS-NNN</a>`

#### 样式

- `.mention-user`：带浅色背景的 inline 标签（如浅蓝色），不可点击
- `.mention-issue`：带浅色背景的 inline 链接（如浅绿色），可点击跳转到问题详情

---

## 实现顺序

1. **Notification App 后端**：模型、migration、serializer、viewset、admin
2. **Notification App 前端**：composable、铃铛组件、下拉面板、通知页面、轮询
3. **Mention/Reference 后端**：issues search 扩展、mention 解析、通知创建
4. **Mention/Reference 前端**：自动补全组件、markdown-it 插件、样式
