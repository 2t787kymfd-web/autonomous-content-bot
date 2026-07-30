"""
state.py
--------
Polymarket版でいう「残高がゼロになったら消滅」に相当する、
このボットの生存状態(残高・稼働ログ)を管理する。

状態は JSON ファイルに永続化するので、プロセスを再起動しても
これまでの収支履歴を引き継げる。
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")


def load_state(starting_balance: float) -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {
            "balance_usd": starting_balance,
            "alive": True,
            "history": [],
            "published_slugs": [],
        }
    # 旧バージョンのstate.jsonにも新フィールドを補う(マイグレーション)
    state.setdefault("content_corpus", [])
    state.setdefault("niche_stats", {})
    state.setdefault("last_fixed_cost_at", None)
    return state


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def log_event(
    state: dict, kind: str, detail: str, delta_usd: float = 0.0, niche: Optional[str] = None
) -> None:
    state["balance_usd"] = round(state["balance_usd"] + delta_usd, 4)
    state["history"].append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,       # cost | revenue | publish | terminate 等
            "detail": detail,
            "delta_usd": delta_usd,
            "balance_after": state["balance_usd"],
            "niche": niche,
        }
    )


def get_existing_texts(state: dict) -> List[str]:
    """品質ゲートの類似度チェック用に、これまで公開した本文をサイクルをまたいで復元する。"""
    return [entry["text"] for entry in state["content_corpus"]]


def record_content(state: dict, niche: str, slug: str, text: str) -> None:
    """公開したコンテンツをcontent_corpusに記録する。同じslug(=ツールの安定URL)への
    再公開は新規追加せず上書きする(データ更新のたびにcorpusが無限に膨らむのを防ぐ)。"""
    now = datetime.now(timezone.utc).isoformat()
    for entry in state["content_corpus"]:
        if entry["slug"] == slug:
            entry["niche"] = niche
            entry["text"] = text
            entry["published_at"] = now
            return
    state["content_corpus"].append(
        {"slug": slug, "niche": niche, "text": text, "published_at": now}
    )


def slug_to_niche(state: dict, slug: str) -> Optional[str]:
    for entry in state["content_corpus"]:
        if entry["slug"] == slug:
            return entry["niche"]
    return None


def update_niche_stats(
    state: dict, niche: str, cost_delta: float = 0.0, revenue_delta: float = 0.0
) -> None:
    stats = state["niche_stats"].setdefault(
        niche,
        {
            "total_cost": 0.0,
            "total_revenue": 0.0,
            "cycles_run": 0,
            "status": "active",
            "revenue_observed": False,
            "revenue_observed_at_cycle": None,
        },
    )
    stats["total_cost"] = round(stats["total_cost"] + cost_delta, 4)
    stats["total_revenue"] = round(stats["total_revenue"] + revenue_delta, 4)
    if cost_delta != 0.0:
        stats["cycles_run"] += 1
    if revenue_delta != 0.0 and not stats["revenue_observed"]:
        # AdSense未承認/manual CSV未記入の間はrevenue_delta=0が続くため、
        # 「収益データが一度でも来たか」と「来てから何サイクル経ったか」を
        # 打ち切り判定の前提条件にする(広告収益は表示され始めてから
        # 実際に積み上がるまで日〜週単位のラグがあるため)
        stats["revenue_observed"] = True
        stats["revenue_observed_at_cycle"] = stats["cycles_run"]


def apply_fixed_cost(state: dict, monthly_fixed_cost_usd: float) -> None:
    """サーバー代等の固定費を、前回按分してからの実経過時間に応じて日割りで残高から
    差し引く。cronの実行間隔(30分毎等)にハードコードで依存せず、実際に経過した
    時間ベースで按分するため、間隔を変更しても自動的に正しく按分され続ける。"""
    now = datetime.now(timezone.utc)
    last_at = state.get("last_fixed_cost_at")
    if last_at is None:
        # 初回はまだ経過時間が無いため課金せず、起点だけ記録する
        state["last_fixed_cost_at"] = now.isoformat()
        return
    elapsed_days = (now - datetime.fromisoformat(last_at)).total_seconds() / 86400
    if elapsed_days <= 0:
        return
    cost = monthly_fixed_cost_usd * elapsed_days / 30
    log_event(state, "cost", f"サーバー固定費(按分、経過{elapsed_days:.3f}日分)", -cost)
    state["last_fixed_cost_at"] = now.isoformat()


def check_survival(state: dict, min_balance: float) -> bool:
    """残高がしきい値を下回ったら False を返し、alive フラグを落とす。"""
    if state["balance_usd"] < min_balance:
        state["alive"] = False
        log_event(state, "terminate", "残高がしきい値を下回ったため停止")
        return False
    return True
