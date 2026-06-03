# 任务派发与点评（复用提升计划，隐藏奖赏）

- 日期：2026-06-03
- 状态：设计已确认，待写实现计划
- 相关模块：`backend/apps/kpi/`、`frontend/app/pages/app/ai/`

## 1. 背景与目标

### 管理痛点（来源：团队现状）
1. **学习主动性差**——没人推就不学。
2. **对业务/框架/日志/表设计毫不关心**，只会用 AI，且不分析、不学习 AI 的输出。
3. **对 bug 的严重程度无感知**，系统里的问题只要没人提出，自己不会主动修。
4. **处罚机制缺失、大锅饭**——干好干坏一个样，缺乏区分与问责。

### 本次目标
建立一个**任务派发 → 执行反馈 → 评分点评**的管理闭环，让管理者能：
- 随时给某个成员派发一条带截止日期的任务；
- 看到成员（线上/线下）的执行进度与反馈；
- 按可配置的行为维度给成员打分并写总评，作为问责与区分的依据。

**重要边界：奖赏机制暂停。** 现有的分值、质量系数、已得分、KPI 五维段位等"奖赏/计件"内容整体**隐藏**（数据保留、UI 不显示），等董事会通过后再启用。本次只做"派发—反馈—评分"闭环。

## 2. 已确认的设计决策

| 决策点 | 结论 |
|---|---|
| 承载底座 | **复用** `ImprovementPlan` / `ActionItem`，隐藏奖赏层（不新建模块、不改用工单） |
| 评分形式 | **多维度打分 + 总评**（管理者手动按行为维度打分，非机器自动复合分） |
| 维度库 | Django admin 维护一个**候选维度库**（预置 4 个：主动性/理解深度/完成质量/交付与沟通），作为**默认池**；注册 `KPIScoringConfig` 单例，不做独立前端配置页 |
| 逐任务维度 | 每个任务**快照**自己的一套维度：派发时默认从库填充，管理者可**勾选子集 + 临时加维度 + 调权重**；评分前都可改 |
| 每维量表 | **1-5 星** |
| 综合分 | 按**该任务自己那套维度**的权重加权平均，**仅展示**，不参与任何奖赏 |
| 派发方式 | **即时派发，月度自动归桶**——选人填任务即出现在对方"我的任务"，后台落到其当月计划并直接发布 |
| 截止日期 | `due_date`，**派发时必填**（用于逾期监督） |
| 工作台 | 待办任务像 issue 一样上首页"工作台"：把现有"我的提升计划"卡改成清爽的**"我的任务"待办清单**（隐藏分数） |
| 奖赏字段 | 仅 UI 隐藏、数据保留；恢复时用"维度总分→系数"映射，无需再迁移 |

> 注：管理者手动按行为打分，与此前"`/app/kpi` 五维**机器复合分**对肉眼评估无意义"的反馈不冲突——前者是有指向性的人工考核标尺，后者是被否定的自动复合分。

## 3. 数据模型变更（`backend/apps/kpi/models.py`）

### 3.1 `KPIScoringConfig`（单例）新增字段 —— 维度"候选库/默认池"
```python
review_dimensions = models.JSONField(
    default=_default_review_dimensions,
    verbose_name="点评维度库",
    help_text="点评维度候选库/默认池，每项 {key,label,weight}；派发新任务时默认从此填充，之后逐任务可改",
)
```
> 这里只是**默认池**。真正生效的是每个任务自己快照的 `ActionItem.review_dimensions`（见 3.2）。

默认值：
```python
def _default_review_dimensions():
    return [
        {"key": "initiative",    "label": "主动性",     "weight": 0.25},
        {"key": "understanding", "label": "理解深度",   "weight": 0.25},
        {"key": "quality",       "label": "完成质量",   "weight": 0.25},
        {"key": "delivery",      "label": "交付与沟通", "weight": 0.25},
    ]
```

### 3.2 `ActionItem` 新增字段
```python
due_date       = models.DateField(null=True, blank=True, verbose_name="截止日期")
scores         = models.JSONField(default=dict, blank=True, verbose_name="维度评分")  # {dim_key: 1..5}
review_comment = models.TextField(blank=True, default="", verbose_name="总评")
reviewed_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="+", verbose_name="评分人")
reviewed_at    = models.DateTimeField(null=True, blank=True, verbose_name="评分时间")
review_dimensions = models.JSONField(default=list, blank=True, verbose_name="本任务维度")
# review_dimensions: [{key,label,weight}] —— 派发时从库快照；管理者逐任务可勾选子集/临时加维度/调权重
```
保留不动（不再展示）：`points`、`quality_factor`、`earned_points` 属性。

新增只读属性：
```python
@property
def overall_score(self):
    """按**本任务自己的** review_dimensions 权重对已打分维度加权平均（1-5）；未打分返回 None。"""
    # 用 self.review_dimensions 的 weight（为空则回退到 KPIScoringConfig 默认池）；
    # 只对 self.scores 中存在的维度计算，并按其权重和重新归一化；
    # 全部未打分返回 None。
```

### 3.3 迁移
单条迁移，全部为新增可空字段，**零数据风险**。

## 4. 后端 API 变更（`backend/apps/kpi/plan_views.py`、`urls.py`）

### 4.1 派发任务（新增）
`POST /api/kpi/tasks/dispatch/` — 权限 `FullDjangoModelPermissions`
- body：`{user_id, title, due_date(必填), description?, measurable_target?, priority?, review_dimensions?}`
- 逻辑：
  1. 取目标用户当月 `ImprovementPlan`（period=当前 `YYYY-MM`）；不存在则创建，`source_kpi_scores={}`。
  2. 确保 `status=published`（draft/archived 一律置为 published，员工立即可见）。
  3. 创建 `ActionItem(source=manager, status=pending, due_date=..., review_dimensions=传入值 或 从库快照)`，`sort_order` 取末位。
  4. 返回新建的 `ActionItem`。
- URL：`path("tasks/dispatch/", TaskDispatchView.as_view(), name="task-dispatch")`

### 4.2 提交反馈（改 `ActionItemStatusView`）
- 员工 `in_progress→submitted` 时，body 可带可选 `note` + `attachment`；若有则在同一请求内创建一条 `ActionItemComment`（成果/提交说明，支持线上/线下反馈）。
- 状态机不变：`pending→in_progress→submitted`，仅本人可操作。

### 4.3 评分（改 `ActionItemVerifyView`）
- body 改为：`{status: "verified"|"not_achieved", scores: {dim_key: 1..5}, review_comment(必填非空), review_dimensions?}`
- 可同时带 `review_dimensions`：评分前对本任务维度的最终调整（勾选/加维度/调权重），随评分一并落到该任务。
- 校验：`scores` 的 key 必须属于**本任务的** `review_dimensions`；值 ∈ [1,5]；`review_comment` 必填。
- 保存：`scores`、`review_comment`、`reviewed_by=request.user`、`reviewed_at=now`、`status`。
- **不再要求 `quality_factor`**；可选地按 `overall_score` 自动反推一个**隐藏**的 `quality_factor`（如 [1,2)→0.5、[2,3)→0.8、[3,4.5)→1.0、[4.5,5]→1.2），供日后恢复奖赏，UI 不展示。
- 顺手修复：现有前端"未达成"传 `'failed'`、后端只认 `'not_achieved'` 的不一致。

### 4.4 配置读取（改 `KPIScoringConfigView`）
- `GET /api/kpi/scoring-config/` 输出 `review_dimensions`，供前端点评弹窗渲染用哪些维度。
- **写入走 Django admin**（见 5.4），本期前端不提供维度编辑。`KPIScoringConfigView` 若已支持 `PUT` 整份配置可顺带带上 `review_dimensions`，但不依赖。

### 4.5 序列化器（`plan_serializers.py`）
- `ActionItemSerializer` 增加只读输出：`scores`、`review_comment`、`overall_score`、`due_date`、`reviewed_by_name`、`reviewed_at`。
- `points`/`quality_factor`/`earned_points` 继续返回（前端不展示即可），降低恢复成本。

## 5. 前端变更（`frontend/app/pages/app/ai/`）

### 5.1 员工「我的任务」(`my-plan.vue`)
- 标题 `我的提升计划` → `我的任务`。
- **隐藏奖赏**：删/隐 `总分值` 卡、`已得分` 卡（保留 `行动项数量`、`完成进度`）；隐每项 `{{ item.points }}分`；验收行的 `实得 X分 (×系数)` 改为**点评展示**。
- **点评展示**：`verified` 时显示各维度 1-5 星 + 总评（`review_comment`），让员工明确知道差在哪。
- **执行反馈**：点"提交完成"时弹出"提交说明"输入（可附图），随状态一起提交。
- **截止日期**：每项显示 `due_date`，逾期高亮。
- 历史区隐藏分数，改为完成情况；空态文案 → `暂无派发给你的任务`。

### 5.2 管理者「团队任务」(`plans/index.vue`)
- 顶部新增「**派发任务**」按钮 → 弹窗（选成员 + 标题 + 截止日期 + 优先级 + 描述/目标）→ 调 dispatch。
- 列表列把 `总积分`/`已得积分` 换为监督信号：`进行中` / `待验收` / `已完成`（可含逾期计数）。
- 「批量生成草案」属奖赏期 AI 流程，本期**隐藏**。

### 5.3 点评页 (`plans/[id].vue`) 与派发弹窗
- **维度编辑器（派发弹窗与点评处共用的组件）**：默认从库带出维度 → 可勾选子集 / 临时加一条（key+label+weight）/ 调每维权重；保存即写入该任务的 `review_dimensions`。
- "验收"区改为：按**本任务维度**逐项 **1-5 星打分 + 总评必填 textarea + 已验收/未达成**。
- 隐藏编辑行动项时的"积分"输入框；保留标题/目标/描述/优先级/截止日期/维度。

### 5.4 维度配置（Django admin）
- 在 `backend/apps/kpi/admin.py` 用 `solo` + `unfold` 注册 `KPIScoringConfig` 单例（`SingletonModelAdmin`），`review_dimensions` 以 JSON 表单在 Django admin 直接编辑——满足"管理员可配置"，**不做独立前端配置页**。
- 现有前端 `/app/settings/kpi-scoring` 页不需为本期改动。

### 5.5 导航/文案
- `useNavigation.ts` 中相关项文案按"任务"口径微调（路由不变）。

### 5.6 工作台首页 (`home.vue`)
- 现有"我的提升计划"卡（调 `/api/kpi/plans/me/`、显示 `分/已得分`、`item.points`）**改造为"我的任务"待办清单**：
  - 复用"我的待办"的 `todo-row` 样式：优先级点 + 标题 + **截止日期/逾期标记** + 状态徽标；逐条链接到 `/app/ai/my-plan`。
  - 只列未完成（`pending`/`in_progress`，逾期或高优先在前）；**隐藏一切分数**。
  - 数据沿用 `/api/kpi/plans/me/`（改造 `fetchPlanSummary`），不新增接口（可选：用预留但未启用的 `ActionItemBriefSerializer` 加一个轻量 `GET /api/kpi/tasks/me/`）。
- 与"我的待办"(issue) **并列为各自独立卡**（任务与工单详情页不同），不合并成一个清单。

## 6. 闭环与角色流转

```
管理者                                员工
  │  派发任务(必填截止日期) ──────────▶  我的任务出现新条目(pending)
  │                                     │ 开始执行 (pending→in_progress)
  │                                     │ 提交完成 + 提交说明/附件 (→submitted)
  │  ◀──── 待验收提醒                   │
  │  按维度打分(1-5★)+总评             │
  │  已验收 / 未达成 ─────────────────▶ 我的任务看到星级+总评(verified/not_achieved)
```

## 7. 隐藏 vs 删除（奖赏恢复路径）
- 所有奖赏字段仅 UI 隐藏、数据保留。
- 恢复时：撤销 UI 隐藏 + 按 `overall_score → quality_factor` 映射回填即可，**无需数据迁移**。

## 8. 边界与校验
- **当月计划唯一**：`unique_together=(user, period)` 不变；派发命中即复用，draft/archived 一律置 published。
- **可见性**：`MyPlanView` 仅取 `status in (published, archived)`；派发即 published → 立即可见。
- **权限**：派发/评分需 `change_improvementplan`；员工仅能改自己条目状态。
- **评分校验**：`scores` 的 key 属于**本任务** `review_dimensions`、星值 1-5、总评非空。
- **综合分**：按**本任务维度**权重、仅对已打分维度归一化求平均；全空为 `None`。
- **维度快照**：任务持有自己的 `review_dimensions`；admin 改库只影响**新**派发的任务，历史任务的维度与评分不变。
- **截止日期**：派发必填；逾期仅作前端高亮提醒，不自动改状态。

## 9. 测试（`backend/tests/`，pytest）
- `test_task_dispatch`：派发创建/复用当月计划、置 published、必填 due_date 校验、权限。
- `test_action_item_review`：评分保存 scores/总评/评分人、`scores` 须属于本任务维度、星值校验、总评必填、`not_achieved` 路径、按本任务权重的 `overall_score` 计算。
- `test_dispatch_dimension_snapshot`：派发默认从库快照 `review_dimensions`；传入值可覆盖；admin 改库后旧任务维度不变。
- `test_status_submit_with_note`：提交带说明生成评论；非本人 403。
- `test_review_dimensions_config`：维度库读取与默认值。
- 前端：`npx nuxi typecheck` 通过；关键流程手动/QA 验证。

## 10. 分期
- **P0 核心闭环**：模型字段（含逐任务 `review_dimensions`）+ 迁移 + 派发接口 + 评分接口改造 + 维度编辑器 + 注册 `KPIScoringConfig` 单例到 admin + `my-plan.vue`/`plans/[id].vue` 改造 + **工作台"我的任务"待办** + 隐藏奖赏 + 后端测试。
- **P1 监督增强**：团队任务监督列、"待我验收"队列、逾期提醒。

## 11. 不做（YAGNI）
- 不引入新的任务/工单模型。
- 不恢复任何奖赏/计件/段位展示。
- 不做自动评分；评分一律人工。
- 不做跨月任务聚合视图（保留月度归桶）。
```