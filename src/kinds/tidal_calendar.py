"""kind_generator.py が自動生成したプラグイン: tidal_calendar"""

import requests
import json
import html
import math
import re
from datetime import datetime, timezone, timedelta

KIND_NAME = "tidal_calendar"
KEYWORDS = ["潮汐", "潮位", "干潮", "満潮", "タイド", "tidal", "tide", "潮見表", "潮汐カレンダー"]
CATEGORY = "天気・防災"

# 日本主要地点の座標マッピング
JAPAN_TIDE_STATIONS = {
    "東京": {"lat": 35.65, "lon": 139.77, "label": "東京湾"},
    "横浜": {"lat": 35.44, "lon": 139.64, "label": "横浜港"},
    "大阪": {"lat": 34.65, "lon": 135.43, "label": "大阪湾"},
    "神戸": {"lat": 34.69, "lon": 135.19, "label": "神戸港"},
    "名古屋": {"lat": 35.05, "lon": 136.88, "label": "名古屋港"},
    "福岡": {"lat": 33.61, "lon": 130.40, "label": "博多湾"},
    "広島": {"lat": 34.39, "lon": 132.46, "label": "広島湾"},
    "仙台": {"lat": 38.27, "lon": 141.02, "label": "仙台湾"},
    "札幌": {"lat": 43.06, "lon": 141.35, "label": "石狩湾"},
    "那覇": {"lat": 26.21, "lon": 127.68, "label": "那覇港"},
    "鹿児島": {"lat": 31.60, "lon": 130.56, "label": "鹿児島湾"},
    "新潟": {"lat": 37.92, "lon": 139.05, "label": "新潟港"},
    "金沢": {"lat": 36.58, "lon": 136.63, "label": "金沢港"},
    "高松": {"lat": 34.34, "lon": 134.05, "label": "高松港"},
    "松山": {"lat": 33.84, "lon": 132.77, "label": "松山港"},
}


def _get_julian_day(year: int, month: int, day: int) -> float:
    """グレゴリオ暦からユリウス日を計算する"""
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5


def _calc_moon_phase(year: int, month: int, day: int) -> tuple:
    """
    月の位相を計算する。
    戻り値: (phase_ratio: 0.0-1.0, moon_age_days: float, moon_name: str)
    0.0 = 新月, 0.5 = 満月
    """
    jd = _get_julian_day(year, month, day)
    # 既知の新月(2000-01-06.4)からの経過日数
    known_new_moon_jd = 2451549.5
    synodic_month = 29.53058867  # 朔望月の日数
    days_since = jd - known_new_moon_jd
    cycles = days_since / synodic_month
    phase_ratio = cycles - math.floor(cycles)  # 0.0〜1.0
    moon_age = phase_ratio * synodic_month

    if phase_ratio < 0.03 or phase_ratio >= 0.97:
        moon_name = "🌑 新月"
    elif phase_ratio < 0.22:
        moon_name = "🌒 三日月"
    elif phase_ratio < 0.28:
        moon_name = "🌓 上弦の月"
    elif phase_ratio < 0.47:
        moon_name = "🌔 十三夜月"
    elif phase_ratio < 0.53:
        moon_name = "🌕 満月"
    elif phase_ratio < 0.72:
        moon_name = "🌖 十六夜月"
    elif phase_ratio < 0.78:
        moon_name = "🌗 下弦の月"
    else:
        moon_name = "🌘 有明月"

    return phase_ratio, moon_age, moon_name


def _estimate_tide_times(phase_ratio: float, base_date_str: str) -> list:
    """
    月の位相から1日の満潮・干潮の目安時刻を推算する。
    ※天文学的近似値。実際の潮汐は地形・海底地形等に大きく依存する。
    大潮: 新月/満月付近 (phase 0, 0.5)
    小潮: 上弦/下弦付近 (phase 0.25, 0.75)
    標準的な半日周潮の場合、月が南中する時刻に満潮になるとする簡易近似。
    月の南中時刻 ≈ 12:00 + (月齢 × 0.8) 時間
    """
    moon_age_days = phase_ratio * 29.53
    # 月の南中時刻の近似 (時間単位)
    # 新月時は太陽と同方向→正午頃南中→正午頃満潮
    # 満月時は太陽の反対→深夜0時頃南中→深夜満潮
    meridian_hour = (12.0 + moon_age_days * (24.0 / 29.53)) % 24.0
    # 半日周潮: 満潮は約12時間25分間隔
    half_period = 12.0 + 25.0 / 60.0

    tides = []
    # 1日分の満潮・干潮(2回ずつ)
    for i in range(2):
        high_hour = (meridian_hour + i * half_period) % 24.0
        low_hour = (high_hour + half_period / 2) % 24.0
        h_hh = int(high_hour)
        h_mm = int((high_hour - h_hh) * 60)
        l_hh = int(low_hour)
        l_mm = int((low_hour - l_hh) * 60)
        tides.append({"type": "満潮", "time": f"{h_hh:02d}:{h_mm:02d}", "icon": "🔼"})
        tides.append({"type": "干潮", "time": f"{l_hh:02d}:{l_mm:02d}", "icon": "🔽"})

    # 時刻順にソート
    def time_to_min(t):
        parts = t["time"].split(":")
        return int(parts[0]) * 60 + int(parts[1])
    tides.sort(key=time_to_min)
    return tides


def _get_tide_strength(phase_ratio: float) -> tuple:
    """
    月の位相から潮の大小を判定する。
    戻り値: (strength_label: str, strength_level: int(1-5), color_class: str)
    """
    # 新月・満月付近が大潮
    dist_new = min(phase_ratio, 1.0 - phase_ratio)
    dist_full = abs(phase_ratio - 0.5)
    dist_min = min(dist_new, dist_full)

    if dist_min < 0.04:
        return "大潮", 5, "tide-ooshio"
    elif dist_min < 0.08:
        return "中潮", 4, "tide-nakaoshio"
    elif dist_min < 0.15:
        return "中潮", 3, "tide-nakaoshio"
    elif dist_min < 0.21:
        return "小潮", 2, "tide-koshio"
    else:
        return "長潮・若潮", 1, "tide-nagashio"


def _find_station(niche: str) -> dict:
    """ニッチ文字列から観測点を特定する"""
    for key, val in JAPAN_TIDE_STATIONS.items():
        if key in niche:
            return {"name": key, **val}
    # デフォルトは東京
    default_key = "東京"
    return {"name": default_key, **JAPAN_TIDE_STATIONS[default_key]}


def _fetch_marine_data(lat: float, lon: float) -> dict:
    """Open-Meteo Marine APIから波浪データを取得する"""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "wave_height_max,wave_period_max,wind_wave_height_max",
        "timezone": "Asia/Tokyo",
        "forecast_days": 7,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch(niche: str) -> tuple:
    """
    researcher.pyの契約:
    (summary: str, sources: list, raw_data: dict) を返す。
    """
    station = _find_station(niche)
    lat = station["lat"]
    lon = station["lon"]
    station_label = station["label"]

    # 現在の日本時間
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    today = now_jst.date()

    # 月の位相計算(7日分)
    moon_phases = []
    for i in range(7):
        d = today + timedelta(days=i)
        phase_ratio, moon_age, moon_name = _calc_moon_phase(d.year, d.month, d.day)
        strength_label, strength_level, strength_class = _get_tide_strength(phase_ratio)
        tides = _estimate_tide_times(phase_ratio, d.isoformat())
        moon_phases.append({
            "date": d.isoformat(),
            "date_label": f"{d.month}/{d.day}({['月','火','水','木','金','土','日'][d.weekday()]})",
            "moon_name": moon_name,
            "moon_age": round(moon_age, 1),
            "phase_ratio": round(phase_ratio, 3),
            "strength_label": strength_label,
            "strength_level": strength_level,
            "strength_class": strength_class,
            "tides": tides,
        })

    # Open-Meteo Marine APIから波浪データを取得
    marine_data = {}
    marine_error = None
    try:
        marine_raw = _fetch_marine_data(lat, lon)
        daily = marine_raw.get("daily", {})
        dates = daily.get("time", [])
        wave_heights = daily.get("wave_height_max", [])
        wave_periods = daily.get("wave_period_max", [])
        if dates:
            for i, d in enumerate(dates):
                marine_data[d] = {
                    "wave_height": wave_heights[i] if i < len(wave_heights) else None,
                    "wave_period": wave_periods[i] if i < len(wave_periods) else None,
                }
    except Exception as e:
        marine_error = str(e)

    # 月相データは必ず取れているのでOK(計算ベース)
    if not moon_phases:
        raise RuntimeError("月相データの計算に失敗しました")

    today_phase = moon_phases[0]
    summary = (
        f"{station_label}の潮汐カレンダー（{today.month}月{today.day}日〜7日間）: "
        f"本日は{today_phase['moon_name']}（月齢{today_phase['moon_age']}日）、"
        f"{today_phase['strength_label']}。"
        f"満潮・干潮の目安時刻を含む7日間の潮汐情報を掲載。"
    )

    raw = {
        "station": station,
        "generated_at": now_jst.strftime("%Y-%m-%d %H:%M"),
        "generated_date": today.isoformat(),
        "moon_phases": moon_phases,
        "marine_data": marine_data,
        "marine_error": marine_error,
    }

    sources = [
        "https://marine-api.open-meteo.com/ (Open-Meteo Marine API - 波浪データ)",
        "https://www.kaiho.mlit.go.jp/KANKYO/TIDE/ (海上保安庁 潮汐推算 参考)",
    ]
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.pyの契約:
    ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    """
    station = raw_data.get("station", {})
    station_label = html.escape(str(station.get("label", "観測点")))
    station_name = html.escape(str(station.get("name", "")))
    generated_at = html.escape(str(raw_data.get("generated_at", "")))
    moon_phases = raw_data.get("moon_phases", [])
    marine_data = raw_data.get("marine_data", {})
    marine_error = raw_data.get("marine_error")

    # 今日のデータ
    today_phase = moon_phases[0] if moon_phases else {}
    today_moon = html.escape(str(today_phase.get("moon_name", "-")))
    today_moon_age = html.escape(str(today_phase.get("moon_age", "-")))
    today_strength = html.escape(str(today_phase.get("strength_label", "-")))
    today_date = html.escape(str(today_phase.get("date", "")))

    # 今日の潮汐
    today_tides = today_phase.get("tides", [])
    today_tide_html = ""
    for t in today_tides:
        t_type = html.escape(str(t.get("type", "")))
        t_time = html.escape(str(t.get("time", "")))
        t_icon = html.escape(str(t.get("icon", "")))
        css_cls = "tide-high" if t.get("type") == "満潮" else "tide-low"
        today_tide_html += f'<span class="tide-badge {css_cls}">{t_icon} {t_type} {t_time}</span> '

    # サマリーカード
    summary_card = (
        f'<div class="tide-summary-card">'
        f'<div class="tide-summary-left">'
        f'<div class="tide-moon-icon">{today_moon}</div>'
        f'<div class="tide-moon-age">月齢 {today_moon_age} 日</div>'
        f'</div>'
        f'<div class="tide-summary-right">'
        f'<div class="tide-strength-badge">{today_strength}</div>'
        f'<div class="tide-today-tides">{today_tide_html}</div>'
        f'</div>'
        f'</div>'
    )

    # 7日間カレンダーテーブル
    calendar_rows = ""
    for phase in moon_phases:
        date_label = html.escape(str(phase.get("date_label", "")))
        moon_name = html.escape(str(phase.get("moon_name", "-")))
        moon_age = html.escape(str(phase.get("moon_age", "-")))
        strength_label = html.escape(str(phase.get("strength_label", "-")))
        strength_level = phase.get("strength_level", 1)
        strength_class = html.escape(str(phase.get("strength_class", "")))
        tides = phase.get("tides", [])
        phase_date = phase.get("date", "")

        # 波浪データ
        wave_info = "-"
        if phase_date in marine_data:
            md = marine_data[phase_date]
            wh = md.get("wave_height")
            if wh is not None:
                wave_info = html.escape(f"{wh:.1f} m")

        # 満潮・干潮時刻セル
        tide_cells = ""
        high_tides = [t for t in tides if t.get("type") == "満潮"]
        low_tides = [t for t in tides if t.get("type") == "干潮"]
        high_str = " / ".join(html.escape(t["time"]) for t in high_tides)
        low_str = " / ".join(html.escape(t["time"]) for t in low_tides)

        # 強さインジケーター
        bars = ""
        for b in range(5):
            bar_cls = "bar-active" if b < strength_level else "bar-inactive"
            bars += f'<span class="tide-bar {bar_cls}"></span>'
        strength_indicator = f'<div class="tide-bars">{bars}</div>'

        # 今日かどうか
        is_today = (phase.get("date") == raw_data.get("generated_date", ""))
        row_cls = "tide-row-today" if is_today else ""

        calendar_rows += (
            f'<tr class="{row_cls}">'
            f'<td class="tide-date">{date_label}</td>'
            f'<td class="tide-moon">{moon_name}</td>'
            f'<td class="tide-age">{moon_age}日</td>'
            f'<td class="tide-strength-cell"><span class="{strength_class}">{strength_label}</span>{strength_indicator}</td>'
            f'<td class="tide-high-time">🔼 {high_str}</td>'
            f'<td class="tide-low-time">🔽 {low_str}</td>'
            f'<td class="tide-wave">{wave_info}</td>'
            f'</tr>'
        )

    calendar_table = (
        f'<div class="tide-table-wrapper">'
        f'<table class="tide-table">'
        f'<thead><tr>'
        f'<th>日付</th><th>月相</th><th>月齢</th><th>潮の大小</th>'
        f'<th>満潮(目安)</th><th>干潮(目安)</th><th>波高(最大)</th>'
        f'</tr></thead>'
        f'<tbody>{calendar_rows}</tbody>'
        f'</table>'
        f'</div>'
    )

    # 波浪セクション
    marine_section = ""
    if marine_data:
        marine_section = (
            '<div class="tide-marine-note">'
            '<strong>🌊 波浪データについて:</strong> '
            f'Open-Meteo Marine APIによる{station_label}周辺の予測値です。'
            '</div>'
        )
    elif marine_error:
        marine_section = (
            '<div class="tide-marine-note tide-marine-error">'
            '波浪データの取得に失敗しました（潮汐データは正常に表示されています）。'
            '</div>'
        )

    # 出典
    sources_html = ""
    for s in sources:
        safe_s = html.escape(str(s))
        # URLを抽出してリンク化
        m = re.match(r'(https://[^\s]+)', s)
        if m:
            url = m.group(1)
            if url.startswith("https://"):
                sources_html += f'<li><a href="{html.escape(url)}" target="_blank" rel="noopener">{safe_s}</a></li>'
            else:
                sources_html += f'<li>{safe_s}</li>'
        else:
            sources_html += f'<li>{safe_s}</li>'

    return (
        f'<h1>🌊 {html.escape(niche)} — {station_label}</h1>'
        f'<p class="tide-subtitle">月相と天文潮汐に基づく7日間の潮見表（{station_name}周辺）</p>'
        f'<p class="tide-generated">更新: {generated_at} JST</p>'
        f'{summary_card}'
        f'<h2>📅 7日間の潮汐カレンダー</h2>'
        f'{calendar_table}'
        f'{marine_section}'
        '<div class="tide-disclaimer">'
        '<strong>⚠️ 免責事項:</strong> '
        'このページの満潮・干潮時刻は<strong>月の位相に基づく天文学的推算値</strong>です。'
        '実際の潮汐は地形・海底地形・気象等の影響を大きく受けるため、'
        '漁業・海水浴・潮干狩り等の実際の行動判断には'
        '<a href="https://www.kaiho.mlit.go.jp/KANKYO/TIDE/" target="_blank" rel="noopener">'
        '海上保安庁 潮汐推算</a>や'
        '<a href="https://www.data.jma.go.jp/kaiyou/db/tide/suisan/" target="_blank" rel="noopener">'
        '気象庁 潮位表</a>の正式データを必ずご参照ください。'
        '</div>'
        f'<div class="source">データ出典: <ul>{sources_html}</ul></div>'
    )

