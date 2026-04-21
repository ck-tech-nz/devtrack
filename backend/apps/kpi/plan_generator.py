"""
提升计划行动项生成引擎

根据 KPI 评分差距和指标短板，生成结构化的行动项。
"""

from __future__ import annotations

MAX_ITEMS = 8

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def generate_action_items(
    scores: dict,
    issue_metrics: dict,
    commit_metrics: dict,
    team_avgs: dict | None,
) -> list[dict]:
    """根据 KPI 数据生成结构化行动项列表。

    Returns
    -------
    list[dict]
        每项包含 dimension, title, description, measurable_target, points, priority, source
    """
    team_avgs = team_avgs or {}
    items: list[dict] = []
    im = issue_metrics
    cm = commit_metrics

    # 1) 效率低于团队均值
    team_eff = team_avgs.get("efficiency")
    if team_eff and scores.get("efficiency", 100) < team_eff:
        daily_avg = im.get("daily_resolved_avg", 0)
        target = round(daily_avg * 1.5, 1) if daily_avg > 0 else 2.0
        items.append({
            "dimension": "efficiency",
            "title": f"提高日均解决量至 {target} 个",
            "description": "关注问题分解和时间管理，优先处理高优先级问题",
            "measurable_target": f"日均解决 ≥ {target}",
            "points": 30,
            "priority": "high",
            "source": "ai_generated",
        })

    # 2) P0/P1 响应慢
    pb = im.get("priority_breakdown", {})
    p0_hours = pb.get("P0", {}).get("avg_hours", 0)
    p1_hours = pb.get("P1", {}).get("avg_hours", 0)
    max_p0p1 = max(p0_hours, p1_hours)
    if max_p0p1 > 24:
        items.append({
            "dimension": "efficiency",
            "title": "P0/P1 响应时间控制在 24h 内",
            "description": "建立紧急响应机制，P0 问题收到后立即处理",
            "measurable_target": "P0/P1 平均解决时间 < 24h",
            "points": 30,
            "priority": "high",
            "source": "ai_generated",
        })

    # 3) Bug 率过高
    bug_rate = cm.get("self_introduced_bug_rate", 0)
    if bug_rate > 0.1:
        pct = round(bug_rate * 100, 1)
        items.append({
            "dimension": "quality",
            "title": "自引 Bug 率降至 10% 以下",
            "description": f"当前 Bug 率 {pct}%，建议加强代码自测和 Code Review",
            "measurable_target": "自引 Bug 率 < 10%",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 4) Churn 率过高
    churn = cm.get("churn_rate", 0)
    if churn > 0.2:
        pct = round(churn * 100, 1)
        items.append({
            "dimension": "quality",
            "title": "代码 Churn 率控制在 20% 以下",
            "description": f"当前 Churn 率 {pct}%，建议加强需求理解和设计评审",
            "measurable_target": "Churn 率 < 20%",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 5) 规范提交率低
    conv = cm.get("conventional_ratio", 0)
    total_commits = cm.get("total_commits", 0)
    if total_commits > 0 and conv < 0.5:
        items.append({
            "dimension": "quality",
            "title": "Conventional Commits 比率提升至 50%",
            "description": f"当前规范提交率 {round(conv * 100)}%，使用 feat:/fix:/refactor: 等前缀",
            "measurable_target": "规范提交比率 ≥ 50%",
            "points": 10,
            "priority": "low",
            "source": "ai_generated",
        })

    # 6) 提交过大
    avg_size = cm.get("avg_commit_size", 0)
    if avg_size > 300:
        items.append({
            "dimension": "quality",
            "title": "单次提交控制在 150 行以内",
            "description": f"当前平均 {round(avg_size)} 行/次，建议拆分为更小的原子提交",
            "measurable_target": "平均提交大小 < 150 行",
            "points": 10,
            "priority": "low",
            "source": "ai_generated",
        })

    # 7) 仓库覆盖不足
    repo_count = len(cm.get("repo_coverage", []))
    if repo_count < 2:
        items.append({
            "dimension": "capability",
            "title": "参与至少 2 个仓库的开发",
            "description": "拓展技术广度，参与不同项目的开发",
            "measurable_target": "有提交的仓库数 ≥ 2",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 8) 无协助
    helper_count = im.get("as_helper_count", 0)
    if helper_count == 0:
        items.append({
            "dimension": "capability",
            "title": "本月协助处理至少 2 个他人问题",
            "description": "提升团队协作能力，主动协助同事解决问题",
            "measurable_target": "协助问题数 ≥ 2",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 按优先级排序，截断至 MAX_ITEMS
    items.sort(key=lambda x: PRIORITY_ORDER.get(x["priority"], 99))
    return items[:MAX_ITEMS]
