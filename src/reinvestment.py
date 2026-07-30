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

安全装置(二段構え): 広告収益は表示され始めてから実際に積み上がるまで
日〜週単位のラグがあるため、コストの積み上がりだけを見て早計に
打ち切ると、本来有望なニッチまで潰しかねない。
1. AdSense未承認・manual CSV未記入などで収益データが一度も来ていない
   ニッチ(`niche_stats.revenue_observed=False`)は、そもそも打ち切り
   判定の対象外にする。
2. 収益データが来始めた直後(`revenue_observed_at_cycle`から
   `min_cycles_after_revenue`サイクル未満)も判定を保留する。
   収益が「入り始めたばかりでまだ少ない」状態と「本当に儲からない」
   状態を区別するため。
config.yaml の reinvestment.enabled を False にすれば、再投資判断
そのものを丸ごと無効化することもできる。
"""

from typing import List, Tuple


def decide_reinvestment(state: dict, config: dict) -> Tuple[List[str], List[str]]:
    reinvestment_cfg = config.get("reinvestment", {})
    if not reinvestment_cfg.get("enabled", True):
        return [], []

    min_cycles = reinvestment_cfg.get("min_cycles_before_judgement", 3)
    min_cycles_after_revenue = reinvestment_cfg.get("min_cycles_after_revenue", 3)
    loss_threshold = reinvestment_cfg.get("loss_threshold_usd", -1.00)

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
            continue

        if not stats.get("revenue_observed", False):
            continue  # 収益データが一度も来ていない間は打ち切り判定しない

        cycles_since_revenue = stats["cycles_run"] - stats["revenue_observed_at_cycle"]
        if cycles_since_revenue < min_cycles_after_revenue:
            continue  # 収益が入り始めたばかりの間も打ち切り判定を保留

        if pnl < loss_threshold:
            stats["status"] = "abandoned"
            abandoned_niches.append(niche)

    return priority_niches, abandoned_niches
