"""
main_loop.py
-------------
Polymarket版の「10分おきに:スキャン→確率計算→賭ける→運用費を抜く」
ループに相当する、コンテンツ版の自律ループ。

  1. 生存チェック(残高がしきい値以上か)
  2. ニッチ探索
  3. 各ニッチについて: リサーチ → 生成 → 品質ゲート → 公開
  4. コスト(API利用料・固定費按分)を残高から差し引く
  5. 収益を取得して残高に加算
  6. 状態を保存

cron等で `python -m src.main_loop` を定期実行する想定。
"""

import sys
import yaml
import os

from . import state as state_mod
from .niche_scanner import discover_niches
from .researcher import research_niche
from .judge import judge_niche
from .generator import generate_article
from .tool_builder import build_tool_html
from .quality_gate import passes_quality_gate
from .revenue_tracker import fetch_revenue
from .reinvestment import decide_reinvestment

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

# 1サイクルあたりのおおよそのAPI利用コスト(概算・要調整)
# 記事生成(generator.py)はAnthropic APIで2000トークン規模の生成を伴うため高め、
# ツール更新(tool_builder.py)はAI生成を伴わずjudge.pyの短い呼び出しのみのため大幅に安い。
# 実際のAnthropic請求額とstate.json上のコスト合計は定期的に(例: 月イチ)突き合わせて調整すること。
ESTIMATED_COST_PER_ARTICLE_GENERATION_USD = 0.05
ESTIMATED_COST_PER_TOOL_REFRESH_USD = 0.005


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_cycle() -> None:
    config = load_config()
    survival = config["survival"]
    st = state_mod.load_state(survival["starting_balance_usd"])

    if not st["alive"]:
        print("[main_loop] このボットは既に停止しています(残高切れ)。")
        return

    # 1. 生存チェック
    if not state_mod.check_survival(st, survival["min_balance_to_operate_usd"]):
        state_mod.save_state(st)
        print("[main_loop] 残高がしきい値未満のため停止しました。")
        return

    # 2. 再投資判断(儲かっているニッチを優先、打ち切り対象を除外)
    priority_niches, abandoned_niches = decide_reinvestment(st, config)
    if priority_niches:
        print(f"[main_loop] 再投資で優先するニッチ: {priority_niches}")
    if abandoned_niches:
        print(f"[main_loop] 打ち切り対象のニッチ: {abandoned_niches}")

    # 3. ニッチ探索
    niches = discover_niches(
        config["seed_niches"],
        config["niches_per_cycle"],
        priority_niches=priority_niches,
        abandoned_niches=abandoned_niches,
    )
    print(f"[main_loop] 今サイクルで評価するニッチ: {niches}")
    if not niches:
        print(
            "[main_loop] 警告: 評価対象のニッチが0件です。seed_niches が全て打ち切り"
            "(abandoned)されたか、関連ワードが尽きた可能性があります。config.yaml の"
            "seed_niches追加、または researcher.py/tool_builder.py への対応データ種別"
            "(kind)追加が必要です。このサイクルは何も生成せず終了します。"
        )

    existing_texts: list[str] = state_mod.get_existing_texts(st)

    for niche in niches:
        try:
            # 3a. リサーチ
            research = research_niche(niche)
            if not research.has_unique_data:
                raise ValueError(
                    f"'{niche}' には独自データがないため生成をスキップします。"
                )

            # 3b. 判断(このギャップを埋める価値があるか)
            judgement = judge_niche(niche, research)
            if not judgement.worth_pursuing:
                print(f"[main_loop] '{niche}' は判断ステップで却下: {judgement.reason}")
                continue

            # 3c. ツール生成を優先(決定的なHTML+JS、対応データ種別のみ)
            tool_html = build_tool_html(research)
            from .publisher import publish_tool, publish_article

            dry_run = config["mode"] == "dry_run"

            if tool_html is not None:
                # ツールは「同じニッチの最新データへの更新」が目的であり、記事のような
                # 量産スパムのリスクが無い(むしろ更新されないことの方が実利用上の問題に
                # なる)ため、品質ゲート(類似度チェック)の対象外にして常に上書き公開する。
                # publish_tool側で安定slug(ニッチ名のみ、タイムスタンプ無し)を使うため
                # 同じURLがデータだけ更新される。
                text_for_corpus = research.data_summary
                slug = publish_tool(niche, tool_html, config["publish"]["output_dir"], dry_run)
                cost = ESTIMATED_COST_PER_TOOL_REFRESH_USD
                cost_label = "ツール更新"
            else:
                # 3d. 対応ツールが無いニッチは記事生成にフォールバック
                text_for_corpus = generate_article(research)
                ok, reason = passes_quality_gate(
                    text_for_corpus,
                    existing_texts,
                    config["quality_gate"]["min_word_count"],
                    config["quality_gate"]["max_similarity_ratio"],
                )
                if not ok:
                    print(f"[main_loop] '{niche}' は品質ゲートで却下: {reason}")
                    continue
                slug = publish_article(niche, text_for_corpus, config["publish"]["output_dir"], dry_run)
                existing_texts.append(text_for_corpus)
                cost = ESTIMATED_COST_PER_ARTICLE_GENERATION_USD
                cost_label = "生成"

            if slug not in st["published_slugs"]:
                st["published_slugs"].append(slug)
            state_mod.record_content(st, niche, slug, text_for_corpus)

            # 4. コスト計上
            state_mod.log_event(
                st, "cost", f"'{niche}' の{cost_label}コスト", -cost, niche=niche
            )
            state_mod.update_niche_stats(st, niche, cost_delta=-cost)

        except ValueError as e:
            print(f"[main_loop] '{niche}' はスキップ: {e}")
            continue

    # 5. 収益取得(ニッチ別)
    try:
        revenue_by_niche = fetch_revenue(config["revenue"]["source"], st)
    except RuntimeError as e:
        print(f"[main_loop] 収益取得をスキップ: {e}")
        revenue_by_niche = {}

    for niche, amount in revenue_by_niche.items():
        if amount == 0:
            continue
        state_mod.log_event(st, "revenue", f"'{niche}' の収益取得", amount, niche=niche)
        if niche != "_unattributed":
            state_mod.update_niche_stats(st, niche, revenue_delta=amount)

    # 固定費按分(簡易的に1日1回想定なら月次固定費/30などにする。ここでは月次分をそのまま例示)
    # state_mod.log_event(st, "cost", "サーバー固定費", -survival["monthly_fixed_cost_usd"] / 30)

    state_mod.save_state(st)
    print(f"[main_loop] サイクル終了。現在の残高: ${st['balance_usd']:.2f}")


if __name__ == "__main__":
    run_cycle()
