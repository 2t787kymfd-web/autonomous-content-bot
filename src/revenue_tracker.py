"""
revenue_tracker.py
--------------------
「稼いだ金から自分にシステム運用費を抜く」に相当する収益集計層。

AdSense/アフィリエイトのAPIは審査・OAuth設定が必要なため、
ここではダミーの収益源(手動入力/CSV)を実装している。
本番では以下に差し替える:
  - Google AdSense Management API
  - ASP(A8.net等)のレポートAPI
"""

import csv
import os
from typing import List, Dict

REVENUE_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "revenue_log.csv")


def fetch_revenue_manual() -> float:
    """
    data/revenue_log.csv に手動で追記した金額を合計するだけの
    プレースホルダ。列: date,amount_usd
    """
    if not os.path.exists(REVENUE_LOG_PATH):
        return 0.0
    total = 0.0
    with open(REVENUE_LOG_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += float(row["amount_usd"])
    return total


def fetch_revenue(source: str) -> float:
    if source == "manual":
        return fetch_revenue_manual()
    # TODO: adsense_api / affiliate_api の実装をここに追加
    raise NotImplementedError(f"未実装の収益ソースです: {source}")
