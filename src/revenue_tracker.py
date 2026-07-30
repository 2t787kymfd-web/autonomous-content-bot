"""
revenue_tracker.py
--------------------
「稼いだ金から自分にシステム運用費を抜く」に相当する収益集計層。

manual(CSV手動入力)に加えて、AdSense Management API への接続を実装している。
アフィリエイトAPIは対象外(未実装のまま)。

収益は niche 別に集計して返す({niche: amount_usd})。ニッチに紐付かない
分は "_unattributed" キーにまとめる。niche への紐付けは、公開時に
state.py の content_corpus に記録した slug→niche のマッピングを使う
(AdSenseはページ単位のレポートしか返さないため)。
"""

import csv
import os
from typing import Dict

import requests

from . import state as state_mod

REVENUE_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "revenue_log.csv")
UNATTRIBUTED = "_unattributed"

ADSENSE_TOKEN_URL = "https://oauth2.googleapis.com/token"
ADSENSE_REPORTS_URL = "https://adsense.googleapis.com/v2/accounts/{account}/reports:generate"


def fetch_revenue_manual() -> Dict[str, float]:
    """
    data/revenue_log.csv に手動で追記した金額を集計する。
    列: date,amount_usd,niche (niche列は空欄可。空欄は _unattributed 扱い)
    """
    totals: Dict[str, float] = {}
    if not os.path.exists(REVENUE_LOG_PATH):
        return totals
    with open(REVENUE_LOG_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            niche = (row.get("niche") or "").strip() or UNATTRIBUTED
            totals[niche] = totals.get(niche, 0.0) + float(row["amount_usd"])
    return totals


def _adsense_access_token() -> str:
    client_id = os.environ.get("ADSENSE_CLIENT_ID")
    client_secret = os.environ.get("ADSENSE_CLIENT_SECRET")
    refresh_token = os.environ.get("ADSENSE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        raise RuntimeError(
            "AdSense連携が未設定です(ADSENSE_CLIENT_ID/ADSENSE_CLIENT_SECRET/"
            "ADSENSE_REFRESH_TOKEN を.envに設定してください)"
        )
    resp = requests.post(
        ADSENSE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_revenue_adsense(state: dict) -> Dict[str, float]:
    """
    AdSense Management API (v2) から前日分の推定収益をページ単位で取得し、
    state.content_corpus の slug→niche マッピングで niche 別に集計する。

    注意: 実アカウント未承認のため未検証。パラメータ名(dateRange/metrics/
    dimensions)は将来のAPI変更に応じて要確認。
    """
    account_id = os.environ.get("ADSENSE_ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("ADSENSE_ACCOUNT_ID が.envに設定されていません")

    access_token = _adsense_access_token()
    resp = requests.get(
        ADSENSE_REPORTS_URL.format(account=account_id),
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "dateRange": "YESTERDAY",
            "metrics": "ESTIMATED_EARNINGS",
            "dimensions": "PAGE_PATH",
        },
        timeout=15,
    )
    resp.raise_for_status()
    report = resp.json()

    totals: Dict[str, float] = {}
    for row in report.get("rows", []):
        cells = row.get("cells", [])
        if len(cells) < 2:
            continue
        page_path, earnings = cells[0]["value"], cells[1]["value"]
        slug = os.path.splitext(os.path.basename(page_path))[0]
        niche = state_mod.slug_to_niche(state, slug) or UNATTRIBUTED
        totals[niche] = totals.get(niche, 0.0) + float(earnings)
    return totals


def fetch_revenue(source: str, state: dict) -> Dict[str, float]:
    if source == "manual":
        return fetch_revenue_manual()
    if source == "adsense_api":
        return fetch_revenue_adsense(state)
    raise NotImplementedError(f"未対応の収益ソースです: {source}")
