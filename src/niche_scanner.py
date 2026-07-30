"""
niche_scanner.py
-----------------
「数百の予測市場をスキャンする」に相当する部分。
ここでは検索トレンドの伸びや、コンテンツが薄い(=機会がある)
トピックを探す。

本番では Google Trends (pytrends) や SerpApi 等と組み合わせて
「検索需要はあるのに、良質なツール/データ記事が少ない」ニッチを
自動発見するように拡張する。ここでは動く形の最小実装として
pytrends を使い、失敗時は config.yaml の seed_niches にフォール
バックする。
"""

from typing import List

try:
    from pytrends.request import TrendReq
except ImportError:  # サンドボックス等でネットワーク/パッケージがない場合
    TrendReq = None


def discover_niches(seed_niches: List[str], n: int) -> List[str]:
    """
    関連トレンドワードを取得して候補ニッチを広げる。
    ネットワークが使えない/失敗した場合はシードだけを返す。
    """
    candidates = list(seed_niches)

    if TrendReq is None:
        return candidates[:n]

    try:
        pytrends = TrendReq(hl="ja-JP", tz=540)
        for seed in seed_niches:
            pytrends.build_payload([seed], timeframe="now 7-d", geo="JP")
            related = pytrends.related_queries().get(seed, {})
            rising = related.get("rising")
            if rising is not None:
                candidates.extend(rising["query"].tolist()[:3])
    except Exception as e:  # ネットワーク不可・レート制限など
        print(f"[niche_scanner] トレンド取得に失敗、シードのみ使用: {e}")

    # 重複排除しつつ上位n件
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:n]
