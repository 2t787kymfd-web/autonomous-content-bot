"""
niche_scanner.py
-----------------
「数百の予測市場をスキャンする」に相当する部分。
ここでは検索トレンドの伸びや、コンテンツが薄い(=機会がある)
トピックを探す。

需要シグナルは pytrends の関心度、供給(既存コンテンツの多寡)シグナルは
Serper.dev(Google検索結果を安価に返すAPI)の検索結果件数を使う。
SERPER_API_KEY が未設定の場合はpytrendsの関心度のみによる
ヒューリスティック近似にフォールバックする。
"""

import math
import os
from typing import List, Optional

try:
    from pytrends.request import TrendReq
except ImportError:  # サンドボックス等でネットワーク/パッケージがない場合
    TrendReq = None

try:
    import requests
except ImportError:
    requests = None

SERPER_ENDPOINT = "https://google.serper.dev/search"
# Serper.devは従量課金/枠制限があるため、1サイクルあたりの呼び出し数を
# トレンドスコア上位の候補だけに絞って抑える
MAX_SCARCITY_LOOKUPS_PER_CYCLE = 6


def _content_scarcity_score(query: str) -> Optional[float]:
    """
    Serper.dev経由でGoogle検索結果件数を取得し、少ないほど高くなる
    希少性スコア(0〜100程度)を返す。未設定/失敗時はNone。
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key or requests is None:
        return None
    try:
        resp = requests.post(
            SERPER_ENDPOINT,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "jp", "hl": "ja"},
            timeout=10,
        )
        resp.raise_for_status()
        total = resp.json().get("searchInformation", {}).get("totalResults")
        if total is None:
            return None
        return 100.0 / (1.0 + math.log10(int(total) + 1))
    except Exception as e:  # ネットワーク不可・レート制限・クォータ切れ等
        print(f"[niche_scanner] Serper.dev呼び出しに失敗: {e}")
        return None


def discover_niches(
    seed_niches: List[str],
    n: int,
    priority_niches: Optional[List[str]] = None,
    abandoned_niches: Optional[List[str]] = None,
) -> List[str]:
    """
    関連トレンドワードを取得して候補ニッチを広げ、機会スコアでソートする。
    機会スコアは pytrends の関心度(需要)を基本とし、SERPER_API_KEY が
    設定されていればトレンドスコア上位候補について実際の検索結果件数
    (供給/既存コンテンツの多寡)も加味して補正する。Serper.dev未設定時は
    関心度のみによるヒューリスティック近似。

    priority_niches: reinvestment.py が「儲かっている」と判定したニッチ。
      スコアに関わらず優先的に候補の先頭に置く。
    abandoned_niches: 「打ち切り」判定されたニッチ。候補から除外する。
    ネットワークが使えない/失敗した場合はシードだけを返す。
    """
    priority_niches = list(priority_niches or [])
    abandoned = set(abandoned_niches or [])

    candidates = list(seed_niches)
    scores = {}

    if TrendReq is not None:
        try:
            pytrends = TrendReq(hl="ja-JP", tz=540)
            for seed in seed_niches:
                pytrends.build_payload([seed], timeframe="now 7-d", geo="JP")
                related = pytrends.related_queries().get(seed, {})
                rising = related.get("rising")
                if rising is not None:
                    candidates.extend(rising["query"].tolist()[:3])

                interest = pytrends.interest_over_time()
                if not interest.empty and seed in interest.columns:
                    scores[seed] = float(interest[seed].mean())
        except Exception as e:  # ネットワーク不可・レート制限など
            print(f"[niche_scanner] トレンド取得に失敗、シードのみ使用: {e}")

    # priority以外の候補をスコア降順(スコア無しは0点)で並べる
    rest = sorted(
        {c for c in candidates if c not in priority_niches},
        key=lambda c: scores.get(c, 0.0),
        reverse=True,
    )

    # Serper.devが使える場合、トレンドスコア上位のみ実際の検索結果件数で補正する
    if os.environ.get("SERPER_API_KEY") and rest:
        head = rest[:MAX_SCARCITY_LOOKUPS_PER_CYCLE]
        tail = rest[MAX_SCARCITY_LOOKUPS_PER_CYCLE:]
        trend_max = max((scores.get(c, 0.0) for c in head), default=0.0) or 1.0

        def _composite(c: str) -> float:
            trend_norm = scores.get(c, 0.0) / trend_max * 100
            scarcity = _content_scarcity_score(c)
            parts = [trend_norm] + ([scarcity] if scarcity is not None else [])
            return sum(parts) / len(parts)

        rest = sorted(head, key=_composite, reverse=True) + tail

    ordered = [c for c in priority_niches if c not in abandoned]
    for c in rest:
        if c not in abandoned and c not in ordered:
            ordered.append(c)

    return ordered[:n]
