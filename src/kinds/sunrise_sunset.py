"""kind_generator.py が自動生成したプラグイン: sunrise_sunset"""

import requests
import html
from datetime import datetime, timezone, timedelta

KIND_NAME = "sunrise_sunset"
KEYWORDS = ["日の出", "日の入り", "日没", "sunrise", "sunset", "日照時間", "薄明", "夜明け"]
CATEGORY = "天文・暦"

# 主要都市の緯度経度
CITY_COORDS = {
    "東京": (35.6895, 139.6917, "Asia/Tokyo"),
    "大阪": (34.6937, 135.5023, "Asia/Tokyo"),
    "札幌": (43.0618, 141.3545, "Asia/Tokyo"),
    "福岡": (33.5904, 130.4017, "Asia/Tokyo"),
    "那覇": (26.2124, 127.6809, "Asia/Tokyo"),
    "仙台": (38.2688, 140.8721, "Asia/Tokyo"),
    "名古屋": (35.1815, 136.9066, "Asia/Tokyo"),
    "広島": (34.3853, 132.4553, "Asia/Tokyo"),
    "金沢": (36.5944, 136.6256, "Asia/Tokyo"),
    "鹿児島": (31.5966, 130.5571, "Asia/Tokyo"),
}

DEFAULT_CITIES = ["東京", "大阪", "札幌", "福岡", "那覇"]


def _parse_utc_to_jst(utc_str: str) -> str:
    """UTC時刻文字列(12:34:56 AM形式)をJST(HH:MM)に変換する"""
    try:
        dt = datetime.strptime(utc_str, "%I:%M:%S %p")
        today = datetime.now(timezone.utc)
        dt_utc = dt.replace(year=today.year, month=today.month, day=today.day, tzinfo=timezone.utc)
        dt_jst = dt_utc + timedelta(hours=9)
        return dt_jst.strftime("%H:%M")
    except Exception:
        return utc_str


def _seconds_to_hm(seconds) -> str:
    """秒数をH時間M分形式に変換"""
    try:
        sec = int(seconds)
        h = sec // 3600
        m = (sec % 3600) // 60
        return f"{h}時間{m:02d}分"
    except Exception:
        return str(seconds)


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    results = []

    for city in DEFAULT_CITIES:
        lat, lng, _ = CITY_COORDS[city]
        url = (
            f"https://api.sunrise-sunset.org/json"
            f"?lat={lat}&lng={lng}&date=today&formatted=0"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "OK":
                continue
            results_data = data["results"]
            # ISO8601 UTC文字列をJSTに変換
            def iso_to_jst(iso_str: str) -> str:
                try:
                    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
                    dt_jst = dt.astimezone(timezone(timedelta(hours=9)))
                    return dt_jst.strftime("%H:%M")
                except Exception:
                    return iso_str

            sunrise_jst = iso_to_jst(results_data.get("sunrise", ""))
            sunset_jst = iso_to_jst(results_data.get("sunset", ""))
            solar_noon_jst = iso_to_jst(results_data.get("solar_noon", ""))
            civil_twilight_begin_jst = iso_to_jst(results_data.get("civil_twilight_begin", ""))
            civil_twilight_end_jst = iso_to_jst(results_data.get("civil_twilight_end", ""))
            day_length_sec = results_data.get("day_length", 0)
            day_length_str = _seconds_to_hm(day_length_sec)

            results.append({
                "city": city,
                "lat": lat,
                "lng": lng,
                "sunrise": sunrise_jst,
                "sunset": sunset_jst,
                "solar_noon": solar_noon_jst,
                "civil_twilight_begin": civil_twilight_begin_jst,
                "civil_twilight_end": civil_twilight_end_jst,
                "day_length": day_length_str,
            })
        except Exception:
            continue

    if not results:
        raise RuntimeError("全都市の日の出日の入りデータ取得に失敗しました")

    city_names = [r["city"] for r in results]
    summary = (
        f"{today_str}の日本主要都市({', '.join(city_names)})の"
        f"日の出・日の入り時刻データを取得しました。"
        f"東京の日の出: {results[0]['sunrise']}、日の入り: {results[0]['sunset']}、"
        f"日照時間: {results[0]['day_length']}"
    )
    sources = ["https://api.sunrise-sunset.org/ (Sunrise Sunset API)"]
    raw = {
        "date": today_str,
        "cities": results,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文HTMLを返す"""
    date_str = html.escape(str(raw_data.get("date", "")))
    cities = raw_data.get("cities", [])

    rows = ""
    for entry in cities:
        city = html.escape(str(entry.get("city", "")))
        sunrise = html.escape(str(entry.get("sunrise", "-")))
        sunset = html.escape(str(entry.get("sunset", "-")))
        solar_noon = html.escape(str(entry.get("solar_noon", "-")))
        civil_begin = html.escape(str(entry.get("civil_twilight_begin", "-")))
        civil_end = html.escape(str(entry.get("civil_twilight_end", "-")))
        day_length = html.escape(str(entry.get("day_length", "-")))
        rows += (
            f"<tr>"
            f"<td><strong>{city}</strong></td>"
            f"<td>{civil_begin}</td>"
            f"<td>{sunrise}</td>"
            f"<td>{solar_noon}</td>"
            f"<td>{sunset}</td>"
            f"<td>{civil_end}</td>"
            f"<td>{day_length}</td>"
            f"</tr>"
        )

    source_links = ""
    for s in sources:
        safe_s = html.escape(str(s))
        # URLを抽出してリンク化
        if s.startswith("https://"):
            url_part = s.split(" ")[0]
            label_part = s[len(url_part):].strip().lstrip("()").strip("()")
            safe_url = html.escape(url_part)
            safe_label = html.escape(label_part)
            source_links += f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_label if safe_label else safe_url}</a> '
        else:
            source_links += safe_s + " "

    return (
        f"<h1>🌅 {html.escape(niche)}</h1>"
        f"<p>{date_str} の日本主要都市における日の出・日の入り・薄明の時刻一覧です（JST）。</p>"
        "<table>"
        "<thead>"
        "<tr>"
        "<th>都市</th>"
        "<th>薄明開始</th>"
        "<th>🌄 日の出</th>"
        "<th>正午(南中)</th>"
        "<th>🌇 日の入り</th>"
        "<th>薄明終了</th>"
        "<th>☀️ 日照時間</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "<p>※ 薄明(Civil Twilight)は、太陽が地平線下6度以内にある薄明るい時間帯です。</p>"
        f'<div class="source">データ出典: {source_links}</div>'
    )

