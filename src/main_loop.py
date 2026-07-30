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
from .generator import generate_article
from .tool_builder import build_tool_html
from .quality_gate import passes_quality_gate
from .revenue_tracker import fetch_revenue

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

# 1サイクルあたりのおおよそのAPI利用コスト(概算・要調整)
ESTIMATED_COST_PER_GENERATION_USD = 0.05


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

    # 2. ニッチ探索
    niches = discover_niches(config["seed_niches"], config["niches_per_cycle"])
    print(f"[main_loop] 今サイクルで評価するニッチ: {niches}")

    existing_texts: list[str] = []  # 本来は既存記事DBから読み込む

    for niche in niches:
        try:
            # 3a. リサーチ
            research = research_niche(niche)
            if not research.has_unique_data:
                raise ValueError(
                    f"'{niche}' には独自データがないため生成をスキップします。"
                )

            # 3b. ツール生成を優先(決定的なHTML+JS、対応データ種別のみ)
            tool_html = build_tool_html(research)
            from .publisher import publish_tool, publish_article

            dry_run = config["mode"] == "dry_run"

            if tool_html is not None:
                # 品質ゲートはツールの元になったデータ要約テキストで判定する
                ok, reason = passes_quality_gate(
                    research.data_summary,
                    existing_texts,
                    min_word_count=20,  # ツールはデータ量より「実際に動くこと」が本体
                    max_similarity_ratio=config["quality_gate"]["max_similarity_ratio"],
                )
                if not ok:
                    print(f"[main_loop] '{niche}' は品質ゲートで却下: {reason}")
                    continue
                slug = publish_tool(niche, tool_html, config["publish"]["output_dir"], dry_run)
                existing_texts.append(research.data_summary)
            else:
                # 3c. 対応ツールが無いニッチは記事生成にフォールバック
                article = generate_article(research)
                ok, reason = passes_quality_gate(
                    article,
                    existing_texts,
                    config["quality_gate"]["min_word_count"],
                    config["quality_gate"]["max_similarity_ratio"],
                )
                if not ok:
                    print(f"[main_loop] '{niche}' は品質ゲートで却下: {reason}")
                    continue
                slug = publish_article(niche, article, config["publish"]["output_dir"], dry_run)
                existing_texts.append(article)

            st["published_slugs"].append(slug)

            # 4. コスト計上
            state_mod.log_event(
                st, "cost", f"'{niche}' の生成コスト", -ESTIMATED_COST_PER_GENERATION_USD
            )

        except ValueError as e:
            print(f"[main_loop] '{niche}' はスキップ: {e}")
            continue

    # 5. 収益取得
    revenue = fetch_revenue(config["revenue"]["source"])
    if revenue > 0:
        state_mod.log_event(st, "revenue", "収益取得", revenue)

    # 固定費按分(簡易的に1日1回想定なら月次固定費/30などにする。ここでは月次分をそのまま例示)
    # state_mod.log_event(st, "cost", "サーバー固定費", -survival["monthly_fixed_cost_usd"] / 30)

    state_mod.save_state(st)
    print(f"[main_loop] サイクル終了。現在の残高: ${st['balance_usd']:.2f}")


if __name__ == "__main__":
    run_cycle()
