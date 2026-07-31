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
from . import tool_content
from .niche_scanner import discover_niches
from .researcher import research_niche
from .judge import judge_niche
from .generator import generate_article
from . import tool_builder
from .tool_builder import build_tool_html
from .quality_gate import passes_quality_gate, word_count
from .revenue_tracker import fetch_revenue
from .reinvestment import decide_reinvestment

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

# 1サイクルあたりのおおよそのAPI利用コスト(概算・要調整)
# 記事生成(generator.py)はAnthropic APIで2000トークン規模の生成を伴うため高め、
# ツール更新(tool_builder.py)はAI生成を伴わずjudge.pyの短い呼び出しのみのため大幅に安い。
# 説明文/FAQ生成(generator.generate_tool_description)はkind単位で初回のみ発生する
# (tool_content.jsonにキャッシュされ2回目以降は呼ばれないため、通常運用への影響は小さい)。
# 実際のAnthropic請求額とstate.json上のコスト合計は定期的に(例: 月イチ)突き合わせて調整すること。
ESTIMATED_COST_PER_ARTICLE_GENERATION_USD = 0.05
ESTIMATED_COST_PER_TOOL_REFRESH_USD = 0.005
ESTIMATED_COST_PER_DESCRIPTION_GENERATION_USD = 0.02


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

    # 記事の類似度チェックは「別ニッチとの比較」のみを行う。同一ニッチの
    # 更新(データが変わっただけで文章の骨子は似る)を別ニッチとの重複と
    # 誤判定して却下しないようにするため(ツールが安定slugで自分自身の
    # 直前バージョンと比較されないのと同じ理由。このサイクル内で新たに
    # 生成された記事も、後続の別ニッチとの比較対象に加える必要があるため
    # session_article_textsで(ニッチ名, 本文)を保持する)。
    session_article_texts: list[tuple[str, str]] = []

    for niche in niches:
        try:
            # 3a. リサーチ
            research = research_niche(niche)
            if not research.has_unique_data:
                raise ValueError(
                    f"'{niche}' には独自データがないため生成をスキップします。"
                )

            # 3b. 判断(このギャップを埋める価値があるか)。
            # judge.pyの基準(「記事としての差別化」)はツール(決定的な計算機/
            # ダッシュボード)には本質的に不適切なため免除する。ツールは文章の
            # 独自性ではなく機能の実用性で価値を持ち、既にtest_plugin()での
            # 実データ疎通確認・quality_gateの文字数下限を通過している
            # (quality_gateの類似度チェックをツールに適用しないのと同じ理由)。
            if not tool_builder.is_tool_kind(research.kind):
                judgement = judge_niche(niche, research)
                if not judgement.worth_pursuing:
                    print(f"[main_loop] '{niche}' は判断ステップで却下: {judgement.reason}")
                    continue

            # 3c. ツール生成を優先(決定的なHTML+JS、対応データ種別のみ)。
            # 説明文/FAQはkind単位で初回のみAI生成し、tool_descriptions.jsonに
            # キャッシュして使い回す(毎サイクル呼ぶとコスト・レイテンシが無駄なため)。
            tool_content_store = tool_content.load()
            was_description_cached = research.kind in tool_content_store
            kind_content = tool_content.get_or_generate(
                tool_content_store, research.kind, niche, research.raw_data, research.sources
            )
            if not was_description_cached:
                tool_content.save(tool_content_store)
                state_mod.log_event(
                    st, "cost",
                    f"kind '{research.kind}' の説明文/FAQ生成コスト(初回のみ)",
                    -ESTIMATED_COST_PER_DESCRIPTION_GENERATION_USD,
                )

            tool_html = build_tool_html(research, kind_content["description"], kind_content["faq"])
            from .publisher import publish_tool, publish_article

            dry_run = config["mode"] == "dry_run"

            if tool_html is not None:
                # ツールは「同じニッチの最新データへの更新」が目的であり、記事のような
                # 量産スパムのリスクが無い(むしろ更新されないことの方が実利用上の問題に
                # なる)ため、既存コンテンツとの類似度チェックの対象外にする(安定slugで
                # 自分自身の直前バージョンとしか比較されず、データの一部更新だけでも
                # 高類似度で誤って弾かれてしまうため)。ただし「薄いコンテンツ」防止の
                # 文字数下限だけは記事と同じ基準で適用する(説明文が加わったことで
                # 実質的に満たせるようになったため復活させる)。
                text_for_corpus = research.data_summary + "\n\n" + kind_content["description"]
                min_wc = config["quality_gate"]["min_word_count"]
                wc = word_count(text_for_corpus)
                if wc < min_wc:
                    print(
                        f"[main_loop] '{niche}' はツール品質ゲートで却下: "
                        f"文字数不足 ({wc} < {min_wc})"
                    )
                    continue
                slug = publish_tool(niche, tool_html, config["publish"]["output_dir"], dry_run, kind=research.kind)
                cost = ESTIMATED_COST_PER_TOOL_REFRESH_USD
                cost_label = "ツール更新"
            else:
                # 3d. 対応ツールが無いニッチは記事生成にフォールバック
                text_for_corpus = generate_article(research)
                other_niche_texts = state_mod.get_existing_texts(st, exclude_niche=niche) + [
                    t for n, t in session_article_texts if n != niche
                ]
                ok, reason = passes_quality_gate(
                    text_for_corpus,
                    other_niche_texts,
                    config["quality_gate"]["min_word_count"],
                    config["quality_gate"]["max_similarity_ratio"],
                )
                if not ok:
                    print(f"[main_loop] '{niche}' は品質ゲートで却下: {reason}")
                    continue
                slug = publish_article(niche, text_for_corpus, config["publish"]["output_dir"], dry_run, kind=research.kind)
                session_article_texts.append((niche, text_for_corpus))
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

        except Exception as e:
            # ValueError(独自データ無し等の意図的な却下)に限らず、AI APIエラー
            # (例: Anthropicクレジット残高不足)やプラグイン側の予期せぬ例外も
            # ここで1ニッチ分だけスキップする。狭くValueErrorのみを捕捉していると、
            # 1ニッチのAI呼び出し失敗でサイクル全体が停止し、他の(AI不要な)
            # ニッチも巻き込んで一切公開されなくなってしまうため。
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

    # 固定費按分(サーバー代等。前回からの実経過時間に応じて日割りで差し引く)
    state_mod.apply_fixed_cost(st, survival["monthly_fixed_cost_usd"])

    state_mod.save_state(st)
    print(f"[main_loop] サイクル終了。現在の残高: ${st['balance_usd']:.2f}")


if __name__ == "__main__":
    run_cycle()
