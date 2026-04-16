"""
KPI 建议引擎

generate_suggestions — 根据评分、指标、团队均值、历史评分生成改进建议、趋势分析和画像。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DIM_LABELS: dict[str, str] = {
    "efficiency": "效率",
    "output": "产出",
    "quality": "质量",
    "capability": "能力",
    "growth": "成长",
}

SCORE_DIMS = ("efficiency", "output", "quality", "capability", "growth")

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

PROFILES: dict[tuple[str, str], str] = {
    ("efficiency", "quality"): "快速响应型，质量有提升空间",
    ("efficiency", "capability"): "快速响应型，建议拓展技术广度",
    ("efficiency", "output"): "快速响应型，可聚焦提升产出量",
    ("efficiency", "growth"): "快速响应型，建议关注持续成长",
    ("output", "quality"): "高产出型，质量有提升空间",
    ("output", "efficiency"): "高产出型，可适当提升响应速度",
    ("output", "capability"): "高产出型，建议拓展技术广度",
    ("output", "growth"): "高产出型，建议关注持续成长",
    ("quality", "efficiency"): "精工细作型，可适当提升响应速度",
    ("quality", "output"): "精工细作型，可聚焦提升产出量",
    ("quality", "capability"): "精工细作型，建议拓展技术广度",
    ("quality", "growth"): "精工细作型，建议关注持续成长",
    ("capability", "output"): "技术全面型，可聚焦提升产出量",
    ("capability", "efficiency"): "技术全面型，可适当提升响应速度",
    ("capability", "quality"): "技术全面型，质量有提升空间",
    ("capability", "growth"): "技术全面型，建议关注持续成长",
    ("growth", "efficiency"): "成长潜力型，可适当提升响应速度",
    ("growth", "output"): "成长潜力型，可聚焦提升产出量",
    ("growth", "quality"): "成长潜力型，质量有提升空间",
    ("growth", "capability"): "成长潜力型，建议拓展技术广度",
}


# ---------------------------------------------------------------------------
# 公共接口
# ---------------------------------------------------------------------------


def generate_suggestions(
    scores: dict,
    issue_metrics: dict,
    commit_metrics: dict,
    team_avgs: dict | None,
    prev_scores: dict | None,
) -> dict:
    """
    生成改进建议、趋势分析和开发者画像。

    Parameters
    ----------
    scores : dict
        当期各维度评分，如 {"efficiency": 80, "output": 75, ...}
    issue_metrics : dict
        由 compute_issue_metrics 返回的问题指标
    commit_metrics : dict
        由 compute_commit_metrics 返回的 Commit 指标
    team_avgs : dict | None
        团队各维度平均分，如 {"efficiency": 70, ...}
    prev_scores : dict | None
        上期各维度评分（用于趋势分析）

    Returns
    -------
    dict
        {"shortcomings": [...], "trends": [...], "profile": "..."}
    """
    return {
        "shortcomings": _detect_shortcomings(scores, issue_metrics, commit_metrics, team_avgs),
        "trends": _detect_trends(scores, prev_scores),
        "profile": _generate_profile(scores),
    }


# ---------------------------------------------------------------------------
# 短板检测
# ---------------------------------------------------------------------------


def _detect_shortcomings(
    scores: dict,
    issue_metrics: dict,
    commit_metrics: dict,
    team_avgs: dict | None,
) -> list[dict]:
    """检测并返回按严重程度排序的短板列表。"""
    items: list[dict] = []

    # 1) efficiency < team_avg.efficiency
    if team_avgs and "efficiency" in team_avgs and "efficiency" in scores:
        if scores["efficiency"] < team_avgs["efficiency"]:
            avg_hours = issue_metrics.get("avg_resolution_hours", 0)
            items.append({
                "dimension": "efficiency",
                "message": f"平均解决耗时 {avg_hours}h，建议关注问题分解和时间管理",
                "severity": "medium",
            })

    # 2) self_introduced_bug_rate > 0.1
    bug_rate = commit_metrics.get("self_introduced_bug_rate", 0)
    if bug_rate > 0.1:
        pct = round(bug_rate * 100, 1)
        items.append({
            "dimension": "quality",
            "message": f"自引入 Bug 率 {pct}%，建议加强代码自测",
            "severity": "high",
        })

    # 3) churn_rate > 0.2
    churn = commit_metrics.get("churn_rate", 0)
    if churn > 0.2:
        pct = round(churn * 100, 1)
        items.append({
            "dimension": "quality",
            "message": f"代码流失率 {pct}%，部分代码稳定性不足，建议加强设计评审",
            "severity": "medium",
        })

    # 4) avg_commit_size > 300
    avg_size = commit_metrics.get("avg_commit_size", 0)
    if avg_size > 300:
        items.append({
            "dimension": "output",
            "message": f"平均每次提交 {avg_size} 行，建议拆分为更小的原子提交",
            "severity": "low",
        })

    # 5) P0 resolved / total resolved < 10% AND P0 assigned > 0
    pb = issue_metrics.get("priority_breakdown", {})
    p0_info = pb.get("P0", {})
    p0_assigned = p0_info.get("assigned", 0)
    p0_resolved = p0_info.get("resolved", 0)
    total_resolved = issue_metrics.get("resolved_count", 0)

    if p0_assigned > 0 and total_resolved > 0:
        p0_pct = round(p0_resolved / total_resolved * 100, 1)
        if p0_pct < 10:
            items.append({
                "dimension": "efficiency",
                "message": f"高优先级问题处理占比仅 {p0_pct}%，建议提升紧急响应能力",
                "severity": "medium",
            })

    # 6) conventional_ratio < 0.5 AND total_commits > 0
    conv_ratio = commit_metrics.get("conventional_ratio", 0)
    total_commits = commit_metrics.get("total_commits", 0)
    if total_commits > 0 and conv_ratio < 0.5:
        pct = round(conv_ratio * 100, 1)
        items.append({
            "dimension": "capability",
            "message": f"仅 {pct}% 的提交遵循规范格式，建议统一提交信息规范",
            "severity": "low",
        })

    # 按严重程度排序: high → medium → low
    items.sort(key=lambda x: SEVERITY_ORDER.get(x["severity"], 99))
    return items


# ---------------------------------------------------------------------------
# 趋势分析
# ---------------------------------------------------------------------------


def _detect_trends(
    scores: dict,
    prev_scores: dict | None,
) -> list[dict]:
    """检测各维度的环比变化趋势。"""
    if not prev_scores:
        return []

    trends: list[dict] = []
    dims = ("efficiency", "output", "quality", "capability")

    for dim in dims:
        curr = scores.get(dim)
        prev = prev_scores.get(dim)
        if curr is None or prev is None or prev == 0:
            continue

        change_pct = round((curr - prev) / prev * 100, 1)
        abs_change = abs(change_pct)
        label = DIM_LABELS.get(dim, dim)

        if abs_change > 10:
            if change_pct > 0:
                trends.append({
                    "dimension": dim,
                    "direction": "up",
                    "change_pct": change_pct,
                    "message": f"{label}评分本期提升 {abs_change}%，保持势头",
                })
            else:
                trends.append({
                    "dimension": dim,
                    "direction": "down",
                    "change_pct": change_pct,
                    "message": f"{label}评分本期下降 {abs_change}%，关注是否有阻塞因素",
                })
        elif abs_change >= 5:
            if change_pct > 0:
                trends.append({
                    "dimension": dim,
                    "direction": "small_up",
                    "change_pct": change_pct,
                    "message": f"{label}评分小幅提升 {abs_change}%，继续保持",
                })
            else:
                trends.append({
                    "dimension": dim,
                    "direction": "small_down",
                    "change_pct": change_pct,
                    "message": f"{label}评分小幅下降 {abs_change}%，建议留意",
                })

    return trends


# ---------------------------------------------------------------------------
# 画像生成
# ---------------------------------------------------------------------------


def _generate_profile(scores: dict) -> str:
    """根据各维度分数生成开发者画像。"""
    dim_scores = {d: scores.get(d, 0) for d in SCORE_DIMS}

    if not any(dim_scores.values()):
        return "数据不足，暂无画像"

    max_val = max(dim_scores.values())
    min_val = min(dim_scores.values())

    if max_val - min_val < 10:
        return "均衡发展型，各维度表现稳定"

    highest = max(dim_scores, key=dim_scores.get)
    lowest = min(dim_scores, key=dim_scores.get)

    profile = PROFILES.get((highest, lowest))
    if profile:
        return profile

    # 缺省组合：使用标签拼接
    high_label = DIM_LABELS.get(highest, highest)
    low_label = DIM_LABELS.get(lowest, lowest)
    return f"{high_label}突出，{low_label}有提升空间"
