"""kind_generator.py が自動生成したプラグイン: uv_index"""

import html
import requests
from datetime import datetime
from typing import Any

KIND_NAME = "uv_index"
KEYWORDS = ["紫外線", "UV", "uv_index", "紫外線指数", "日焼け", "UVインデックス"]
CATEGORY = "天気・防災"

# 主要都市の座標
CITY_COORDS = {
    "東京": (35.6895, 139.6917),
    "大阪": (34.6937, 135.5023),
    "名古屋": (35.1815, 136.9066),
    "札幌": (43.0618, 141.3545),
    "福岡": (33.5904, 130.4017),
    "那覇": (26.2124, 127.6809),
    "仙台": (38.2688, 140.8721),
    "広島": (34.3853, 132.4553),
    "京都": (35.0116, 135.7681),
    "神戸": (34.6901, 135.1956),
}

DEFAULT_CITY = "東京"


def _uv_level(uv: float) -> tuple:
    """UV指数からレベル名と対策を返す。"""
    if uv < 3:
        return ("低い", "🟢", "特別な対策は不要ですが、長時間の外出時は帽子を。")
    elif uv < 6:
        return ("中程度", "🟡", "日焼け止め(SPF15以上)を塗り、帽子・サングラスを着用。")
    elif uv < 8:
        return ("高い", "🟠", "日焼け止め(SPF30以上)必須。10〜14時の外出はなるべく避けて。")
    elif uv < 11:
        return ("非常に高い", "🔴", "日焼け止め(SPF50以上)必須。できるだけ屋内で過ごして。")
    else:
        return ("極端に強い", "🟣", "外出を避け、やむを得ない場合は完全防備で短時間に留めて。")


def _resolve_city(niche: str) -> tuple:
    """ニッチ名から都市名と座標を解決する。"""
    for city, coords in CITY_COORDS.items():
        if city in niche:
            return city, coords
    return DEFAULT_CITY, CITY_COORDS[DEFAULT_CITY]


def fetch(niche: str) -> tuple:
    city, (lat, lon) = _resolve_city(niche)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "uv_index_max",
        "timezone": "Asia/Tokyo",
        "forecast_days": 7,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    dates = data["daily"]["time"]
    uv_values = data["daily"]["uv_index_max"]

    # サマリ生成
    today_uv = uv_values[0] if uv_values else 0
    level_name, emoji, advice = _uv_level(today_uv if today_uv is not None else 0)
    summary = (
        f"{city}の本日の最大UV指数は {today_uv}({level_name}{emoji})です。"
        f" {advice}"
        f" 今後7日間の最大UV指数: {', '.join(str(v) for v in uv_values)}。"
    )

    sources = [
        "https://open-meteo.com/ (Open-Meteo 無料気象API)",
        "https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-(uv)-index (WHO UV指数ガイドライン)",
    ]

    raw = {
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "dates": dates,
        "uv_values": uv_values,
        "today_uv": today_uv,
        "level_name": level_name,
        "emoji": emoji,
        "advice": advice,
        "timezone": data.get("timezone", "Asia/Tokyo"),
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    city = html.escape(str(raw_data.get("city", DEFAULT_CITY)))
    dates = raw_data.get("dates", [])
    uv_values = raw_data.get("uv_values", [])
    today_uv = raw_data.get("today_uv", 0)
    level_name = html.escape(str(raw_data.get("level_name", "-")))
    emoji = html.escape(str(raw_data.get("emoji", "")))
    advice = html.escape(str(raw_data.get("advice", "")))
    fetched_at = html.escape(str(raw_data.get("fetched_at", "-")))
    lat = raw_data.get("latitude", 0)
    lon = raw_data.get("longitude", 0)

    # 今日のカード
    today_card = (
        f'<div class="uv-today-card">'
        f'<span class="uv-emoji">{emoji}</span>'
        f'<span class="uv-value tel-value">{html.escape(str(today_uv if today_uv is not None else "-"))}</span>'
        f'<span class="uv-label">本日のUV指数({level_name})</span>'
        f'<p class="uv-advice">{advice}</p>'
        f'</div>'
    )

    # 7日間テーブル
    rows = ""
    for d, v in zip(dates, uv_values):
        safe_d = html.escape(str(d))
        safe_v = html.escape(str(v if v is not None else "-"))
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            weekdays = ["月", "火", "水", "木", "金", "土", "日"]
            wday = weekdays[dt.weekday()]
            display_date = html.escape(f"{dt.month}/{dt.day}({wday})")
        except Exception:
            display_date = safe_d

        try:
            uv_float = float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            uv_float = 0.0

        lv_name, lv_emoji, _ = _uv_level(uv_float)
        safe_lv = html.escape(lv_name)
        safe_lv_emoji = html.escape(lv_emoji)

        # プログレスバー(最大15を100%とする)
        bar_pct = min(int(uv_float / 15 * 100), 100)
        rows += (
            f'<tr>'
            f'<td>{display_date}</td>'
            f'<td class="tel-value"><b>{safe_v}</b></td>'
            f'<td>{safe_lv_emoji} {safe_lv}</td>'
            f'<td><div class="uv-bar-bg"><div class="uv-bar" style="width:{bar_pct}%"></div></div></td>'
            f'</tr>'
        )

    table = (
        '<table class="uv-table">'
        '<thead><tr><th>日付</th><th>UV指数(最大)</th><th>レベル</th><th>強さ</th></tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table>'
    )

    # UV指数の目安
    guide_rows = (
        '<tr><td class="tel-value">🟢 0〜2</td><td>低い</td><td>特別な対策不要</td></tr>'
        '<tr><td class="tel-value">🟡 3〜5</td><td>中程度</td><td>日焼け止め・帽子</td></tr>'
        '<tr><td class="tel-value">🟠 6〜7</td><td>高い</td><td>SPF30以上・サングラス</td></tr>'
        '<tr><td class="tel-value">🔴 8〜10</td><td>非常に高い</td><td>SPF50以上・日陰行動</td></tr>'
        '<tr><td class="tel-value">🟣 11+</td><td>極端に強い</td><td>外出を極力回避</td></tr>'
    )
    guide = (
        '<h2>UV指数の目安(WHO基準)</h2>'
        '<table class="uv-table">'
        '<thead><tr><th>指数</th><th>レベル</th><th>推奨対策</th></tr></thead>'
        f'<tbody>{guide_rows}</tbody>'
        '</table>'
    )

    # 出典
    source_items = "".join(
        f'<li><a href="{html.escape(s.split(" ")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a></li>'
        if s.startswith("https://") else f'<li>{html.escape(s)}</li>'
        for s in sources
    )
    source_div = (
        f'<div class="source">'
        f'<b>データ出典:</b><ul>{source_items}</ul>'
        f'<small class="tel-value">座標: {html.escape(str(lat))}, {html.escape(str(lon))} / 取得日時: {fetched_at}</small>'
        f'</div>'
    )

    return (
        f'<h1>☀️ {html.escape(niche)} — {city}</h1>'
        '<p>Open-Meteo APIを使用した今後7日間の紫外線指数(UV Index)予報です。'
        'UV指数はWHO基準に基づき、日焼けや皮膚へのダメージリスクを示します。</p>'
        + today_card
        + '<h2>7日間の紫外線指数予報</h2>'
        + table
        + guide
        + source_div
    )

