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
    state["content_corpus"].append(
        {
            "slug": slug,
            "niche": niche,
            "text": text,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
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
        niche, {"total_cost": 0.0, "total_revenue": 0.0, "cycles_run": 0, "status": "active"}
    )
    stats["total_cost"] = round(stats["total_cost"] + cost_delta, 4)
    stats["total_revenue"] = round(stats["total_revenue"] + revenue_delta, 4)
    if cost_delta != 0.0:
        stats["cycles_run"] += 1


def check_survival(state: dict, min_balance: float) -> bool:
    """残高がしきい値を下回ったら False を返し、alive フラグを落とす。"""
    if state["balance_usd"] < min_balance:
        state["alive"] = False
        log_event(state, "terminate", "残高がしきい値を下回ったため停止")
        return False
    return True
