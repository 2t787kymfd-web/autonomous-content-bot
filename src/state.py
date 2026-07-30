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

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")


def load_state(starting_balance: float) -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "balance_usd": starting_balance,
        "alive": True,
        "history": [],
        "published_slugs": [],
    }


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def log_event(state: dict, kind: str, detail: str, delta_usd: float = 0.0) -> None:
    state["balance_usd"] = round(state["balance_usd"] + delta_usd, 4)
    state["history"].append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,       # cost | revenue | publish | terminate 等
            "detail": detail,
            "delta_usd": delta_usd,
            "balance_after": state["balance_usd"],
        }
    )


def check_survival(state: dict, min_balance: float) -> bool:
    """残高がしきい値を下回ったら False を返し、alive フラグを落とす。"""
    if state["balance_usd"] < min_balance:
        state["alive"] = False
        log_event(state, "terminate", "残高がしきい値を下回ったため停止")
        return False
    return True
