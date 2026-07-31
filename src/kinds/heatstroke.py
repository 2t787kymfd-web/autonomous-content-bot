"""kind_generator.py が自動生成したプラグイン: heatstroke"""

import requests
import html
from datetime import datetime

KIND_NAME = "heatstroke"
KEYWORDS = ["熱中症", "警戒指数", "WBGT", "暑さ指数", "熱中症アラート", "heatstroke", "heat index"]
CATEGORY = "天気・防災"

# 主要都市の座標
CITIES = [
    {"name": "札幌", "lat": 43.06, "lon": 141.35},
    {"name": "仙台", "lat": 38.27, "lon": 140.87},
    {"name": "東京", "lat": 35.69, "lon": 139.69},
    {"name": "横浜", "lat": 35.44, "lon": 139.64},
    {"name": "名古屋", "lat": 35.18, "lon": 136.91},
    {"name": "大阪", "lat": 34.69, "lon": 135.50},
    {"name": "京都", "lat": 35.01, "lon": 135.76},
    {"name": "神戸", "lat": 34.69, "lon": 135.19},
    {"name": "広島", "lat": 34.40, "lon": 132.46},
    {"name": "福岡", "lat": 33.59, "lon": 130.40},
    {"name": "那覇", "lat": 26.21, "lon": 127.68},
    {"name": "金沢", "lat": 36.56, "lon": 136.66},
]

def _calc_wbgt(temp_c: float, humidity_pct: float, solar_rad: float, wind_ms: float) -> float:
    """
    WBGT(湿球黒球温度)の簡易推定式。
    ISO 7243 / 環境省の屋外式に基づく近似:
      WBGT ≈ 0.7*Tw + 0.2*Tg + 0.1*Ta
    Tw(湿球温度): スターゲント近似
    Tg(黒球温度): 日射と風速から近似
    Ta(乾球温度): 気温そのまま
    """
    ta = temp_c
    rh = humidity_pct

    # 湿球温度 Tw の近似 (Stull 2011)
    tw = ta * (0.151977 * (rh + 8.313659) ** 0.5) \
         + (0.00391838 * rh ** (3/2)) * (0.023101 * ta - 4.686035) \
         - 0.581 \
         + 0.00391838 * (rh ** 1.5) \
         - (ta + 0.023101 * ta - 4.686035)
    # より安定した近似に置き換え
    # Tw ≈ Ta - ((100 - RH) / 5) という線形近似も利用
    tw = ta - ((100.0 - rh) / 5.0)

    # 黒球温度 Tg の近似
    # Tg ≈ Ta + 2.5 * (solar_rad / 1000)^0.5 - 0.5 * wind_ms  (W/m²)
    solar_kw = max(solar_rad, 0.0) / 1000.0
    wind_safe = max(wind_ms, 0.1)
    tg = ta + 2.5 * (solar_kw ** 0.5) - 0.5 * wind_safe

    wbgt = 0.7 * tw + 0.2 * tg + 0.1 * ta
    return round(wbgt, 1)


def _wbgt_level(wbgt: float) -> tuple:
    """環境省の暑さ指数区分に基づくレベル判定。"""
    if wbgt >= 31:
        return ("危険", "#d9001b", "運動は原則中止")
    elif wbgt >= 28:
        return ("厳重警戒", "#ff6600", "激しい運動は中止")
    elif wbgt >= 25:
        return ("警戒", "#ffd700", "積極的に休憩")
    elif wbgt >= 21:
        return ("注意", "#90ee90", "積極的に水分補給")
    else:
        return ("ほぼ安全", "#87ceeb", "適宜水分補給")


def fetch(niche: str) -> tuple:
    """
    researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    Open-Meteo APIから気温・湿度・日射量・風速を取得しWBGT相当値を計算する。
    """
    results = []
    now_jst = datetime.utcnow()  # UTC基準で処理

    for city in CITIES:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={city['lat']}&longitude={city['lon']}"
            "&current=temperature_2m,relative_humidity_2m,"
            "shortwave_radiation,wind_speed_10m"
            "&timezone=Asia%2FTokyo"
            "&forecast_days=1"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current", {})
            temp = current.get("temperature_2m")
            hum = current.get("relative_humidity_2m")
            solar = current.get("shortwave_radiation", 0.0)
            wind = current.get("wind_speed_10m", 1.0)
            if temp is None or hum is None:
                continue
            wbgt = _calc_wbgt(float(temp), float(hum), float(solar), float(wind))
            level, color, advice = _wbgt_level(wbgt)
            results.append({
                "city": city["name"],
                "temp": temp,
                "humidity": hum,
                "solar": solar,
                "wind": wind,
                "wbgt": wbgt,
                "level": level,
                "color": color,
                "advice": advice,
            })
        except Exception:
            continue

    if not results:
        raise RuntimeError("Open-Meteoからデータを取得できませんでした")

    # サマリー作成
    danger_cities = [r["city"] for r in results if r["level"] == "危険"]
    caution_cities = [r["city"] for r in results if r["level"] == "厳重警戒"]
    max_wbgt = max(r["wbgt"] for r in results)
    max_city = next(r["city"] for r in results if r["wbgt"] == max_wbgt)

    summary_parts = [f"本日の主要都市のWBGT(暑さ指数)まとめ。最高は{max_city}の{max_wbgt}℃。"]
    if danger_cities:
        summary_parts.append(f"危険レベル: {', '.join(danger_cities)}。")
    if caution_cities:
        summary_parts.append(f"厳重警戒: {', '.join(caution_cities)}。")
    summary = " ".join(summary_parts)

    sources = [
        "https://open-meteo.com/ (Open-Meteo 気象API)",
        "https://www.wbgt.env.go.jp/ (環境省 熱中症予防情報サイト 参考)",
    ]
    raw = {
        "results": results,
        "fetched_at": now_jst.strftime("%Y-%m-%d %H:%M UTC"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    """
    results = raw_data.get("results", [])
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    safe_niche = html.escape(niche)

    # 統計
    if results:
        max_wbgt = max(r["wbgt"] for r in results)
        max_city = next(r["city"] for r in results if r["wbgt"] == max_wbgt)
        danger_count = sum(1 for r in results if r["level"] == "危険")
        caution_count = sum(1 for r in results if r["level"] == "厳重警戒")
    else:
        max_wbgt = "-"
        max_city = "-"
        danger_count = 0
        caution_count = 0

    # サマリーカード
    summary_cards = ""
    card_data = [
        ("🌡️ 最高暑さ指数", f"{max_wbgt}℃ ({html.escape(str(max_city))})" if results else "-"),
        ("🚨 危険都市数", f"{danger_count} 都市"),
        ("⚠️ 厳重警戒都市数", f"{caution_count} 都市"),
        ("🕐 取得時刻", fetched_at),
    ]
    for label, value in card_data:
        summary_cards += (
            f'<div class="card">'
            f'<div class="card-label">{html.escape(label)}</div>'
            f'<div class="card-value tel-value">{value}</div>'
            f'</div>'
        )

    # WBGT説明
    legend_rows = [
        ("≥31℃", "危険", "#d9001b", "運動は原則中止"),
        ("28〜31℃", "厳重警戒", "#ff6600", "激しい運動は中止"),
        ("25〜28℃", "警戒", "#ffd700", "積極的に休憩"),
        ("21〜25℃", "注意", "#90ee90", "積極的に水分補給"),
        ("<21℃", "ほぼ安全", "#87ceeb", "適宜水分補給"),
    ]
    legend_html = ""
    for rng, lvl, col, adv in legend_rows:
        legend_html += (
            f'<tr>'
            f'<td style="background:{html.escape(col)};color:#333;font-weight:bold;padding:4px 10px;">'
            f'{html.escape(lvl)}</td>'
            f'<td class="tel-value">{html.escape(rng)}</td>'
            f'<td>{html.escape(adv)}</td>'
            f'</tr>'
        )

    # 都市テーブル
    city_rows = ""
    sorted_results = sorted(results, key=lambda r: r["wbgt"], reverse=True)
    for r in sorted_results:
        city = html.escape(str(r["city"]))
        temp = html.escape(str(r["temp"]))
        hum = html.escape(str(r["humidity"]))
        wbgt = html.escape(str(r["wbgt"]))
        level = html.escape(str(r["level"]))
        color = html.escape(str(r["color"])) if str(r["color"]).startswith("#") else "#cccccc"
        advice = html.escape(str(r["advice"]))
        city_rows += (
            f'<tr>'
            f'<td>{city}</td>'
            f'<td class="tel-value">{temp}℃</td>'
            f'<td class="tel-value">{hum}%</td>'
            f'<td style="font-weight:bold;"><span class="tel-value" style="background:{color};padding:2px 8px;border-radius:4px;color:#333;">'
            f'{wbgt}℃</span></td>'
            f'<td><span style="background:{color};padding:2px 8px;border-radius:4px;color:#333;">'
            f'{level}</span></td>'
            f'<td>{advice}</td>'
            f'</tr>'
        )

    # 出典リンク
    source_links = ""
    for s in sources:
        safe_s = html.escape(s)
        # URLを抽出してリンク化
        if s.startswith("https://"):
            url_part = s.split(" ")[0]
            if url_part.startswith("https://"):
                label_part = s[len(url_part):].strip(" ()")
                source_links += f'<a href="{html.escape(url_part)}" target="_blank" rel="noopener">{html.escape(label_part) if label_part else html.escape(url_part)}</a> '
            else:
                source_links += safe_s + " "
        else:
            source_links += safe_s + " "

    return (
        f'<h1>🥵 {safe_niche}</h1>'
        '<p>Open-Meteo APIの気温・湿度・日射量・風速から<strong>WBGT(暑さ指数)</strong>を算出し、'
        '環境省の基準に基づいて熱中症リスクを判定します。'
        'WBGT28℃以上で激しい運動を控え、31℃以上では原則中止が推奨されます。</p>'
        '<div class="card-grid">'
        + summary_cards +
        '</div>'
        '<h2>📊 WBGT基準値(環境省準拠)</h2>'
        '<table>'
        '<thead><tr><th>レベル</th><th>WBGT目安</th><th>行動指針</th></tr></thead>'
        '<tbody>' + legend_html + '</tbody>'
        '</table>'
        '<h2>🗾 主要都市の暑さ指数一覧</h2>'
        '<p>※ WBGTはOpen-Meteoの現況データ(気温・湿度・日射量・風速)から計算した推定値です。'
        '公式の観測値とは異なる場合があります。</p>'
        '<table>'
        '<thead><tr>'
        '<th>都市</th><th>気温</th><th>湿度</th>'
        '<th>WBGT推定値</th><th>危険レベル</th><th>行動指針</th>'
        '</tr></thead>'
        '<tbody>' + city_rows + '</tbody>'
        '</table>'
        '<h2>💡 熱中症予防のポイント</h2>'
        '<ul>'
        '<li>WBGT28℃以上は激しい運動・作業を避け、こまめな休憩を取ってください。</li>'
        '<li>のどが渇く前に水分補給を行いましょう(目安: 1時間に200〜300ml)。</li>'
        '<li>室内でもエアコンを適切に活用し、熱がこもらないよう換気してください。</li>'
        '<li>高齢者・乳幼児・持病のある方は特に注意が必要です。</li>'
        '<li>異常を感じたらすぐに涼しい場所へ移動し、医療機関に相談してください。</li>'
        '</ul>'
        f'<div class="source">データ取得: {fetched_at} | 出典: {source_links}'
        ' | WBGT算出式はISO 7243・環境省指針に基づく推定値。</div>'
    )

