"""
researcher.py
--------------
「自分で本当の確率(=価値)がどれくらいかを計算する」に相当する部分。
生成前に、そのニッチについての一次情報・データを集める。

ここは最も差別化が必要な層 = 単なるAI要約記事(scaled content
abuse扱いされやすい)にしないための核。実運用では以下のような
外部ソースに差し替える:
  - 公的統計API / 業界団体のオープンデータ
  - 為替・価格などのリアルタイムAPI
  - 自社で集計したユニークなデータセット

このテンプレートでは「本当に使える外部データがあるか」を
明示的にチェックし、無ければ生成をスキップさせる設計にしている
(=データが無いのに記事だけ量産する、を防ぐガード)。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

FX_API_URL = "https://api.frankfurter.app/latest"          # 無料・APIキー不要(ECBデータ)
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"  # 無料・APIキー不要

FX_BASES = ["USD", "EUR", "GBP", "AUD"]
FX_TARGET = "JPY"

CRYPTO_IDS = ["bitcoin", "ethereum", "solana"]
CRYPTO_VS = ["jpy", "usd"]

CRYPTO_KEYWORDS = ["暗号", "ビットコイン", "イーサリアム", "crypto", "仮想通貨", "btc", "eth"]


@dataclass
class ResearchResult:
    niche: str
    has_unique_data: bool
    data_summary: Optional[str]
    sources: list
    kind: Optional[str] = None          # "fx" | "crypto" | None
    raw_data: Optional[dict] = None     # ツール生成用の構造化データ


def _looks_like_crypto(niche: str) -> bool:
    lowered = niche.lower()
    return any(k.lower() in lowered for k in CRYPTO_KEYWORDS)


def _fetch_fx_rates() -> tuple[str, list, dict]:
    """Frankfurter API から複数通貨の対円レートを取得する。"""
    lines = []
    rates = {}
    fetched_date = None
    for base in FX_BASES:
        resp = requests.get(FX_API_URL, params={"from": base, "to": FX_TARGET}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = data["rates"][FX_TARGET]
        rates[base] = rate
        fetched_date = data["date"]
        lines.append(f"1 {base} = {rate} {FX_TARGET} (基準日: {data['date']})")
    summary = "為替レート(ECBデータ, Frankfurter API経由):\n" + "\n".join(lines)
    raw = {"target": FX_TARGET, "rates": rates, "date": fetched_date}
    return summary, ["https://frankfurter.dev (ECB公表データ)"], raw


def _fetch_crypto_rates() -> tuple[str, list, dict]:
    """CoinGecko API から暗号資産の現在価格を取得する。"""
    resp = requests.get(
        CRYPTO_API_URL,
        params={"ids": ",".join(CRYPTO_IDS), "vs_currencies": ",".join(CRYPTO_VS)},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    lines = []
    for coin_id, prices in data.items():
        price_str = ", ".join(f"{v} {cur.upper()}" for cur, v in prices.items())
        lines.append(f"{coin_id}: {price_str}")
    fetched_at = datetime.now(timezone.utc).isoformat()
    summary = f"暗号資産価格(取得時刻: {fetched_at}, CoinGecko経由):\n" + "\n".join(lines)
    raw = {"prices": data, "fetched_at": fetched_at}
    return summary, ["https://www.coingecko.com/ (CoinGecko API)"], raw


def research_niche(niche: str) -> ResearchResult:
    """
    ニッチの内容に応じて、実際に外部APIから一次データを取得する。
    取得できなければ has_unique_data=False を返し、
    main_loop 側で「生成をスキップする」安全側の挙動になる。
    """
    try:
        if _looks_like_crypto(niche):
            summary, sources, raw = _fetch_crypto_rates()
            kind = "crypto"
        else:
            summary, sources, raw = _fetch_fx_rates()
            kind = "fx"
        return ResearchResult(
            niche=niche,
            has_unique_data=True,
            data_summary=summary,
            sources=sources,
            kind=kind,
            raw_data=raw,
        )
    except Exception as e:
        # ネットワーク不可・レート制限・APIダウンなど。
        # データが取れないニッチは「生成しない」が正しい挙動。
        print(f"[researcher] '{niche}' のデータ取得に失敗: {e}")
        return ResearchResult(niche=niche, has_unique_data=False, data_summary=None, sources=[])
