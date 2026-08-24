"""kind_generator.py が自動生成したプラグイン: electric_power_demand"""

import requests
import json
import html
import math
from datetime import datetime, timezone, timedelta

KIND_NAME = "electric_power_demand"
KEYWORDS = ["電力", "電力需給", "節電", "でんき予報", "電力消費", "electric power", "power demand", "energy"]
CATEGORY = "生活計算"

# 主要都市の座標(日本の電力需給を代表するエリア)
CITY_COORDS = {
    "東京": (35.6895, 139.6917, "東京電力"),
    "大阪": (34.6937, 135.5022, "関西電力"),
    "名古屋": (35.1815, 136.9066, "中部電力"),
    "札幌": (43.0642, 141.3469, "北海道電力"),
    "福岡": (33.5904, 130.4017, "九州電力"),
}


def _estimate_demand_ratio(temp_c: float, hour: int, month: int) -> float:
    """
    気温・時刻・月から電力需要率(%,対ピーク比)を推定する。
    夏(7-9月)・冬(12-2月)にピーク、朝夕に増加するモデル。
    """
    # 時刻係数(朝8-10時、夜18-21時にピーク)
    if 0 <= hour < 5:
        time_factor = 0.55
    elif 5 <= hour < 8:
        time_factor = 0.65 + (hour - 5) * 0.05
    elif 8 <= hour < 11:
        time_factor = 0.80 + (hour - 8) * 0.05
    elif 11 <= hour < 14:
        time_factor = 0.88
    elif 14 <= hour < 18:
        time_factor = 0.85
    elif 18 <= hour < 21:
        time_factor = 0.90
    elif 21 <= hour < 24:
        time_factor = 0.75 - (hour - 21) * 0.05
    else:
        time_factor = 0.70

    # 気温係数(冷暖房負荷)
    if temp_c >= 30:
        temp_factor = 0.95 + min((temp_c - 30) * 0.02, 0.10)
    elif temp_c >= 25:
        temp_factor = 0.80 + (temp_c - 25) * 0.03
    elif temp_c >= 15:
        temp_factor = 0.72
    elif temp_c >= 5:
        temp_factor = 0.80 + (15 - temp_c) * 0.015
    else:
        temp_factor = 0.90 + min((5 - temp_c) * 0.02, 0.10)

    # 季節係数
    if month in [7, 8, 9]:
        season_factor = 1.05
    elif month in [12, 1, 2]:
        season_factor = 1.03
    elif month in [4, 5, 10, 11]:
        season_factor = 0.90
    else:
        season_factor = 0.95

    raw = time_factor * temp_factor * season_factor * 100
    return min(max(round(raw, 1), 30.0), 105.0)


def _demand_level(ratio: float) -> tuple:
    """需要率から警戒レベルと絵文字を返す"""
    if ratio >= 95:
        return "需給逼迫", "🔴"
    elif ratio >= 85:
        return "やや逼迫", "🟠"
    elif ratio >= 75:
        return "注意", "🟡"
    else:
        return "安定", "🟢"


def _estimate_carbon_intensity(temp_c: float, ratio: float) -> int:
    """
    需要率と気温からCO2排出強度(gCO2/kWh)を大まかに推定する。
    日本の平均は約400-500g/kWh程度。需要が高いほど火力依存増加。
    """
    base = 430
    demand_add = (ratio - 70) * 2.5 if ratio > 70 else 0
    return int(min(max(base + demand_add, 350), 600))


def fetch(niche: str) -> tuple:
    """
    Open-Meteo APIで主要都市の気象データを取得し、
    電力需要率・CO2排出強度を推定して返す。
    """
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    hour_jst = now_jst.hour
    month_jst = now_jst.month

    results = []
    errors = []

    for city, (lat, lon, company) in CITY_COORDS.items():
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m"
                f"&timezone=Asia%2FTokyo"
                f"&forecast_days=1"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})
            temp = current.get("temperature_2m")
            apparent = current.get("apparent_temperature")
            wind = current.get("wind_speed_10m")
            precip = current.get("precipitation")

            if temp is None:
                errors.append(f"{city}: 気温データなし")
                continue

            demand_ratio = _estimate_demand_ratio(float(temp), hour_jst, month_jst)
            level_name, level_emoji = _demand_level(demand_ratio)
            carbon = _estimate_carbon_intensity(float(temp), demand_ratio)

            results.append({
                "city": city,
                "company": company,
                "temp_c": temp,
                "apparent_c": apparent,
                "wind_kmh": wind,
                "precipitation": precip,
                "demand_ratio": demand_ratio,
                "level_name": level_name,
                "level_emoji": level_emoji,
                "carbon_intensity": carbon,
            })
        except Exception as e:
            errors.append(f"{city}: {e}")

    if not results:
        raise RuntimeError(f"全都市のデータ取得に失敗しました: {'; '.join(errors)}")

    timestamp = now_jst.strftime("%Y-%m-%d %H:%M JST")
    cities_str = "、".join(r["city"] for r in results)
    first = results[0]
    summary = (
        f"{timestamp} 時点の電力需給推計。"
        f"対象都市: {cities_str}。"
        f"東京エリア推定需要率: {first['demand_ratio']}%、"
        f"需給レベル: {first['level_name']}、"
        f"推定CO2強度: {first['carbon_intensity']} gCO2/kWh。"
    )
    sources = [
        "https://api.open-meteo.com/ (Open-Meteo 気象API)",
        "https://open-meteo.com/ (Open-Meteo 公式サイト)",
    ]
    raw = {
        "timestamp": timestamp,
        "hour_jst": hour_jst,
        "month": month_jst,
        "results": results,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    timestamp = html.escape(str(raw_data.get("timestamp", "-")))
    results = raw_data.get("results", [])
    hour = raw_data.get("hour_jst", 12)

    # テーブル行生成
    rows = []
    for r in results:
        city = html.escape(str(r.get("city", "-")))
        company = html.escape(str(r.get("company", "-")))
        temp = html.escape(str(r.get("temp_c", "-")))
        apparent = html.escape(str(r.get("apparent_c", "-")))
        demand = html.escape(str(r.get("demand_ratio", "-")))
        level_name = html.escape(str(r.get("level_name", "-")))
        level_emoji = html.escape(str(r.get("level_emoji", "")))
        carbon = html.escape(str(r.get("carbon_intensity", "-")))
        wind = html.escape(str(r.get("wind_kmh", "-")))

        # 需要率に応じた背景色クラス
        ratio_val = r.get("demand_ratio", 0)
        if ratio_val >= 95:
            row_class = ' class="demand-critical"'
        elif ratio_val >= 85:
            row_class = ' class="demand-high"'
        elif ratio_val >= 75:
            row_class = ' class="demand-mid"'
        else:
            row_class = ''

        rows.append(
            f'<tr{row_class}>'
            f'<td>{city}</td>'
            f'<td>{company}</td>'
            f'<td class="tel-value">{temp} ℃</td>'
            f'<td class="tel-value">{apparent} ℃</td>'
            f'<td class="tel-value">{wind} km/h</td>'
            f'<td class="tel-value">{demand} %</td>'
            f'<td>{level_emoji} {level_name}</td>'
            f'<td class="tel-value">{carbon} g/kWh</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows)

    # 時刻帯に応じたアドバイスメッセージ
    if 8 <= hour < 11 or 18 <= hour < 21:
        advice = "⚡ 現在は需要ピーク時間帯です。大型家電の使用を少しずらすと節電効果があります。"
    elif 0 <= hour < 5:
        advice = "🌙 深夜帯は電力需要が低く料金も安い時間帯です。洗濯・食洗機などの活用がおすすめです。"
    elif 11 <= hour < 14:
        advice = "☀️ 昼間は太陽光発電が稼働しています。晴れた日の昼間は比較的安定しています。"
    else:
        advice = "💡 エアコンのフィルター掃除・設定温度の見直しで消費電力を削減できます。"

    # 凡例
    legend = (
        '<div class="legend">'
        '<span class="legend-item">🟢 安定 (75%未満)</span>'
        '<span class="legend-item">🟡 注意 (75〜84%)</span>'
        '<span class="legend-item">🟠 やや逼迫 (85〜94%)</span>'
        '<span class="legend-item">🔴 需給逼迫 (95%以上)</span>'
        '</div>'
    )

    sources_html = "".join(
        f'<a href="{html.escape(s.split(" ")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a><br>'
        for s in sources
        if s.split(" ")[0].startswith("https://")
    )

    return (
        f'<h1>⚡ {html.escape(niche)}</h1>'
        f'<p>Open-Meteo の気象データ(気温・気象状況)をもとに、主要都市エリアの'
        f'<strong>推定電力需要率</strong>と<strong>推定CO₂排出強度</strong>をリアルタイムで計算します。'
        f'数値は気温・時刻・季節から算出した推計値です。</p>'
        f'<p class="update-time">🕐 データ取得時刻: <span class="tel-value">{timestamp}</span></p>'
        f'<div class="advice-box">{advice}</div>'
        f'<table>'
        f'<thead><tr>'
        f'<th>エリア</th><th>電力会社</th><th>気温</th><th>体感気温</th>'
        f'<th>風速</th><th>推定需要率</th><th>需給レベル</th><th>推定CO₂強度</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
        f'{legend}'
        f'<h2>📖 電力需給の読み方</h2>'
        f'<ul>'
        f'<li><strong>推定需要率</strong>: ピーク電力に対する現在の推定使用割合。90%超で節電の協力要請が出ることがあります。</li>'
        f'<li><strong>推定CO₂強度</strong>: 電力1kWhあたりの推定CO₂排出量。需要が高いほど火力発電への依存が増え数値が上がります。</li>'
        f'<li>※ 本ページの数値は気温・時刻・季節から算出した<strong>推計値</strong>であり、各電力会社の実測値とは異なります。</li>'
        f'</ul>'
        f'<div class="source">データ出典: {sources_html}</div>'
    )

