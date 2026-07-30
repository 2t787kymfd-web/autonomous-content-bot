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

import importlib
import pkgutil
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import requests

from . import kinds as kinds_pkg
from .safe_http import patched_requests

FX_API_URL = "https://api.frankfurter.app/latest"          # 無料・APIキー不要(ECBデータ)
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"  # 無料・APIキー不要
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"  # 無料・APIキー不要

FX_BASES = ["USD", "EUR", "GBP", "AUD"]
FX_TARGET = "JPY"

CRYPTO_IDS = ["bitcoin", "ethereum", "solana"]
CRYPTO_VS = ["jpy", "usd"]

CRYPTO_KEYWORDS = ["暗号", "ビットコイン", "イーサリアム", "crypto", "仮想通貨", "btc", "eth"]
WEATHER_KEYWORDS = ["天気", "気温", "weather", "降水確率", "予報"]

WEATHER_CITIES = {
    "東京": (35.6812, 139.7671),
    "大阪": (34.6937, 135.5023),
    "名古屋": (35.1815, 136.9066),
    "札幌": (43.0618, 141.3545),
    "福岡": (33.5904, 130.4017),
    "那覇": (26.2124, 127.6809),
}

WMO_WEATHER_CODE_JA = {
    0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り",
    45: "霧", 48: "霧氷",
    51: "弱い霧雨", 53: "霧雨", 55: "強い霧雨",
    61: "小雨", 63: "雨", 65: "強い雨",
    71: "小雪", 73: "雪", 75: "大雪",
    80: "にわか雨", 81: "にわか雨", 82: "激しいにわか雨",
    85: "にわか雪", 86: "強いにわか雪",
    95: "雷雨",
}


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


def _looks_like_weather(niche: str) -> bool:
    lowered = niche.lower()
    return any(k.lower() in lowered for k in WEATHER_KEYWORDS)


def _load_kind_plugins() -> List:
    """src/kinds/ 配下のプラグインモジュールを読み込む(kind_generator.pyが
    生成した新規データ種別)。KIND_NAME/KEYWORDS/fetch/build_htmlを持つ
    モジュールのみ有効なプラグインとして扱う。"""
    plugins = []
    for _, name, _ in pkgutil.iter_modules(kinds_pkg.__path__):
        try:
            mod = importlib.import_module(f".kinds.{name}", package=__package__)
        except Exception as e:
            print(f"[researcher] プラグイン'{name}'の読み込みに失敗: {e}")
            continue
        if hasattr(mod, "KIND_NAME") and hasattr(mod, "KEYWORDS") and hasattr(mod, "fetch"):
            plugins.append(mod)
    return plugins


def _looks_like_plugin(niche: str, plugin) -> bool:
    lowered = niche.lower()
    return any(k.lower() in lowered for k in plugin.KEYWORDS)


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


def _fetch_weather_data() -> tuple[str, list, dict]:
    """Open-Meteo API から主要都市の現在の天気・当日予報を取得する。"""
    lines = []
    cities_data = {}
    for city, (lat, lon) in WEATHER_CITIES.items():
        resp = requests.get(
            WEATHER_API_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "Asia/Tokyo",
                "forecast_days": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data["current_weather"]
        daily = data["daily"]
        code = current["weathercode"]
        description = WMO_WEATHER_CODE_JA.get(code, f"不明(コード{code})")
        temp = current["temperature"]
        tmax = daily["temperature_2m_max"][0]
        tmin = daily["temperature_2m_min"][0]
        precip = daily["precipitation_probability_max"][0]
        cities_data[city] = {
            "description": description,
            "temperature": temp,
            "temp_max": tmax,
            "temp_min": tmin,
            "precipitation_probability": precip,
        }
        lines.append(
            f"{city}: {description}、現在{temp}°C(最高{tmax}°C/最低{tmin}°C)、降水確率{precip}%"
        )
    fetched_at = datetime.now(timezone.utc).isoformat()
    summary = f"日本の主要都市の天気(取得時刻: {fetched_at}, Open-Meteo経由):\n" + "\n".join(lines)
    raw = {"cities": cities_data, "fetched_at": fetched_at}
    return summary, ["https://open-meteo.com/ (Open-Meteo API)"], raw


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
        elif _looks_like_weather(niche):
            summary, sources, raw = _fetch_weather_data()
            kind = "weather"
        else:
            matched_plugin = None
            for plugin in _load_kind_plugins():
                if _looks_like_plugin(niche, plugin):
                    matched_plugin = plugin
                    break
            if matched_plugin is not None:
                # マージ済み(=人間レビュー済み)のプラグインであっても、
                # nicheはpytrends等の外部影響を受けうる文字列であり、将来的に
                # URLの動的組み立てに使われる可能性を考慮して、本番実行でも
                # SSRF対策込みの安全なrequestsラッパーを常に適用する。
                # _load_kind_plugins()でのimportはpatched_requests()の外で
                # 行われており、モジュールの`requests`参照は既にその時点の
                # (本物の)requestsに束縛済みのため、ここでreloadして
                # 安全なラッパーへの束縛をやり直す必要がある。
                with patched_requests():
                    importlib.reload(matched_plugin)
                    summary, sources, raw = matched_plugin.fetch(niche)
                kind = matched_plugin.KIND_NAME
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
