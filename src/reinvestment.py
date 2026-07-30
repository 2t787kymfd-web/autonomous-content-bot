"""
reinvestment.py
----------------
Polymarket版でいう「勝っているポジションに追加投資し、
負けているポジションを手仕舞う」に相当する判断。

state.py の niche_stats(ニッチ別の累積コスト/収益)を見て、
- 儲かっているニッチ → 次サイクルで優先的に再探索(priority_niches)
- config.yaml の loss_threshold_usd を下回ったニッチ → 打ち切り(abandoned_niches)
を決める。judge.py 同様、まだ十分な回数を回していないニッチは
判定を保留する(min_cycles_before_judgement)。
"""

from typing import List, Tuple


def decide_reinvestment(state: dict, config: dict) -> Tuple[List[str], List[str]]:
    reinvestment_cfg = config.get("reinvestment", {})
    min_cycles = reinvestment_cfg.get("min_cycles_before_judgement", 3)
    loss_threshold = reinvestment_cfg.get("loss_threshold_usd", -0.20)

    priority_niches: List[str] = []
    abandoned_niches: List[str] = []

    for niche, stats in state["niche_stats"].items():
        if stats["status"] == "abandoned":
            abandoned_niches.append(niche)
            continue

        if stats["cycles_run"] < min_cycles:
            continue  # サンプル数が少なすぎる間は判定を保留

        pnl = stats["total_revenue"] + stats["total_cost"]  # total_costは負の値で記録される
        if pnl > 0:
            priority_niches.append(niche)
        elif pnl < loss_threshold:
            stats["status"] = "abandoned"
            abandoned_niches.append(niche)

    return priority_niches, abandoned_niches
