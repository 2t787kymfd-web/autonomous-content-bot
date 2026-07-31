"""kind_generator.py が自動生成したプラグイン: air_quality"""

import html
import requests
import datetime
from typing import Any

KIND_NAME = "air_quality"
KEYWORDS = ["大気汚染", "AQI", "空気質", "PM2.5", "PM10", "大気質", "air quality", "エアクオリティ", "大気汚染指数"]
CATEGORY = "天気・防災"

# 代表的な都市の座標
CITY_COORDS = [
    {"name": "東京", "lat": 35.6762, "lon": 139.6503},
    {"name": "大阪", "lat": 34.6937, "lon": 135.5023},
    {"name": "名古屋", "lat": 35.1815, "lon": 136.9066},
    {"name": "福岡", "lat": 33.5904, "lon": 130.4017},
    {"name": "札幌", "lat": 43.0618, "lon": 141.3545},
    {"name": "仙台", "lat": 38.2682, "lon": 140.8694},
    {"name": "広島", "lat": 34.3853, "lon": 132.4553},
    {"name": "那覇", "lat": 26.2124, "lon": 127.6809},
]

def _get_aqi_level(pm25: float) -> tuple:
    """PM2.5濃度からAQIレベルと色クラスを返す。"""
    if pm25 < 0:
        return "不明", "aqi-unknown"
    elif pm25 < 12:
        return "良好", "aqi-good"
    elif pm25 < 35.4:
        return "普通", "aqi-moderate"
    elif pm25 < 55.4:
        return "敏感な方に不健康", "aqi-sensitive"
    elif pm25 < 150.4:
        return "不健康", "aqi-unhealthy"
    elif pm25 < 250.4:
        return "非常に不健康", "aqi-very-unhealthy"
    else:
        return "危険", "aqi-hazardous"

def fetch(niche: str) -> tuple:
    """
    researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    Open-Meteo Air Quality APIから日本主要都市のAQIデータを取得する。
    """
    cities_data = []
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:00")

    for city in CITY_COORDS:
        try:
            params = {
                "latitude": city["lat"],
                "longitude": city["lon"],
                "hourly": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
                "timezone": "Asia/Tokyo",
                "forecast_days": 1,
            }
            resp = requests.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            pm25_list = hourly.get("pm2_5", [])
            pm10_list = hourly.get("pm10", [])
            co_list = hourly.get("carbon_monoxide", [])
            no2_list = hourly.get("nitrogen_dioxide", [])
            so2_list = hourly.get("sulphur_dioxide", [])
            o3_list = hourly.get("ozone", [])

            # 現在時刻に最も近いインデックスを取得
            idx = 0
            if times:
                now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
                now_jst_str = now_jst.strftime("%Y-%m-%dT%H:00")
                if now_jst_str in times:
                    idx = times.index(now_jst_str)
                else:
                    idx = min(len(times) - 1, now_jst.hour)

            def safe_val(lst, i):
                if lst and i < len(lst) and lst[i] is not None:
                    return round(float(lst[i]), 1)
                return -1.0

            pm25 = safe_val(pm25_list, idx)
            pm10 = safe_val(pm10_list, idx)
            co = safe_val(co_list, idx)
            no2 = safe_val(no2_list, idx)
            so2 = safe_val(so2_list, idx)
            o3 = safe_val(o3_list, idx)

            level, css_class = _get_aqi_level(pm25)

            cities_data.append({
                "name": city["name"],
                "pm25": pm25,
                "pm10": pm10,
                "co": co,
                "no2": no2,
                "so2": so2,
                "o3": o3,
                "level": level,
                "css_class": css_class,
                "time": times[idx] if times else "",
            })
        except Exception:
            cities_data.append({
                "name": city["name"],
                "pm25": -1.0,
                "pm10": -1.0,
                "co": -1.0,
                "no2": -1.0,
                "so2": -1.0,
                "o3": -1.0,
                "level": "取得失敗",
                "css_class": "aqi-unknown",
                "time": "",
            })

    # サマリー生成
    valid = [c for c in cities_data if c["pm25"] >= 0]
    if valid:
        worst = max(valid, key=lambda c: c["pm25"])
        best = min(valid, key=lambda c: c["pm25"])
        summary = (
            f"日本主要{len(cities_data)}都市の大気汚染指数(AQI)まとめ。"
            f"PM2.5が最も高いのは{worst['name']}({worst['pm25']} μg/m³・{worst['level']})、"
            f"最も低いのは{best['name']}({best['pm25']} μg/m³・{best['level']})です。"
        )
    else:
        summary = "日本主要都市の大気汚染指数(AQI)データを取得しました。"

    raw = {
        "cities": cities_data,
        "updated_at": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).strftime("%Y年%m月%d日 %H:%M JST"),
    }
    sources = [
        "https://open-meteo.com/ (Open-Meteo Air Quality API)",
        "https://air-quality-api.open-meteo.com/ (Open-Meteo Air Quality)",
    ]
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    """
    cities = raw_data.get("cities", [])
    updated_at = html.escape(str(raw_data.get("updated_at", "")))

    # AQIレベル凡例
    legend_html = (
        '<div class="aqi-legend">'
        '<strong>PM2.5 AQIレベル凡例:</strong>&nbsp;'
        '<span class="badge badge-good">良好 (&lt;12)</span>&nbsp;'
        '<span class="badge badge-moderate">普通 (12〜35.4)</span>&nbsp;'
        '<span class="badge badge-sensitive">敏感な方に不健康 (35.4〜55.4)</span>&nbsp;'
        '<span class="badge badge-unhealthy">不健康 (55.4〜150.4)</span>&nbsp;'
        '<span class="badge badge-very-unhealthy">非常に不健康 (150.4〜250.4)</span>&nbsp;'
        '<span class="badge badge-hazardous">危険 (&ge;250.4)</span>'
        '</div>'
    )

    # テーブルヘッダー
    table_html = (
        '<div class="table-responsive">'
        '<table>'
        '<thead><tr>'
        '<th>都市</th>'
        '<th>AQIレベル</th>'
        '<th>PM2.5<br><small>(μg/m³)</small></th>'
        '<th>PM10<br><small>(μg/m³)</small></th>'
        '<th>CO<br><small>(μg/m³)</small></th>'
        '<th>NO₂<br><small>(μg/m³)</small></th>'
        '<th>SO₂<br><small>(μg/m³)</small></th>'
        '<th>オゾン<br><small>(μg/m³)</small></th>'
        '</tr></thead>'
        '<tbody>'
    )

    def fmt(val: float) -> str:
        if val < 0:
            return '-'
        return str(val)

    for city in cities:
        name = html.escape(str(city.get("name", "")))
        level = html.escape(str(city.get("level", "")))
        css_class = html.escape(str(city.get("css_class", "aqi-unknown")))
        pm25 = fmt(city.get("pm25", -1))
        pm10 = fmt(city.get("pm10", -1))
        co = fmt(city.get("co", -1))
        no2 = fmt(city.get("no2", -1))
        so2 = fmt(city.get("so2", -1))
        o3 = fmt(city.get("o3", -1))

        # バッジのクラス名をAQIレベルから生成
        badge_map = {
            "aqi-good": "badge-good",
            "aqi-moderate": "badge-moderate",
            "aqi-sensitive": "badge-sensitive",
            "aqi-unhealthy": "badge-unhealthy",
            "aqi-very-unhealthy": "badge-very-unhealthy",
            "aqi-hazardous": "badge-hazardous",
            "aqi-unknown": "badge-unknown",
        }
        badge_class = html.escape(badge_map.get(city.get("css_class", "aqi-unknown"), "badge-unknown"))

        table_html += (
            f'<tr>'
            f'<td><strong>{name}</strong></td>'
            f'<td><span class="badge {badge_class}">{level}</span></td>'
            f'<td>{html.escape(pm25)}</td>'
            f'<td>{html.escape(pm10)}</td>'
            f'<td>{html.escape(co)}</td>'
            f'<td>{html.escape(no2)}</td>'
            f'<td>{html.escape(so2)}</td>'
            f'<td>{html.escape(o3)}</td>'
            f'</tr>'
        )

    table_html += '</tbody></table></div>'

    # 解説セクション
    explanation_html = (
        '<div class="info-box">'
        '<h2>📖 各指標の説明</h2>'
        '<ul>'
        '<li><strong>PM2.5</strong>: 粒径2.5μm以下の微小粒子状物質。肺の奥深くまで侵入し健康被害を引き起こす。</li>'
        '<li><strong>PM10</strong>: 粒径10μm以下の粒子状物質。鼻や口から吸入される。</li>'
        '<li><strong>CO (一酸化炭素)</strong>: 不完全燃焼により発生する無色・無臭の有毒ガス。</li>'
        '<li><strong>NO₂ (二酸化窒素)</strong>: 自動車や工場から排出される大気汚染物質。呼吸器に影響。</li>'
        '<li><strong>SO₂ (二酸化硫黄)</strong>: 化石燃料の燃焼や火山活動で発生。酸性雨の原因。</li>'
        '<li><strong>オゾン (O₃)</strong>: 地表付近のオゾンは光化学スモッグの原因となる。</li>'
        '</ul>'
        '<p>⚠️ AQIが「敏感な方に不健康」以上の場合は、外出時にマスクの着用をおすすめします。</p>'
        '</div>'
    )

    # 出典
    source_items = ""
    for s in sources:
        safe_s = html.escape(str(s))
        # URLを抽出してリンク化
        if s.startswith("https://"):
            url_part = s.split(" ")[0]
            label_part = s[len(url_part):].strip()
            if label_part.startswith("(") and label_part.endswith(")"):
                label_part = label_part[1:-1]
            safe_url = html.escape(url_part)
            safe_label_part = html.escape(label_part) if label_part else safe_url
            source_items += f'<li><a href="{safe_url}" target="_blank" rel="noopener">{safe_label_part}</a></li>'
        else:
            source_items += f'<li>{safe_s}</li>'

    source_html = (
        '<div class="source">'
        f'<p>最終更新: {updated_at}</p>'
        '<p>データ出典:</p>'
        f'<ul>{source_items}</ul>'
        '<p>※ Open-Meteo Air Quality APIはCC BY 4.0ライセンスで提供されています。</p>'
        '</div>'
    )

    safe_niche = html.escape(str(niche))

    return (
        f'<h1>🌫️ {safe_niche}</h1>'
        '<p>Open-Meteo Air Quality APIを使用して、日本の主要都市のリアルタイム大気汚染指数(AQI)をまとめています。'
        'PM2.5・PM10・CO・NO₂・SO₂・オゾンの各指標を確認できます。</p>'
        + legend_html
        + table_html
        + explanation_html
        + source_html
    )

