"""
KPI 评分引擎

compute_scores   — 根据指标计算 5 维评分 + 综合分
compute_rankings — 根据所有用户评分计算排名与百分位
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _saturate(value: float, ceiling: float) -> float:
    """将 value 映射到 0-100，ceiling 为饱和天花板。"""
    if ceiling <= 0:
        return 0.0
    return min(value / ceiling * 100, 100.0)


def _clamp(score: float) -> int:
    """将分数限制在 0-100 整数范围内。"""
    return max(0, min(100, round(score)))


def _p0p1_avg_hours(im: dict) -> float:
    """加权计算 P0/P1 平均解决时间（P0 权重 2, P1 权重 1）。

    返回加权平均小时数；如果无 P0/P1 已解决记录则返回 0。
    """
    pb = im.get("priority_breakdown", {})
    p0 = pb.get("P0", {})
    p1 = pb.get("P1", {})

    p0_resolved = p0.get("resolved", 0)
    p1_resolved = p1.get("resolved", 0)
    p0_hours = p0.get("avg_hours", 0)
    p1_hours = p1.get("avg_hours", 0)

    weighted_sum = p0_hours * p0_resolved * 2 + p1_hours * p1_resolved * 1
    total_weight = p0_resolved * 2 + p1_resolved * 1

    if total_weight == 0:
        return 0.0
    return weighted_sum / total_weight


def _p0_handling_ratio(im: dict) -> float:
    """P0 已解决 / 全部已解决 * 100。无已解决时返回 0。"""
    resolved_count = im.get("resolved_count", 0)
    if resolved_count == 0:
        return 0.0
    pb = im.get("priority_breakdown", {})
    p0_resolved = pb.get("P0", {}).get("resolved", 0)
    return p0_resolved / resolved_count * 100


def _commit_size_score(avg_size: float) -> float:
    """理想 commit 大小 50-150 行，偏离越多扣分越多。

    在 [50, 150] 内得满分 100。偏离区间用高斯衰减。
    """
    ideal_low = 50
    ideal_high = 150

    if ideal_low <= avg_size <= ideal_high:
        return 100.0

    if avg_size < ideal_low:
        deviation = ideal_low - avg_size
    else:
        deviation = avg_size - ideal_high

    # sigma=100 给出平缓的衰减曲线
    return 100.0 * math.exp(-(deviation ** 2) / (2 * 100 ** 2))


# ---------------------------------------------------------------------------
# 评分计算
# ---------------------------------------------------------------------------

# 饱和天花板值
_DAILY_RESOLVED_CEILING = 3.0       # 每天解决 3 个 = 满分
_AVG_HOURS_CEILING = 168.0          # 一周 = 最慢，用于反转
_P0P1_HOURS_CEILING = 48.0          # P0/P1 48h = 最慢
_WEIGHTED_VALUE_CEILING = 200.0     # 加权 issue 价值上限
_RESOLVED_COUNT_CEILING = 30.0      # 期间解决 30 个 = 满分
_COMMIT_VOLUME_CEILING = 100.0      # 100 commits = 满分
_REPO_BREADTH_CEILING = 5.0         # 覆盖 5 个仓库 = 满分
_FILE_TYPE_CEILING = 8.0            # 8 种文件类型 = 满分
_REPO_COVERAGE_CEILING = 5.0        # 覆盖 5 个仓库 = 满分
_HELPER_CEILING = 10.0              # 协助 10 个 issue = 满分


def compute_scores(
    issue_metrics: dict,
    commit_metrics: dict,
    prev_scores: dict | None = None,
) -> dict:
    """根据问题指标和 commit 指标计算 5 维评分 + 综合分。

    Parameters
    ----------
    issue_metrics : dict
        来自 compute_issue_metrics 的输出。
    commit_metrics : dict
        来自 compute_commit_metrics 的输出。
    prev_scores : dict | None
        上一期评分（含 efficiency, output, quality, capability 键），
        用于计算 growth。无历史数据时 growth 固定为 50。

    Returns
    -------
    dict
        包含 efficiency, output, quality, capability, growth, overall 六个键，
        值为 0-100 整数。
    """
    im = issue_metrics
    cm = commit_metrics

    # ----- Efficiency -----
    # 40% daily_resolved_avg + 40% speed (inverse avg_hours) + 20% P0/P1 speed
    daily_score = _saturate(im.get("daily_resolved_avg", 0), _DAILY_RESOLVED_CEILING)

    avg_hours = im.get("avg_resolution_hours", 0)
    if avg_hours > 0:
        # 越快越好：0h -> 100, ceiling -> 0
        speed_score = max(0.0, (_AVG_HOURS_CEILING - avg_hours) / _AVG_HOURS_CEILING * 100)
    else:
        # 没有已解决的 issue，speed 为 0
        speed_score = 0.0 if im.get("resolved_count", 0) == 0 else 100.0

    p0p1_hours = _p0p1_avg_hours(im)
    if p0p1_hours > 0:
        p0p1_speed = max(0.0, (_P0P1_HOURS_CEILING - p0p1_hours) / _P0P1_HOURS_CEILING * 100)
    else:
        pb = im.get("priority_breakdown", {})
        has_p0p1_resolved = (
            pb.get("P0", {}).get("resolved", 0) + pb.get("P1", {}).get("resolved", 0)
        ) > 0
        p0p1_speed = 100.0 if has_p0p1_resolved else 0.0

    efficiency = daily_score * 0.4 + speed_score * 0.4 + p0p1_speed * 0.2

    # ----- Output -----
    # 40% weighted_issue_value + 30% resolved_count + 20% commit volume + 10% repo breadth
    wiv_score = _saturate(im.get("weighted_issue_value", 0), _WEIGHTED_VALUE_CEILING)
    resolved_score = _saturate(im.get("resolved_count", 0), _RESOLVED_COUNT_CEILING)
    commit_vol_score = _saturate(cm.get("total_commits", 0), _COMMIT_VOLUME_CEILING)
    repo_breadth_score = _saturate(len(cm.get("repo_coverage", [])), _REPO_BREADTH_CEILING)

    output = (
        wiv_score * 0.4
        + resolved_score * 0.3
        + commit_vol_score * 0.2
        + repo_breadth_score * 0.1
    )

    # ----- Quality -----
    # 30% inv(self_bug_rate) + 25% inv(churn_rate) + 20% commit_size_score + 25% conventional_ratio
    bug_rate = cm.get("self_introduced_bug_rate", 0)
    inv_bug = (1 - bug_rate) * 100  # 0% bug = 100, 100% bug = 0

    churn = cm.get("churn_rate", 0)
    inv_churn = (1 - churn) * 100

    cs_score = _commit_size_score(cm.get("avg_commit_size", 0))

    conv_ratio = cm.get("conventional_ratio", 0)
    conv_score = conv_ratio * 100

    quality = (
        inv_bug * 0.30
        + inv_churn * 0.25
        + cs_score * 0.20
        + conv_score * 0.25
    )

    # ----- Capability -----
    # 25% file_type_breadth + 25% repo_coverage + 25% P0_handling_ratio + 25% helper_participation
    ft_score = _saturate(cm.get("file_type_breadth", 0), _FILE_TYPE_CEILING)
    rc_score = _saturate(len(cm.get("repo_coverage", [])), _REPO_COVERAGE_CEILING)
    p0_ratio = _p0_handling_ratio(im)
    helper_score = _saturate(im.get("as_helper_count", 0), _HELPER_CEILING)

    capability = (
        ft_score * 0.25
        + rc_score * 0.25
        + p0_ratio * 0.25
        + helper_score * 0.25
    )

    # ----- Growth -----
    if prev_scores and any(
        prev_scores.get(k) is not None
        for k in ("efficiency", "output", "quality", "capability")
    ):
        current = {
            "efficiency": efficiency,
            "output": output,
            "quality": quality,
            "capability": capability,
        }
        deltas = []
        for dim in ("efficiency", "output", "quality", "capability"):
            prev_val = prev_scores.get(dim)
            if prev_val is not None:
                deltas.append(current[dim] - prev_val)

        if deltas:
            avg_delta = sum(deltas) / len(deltas)
            # 将 delta 映射到 0-100：delta=0 -> 50, delta=+50 -> 100, delta=-50 -> 0
            growth = 50 + avg_delta
        else:
            growth = 50
    else:
        growth = 50

    # ----- Overall -----
    overall = (
        efficiency * 0.25
        + output * 0.25
        + quality * 0.25
        + capability * 0.15
        + growth * 0.10
    )

    return {
        "efficiency": _clamp(efficiency),
        "output": _clamp(output),
        "quality": _clamp(quality),
        "capability": _clamp(capability),
        "growth": _clamp(growth),
        "overall": _clamp(overall),
    }


# ---------------------------------------------------------------------------
# 排名计算
# ---------------------------------------------------------------------------


def compute_rankings(all_user_scores: list[dict]) -> dict:
    """根据所有用户的评分计算排名与百分位。

    Parameters
    ----------
    all_user_scores : list[dict]
        格式 [{"user_id": ..., "scores": {"efficiency": N, ..., "overall": N}}, ...]

    Returns
    -------
    dict
        {user_id: {"efficiency_percentile": N, ..., "overall_rank": N, "total_developers": N}}
    """
    n = len(all_user_scores)
    if n == 0:
        return {}

    dimensions = ("efficiency", "output", "quality", "capability", "growth", "overall")
    result: dict = {}

    # 提取每维度分数列表
    dim_scores: dict[str, list[tuple]] = {}
    for dim in dimensions:
        scored = [
            (entry["user_id"], entry["scores"].get(dim, 0))
            for entry in all_user_scores
        ]
        dim_scores[dim] = scored

    # 初始化结果字典
    for entry in all_user_scores:
        uid = entry["user_id"]
        result[uid] = {"total_developers": n}

    # 计算百分位和排名
    for dim in dimensions:
        scores_list = dim_scores[dim]
        values = [s[1] for s in scores_list]

        for uid, score in scores_list:
            if n == 1:
                percentile = 50
            else:
                count_below = sum(1 for v in values if v < score)
                percentile = round(count_below / (n - 1) * 100)

            result[uid][f"{dim}_percentile"] = percentile

        # 按分数降序排名
        sorted_scores = sorted(scores_list, key=lambda x: x[1], reverse=True)
        for rank, (uid, _score) in enumerate(sorted_scores, start=1):
            result[uid][f"{dim}_rank"] = rank

    return result
