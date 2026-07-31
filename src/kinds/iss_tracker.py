"""kind_generator.py が自動生成したプラグイン: iss_tracker"""

import requests
import html
import datetime

KIND_NAME = "iss_tracker"
KEYWORDS = ["ISS", "国際宇宙ステーション", "宇宙ステーション", "ISSトラッカー", "ISS位置", "international space station"]
CATEGORY = "天文・暦"


def fetch(niche: str) -> tuple:
    """
    wheretheiss.at API からISSのリアルタイム位置情報を取得する。
    """
    url = "https://api.wheretheiss.at/v1/satellites/25544"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    altitude = data.get("altitude")
    velocity = data.get("velocity")
    timestamp = data.get("timestamp")
    visibility = data.get("visibility", "")
    footprint = data.get("footprint")

    if latitude is None or longitude is None:
        raise RuntimeError("ISSの位置データが取得できませんでした。")

    dt_utc = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S UTC") if timestamp else "不明"

    # 緯度・経度から大まかな位置説明を生成
    lat_dir = "北緯" if latitude >= 0 else "南緯"
    lon_dir = "東経" if longitude >= 0 else "西経"
    summary = (
        f"ISS(国際宇宙ステーション)は現在、{lat_dir}{abs(latitude):.4f}度・"
        f"{lon_dir}{abs(longitude):.4f}度の上空約{altitude:.1f}kmを"
        f"時速{velocity:.1f}kmで飛行中({dt_utc})。"
    )

    sources = ["https://wheretheiss.at/ (Where the ISS at?)"]
    raw = {
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "velocity": velocity,
        "timestamp": timestamp,
        "dt_utc": dt_utc,
        "visibility": visibility,
        "footprint": footprint,
        "lat_dir": lat_dir,
        "lon_dir": lon_dir,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    ISSリアルタイム位置情報のHTML断片を返す。
    """
    latitude = raw_data.get("latitude", 0.0)
    longitude = raw_data.get("longitude", 0.0)
    altitude = raw_data.get("altitude", 0.0)
    velocity = raw_data.get("velocity", 0.0)
    dt_utc = html.escape(str(raw_data.get("dt_utc", "不明")))
    visibility = html.escape(str(raw_data.get("visibility", "")))
    footprint = raw_data.get("footprint")
    lat_dir = html.escape(str(raw_data.get("lat_dir", "北緯")))
    lon_dir = html.escape(str(raw_data.get("lon_dir", "東経")))

    lat_abs = abs(latitude)
    lon_abs = abs(longitude)

    # OpenStreetMapの埋め込みURL(ISSの現在位置を表示)
    osm_url = f"https://www.openstreetmap.org/?mlat={latitude:.4f}&mlon={longitude:.4f}&zoom=3"
    safe_osm_url = html.escape(osm_url)

    # Google Maps URL
    gmaps_url = f"https://www.google.com/maps?q={latitude:.4f},{longitude:.4f}&z=3"
    safe_gmaps_url = html.escape(gmaps_url)

    visibility_label = ""
    if visibility == "daylight":
        visibility_label = "☀️ 昼間(太陽光あり)"
    elif visibility == "eclipsed":
        visibility_label = "🌑 夜間(地球の影)"
    else:
        visibility_label = html.escape(visibility) if visibility else "不明"

    footprint_str = f"{footprint:.1f} km" if footprint is not None else "不明"

    source_items = "".join(
        f'<li><a href="{html.escape(s.split(" ")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a></li>'
        for s in sources
    )

    html_out = (
        f'<h1>🛰️ {html.escape(niche)}</h1>'
        '<p>国際宇宙ステーション(ISS)のリアルタイム位置情報です。'
        'データは <a href="https://wheretheiss.at/" target="_blank" rel="noopener">Where the ISS at?</a> APIより取得しています。</p>'
        '<table>'
        '<thead><tr><th>項目</th><th>値</th></tr></thead>'
        '<tbody>'
        f'<tr><th>📍 現在位置（緯度）</th><td class="tel-value">{lat_dir} {lat_abs:.4f}°</td></tr>'
        f'<tr><th>📍 現在位置（経度）</th><td class="tel-value">{lon_dir} {lon_abs:.4f}°</td></tr>'
        f'<tr><th>🌐 高度</th><td class="tel-value">約 {altitude:.1f} km</td></tr>'
        f'<tr><th>⚡ 速度</th><td class="tel-value">{velocity:.1f} km/h（約 {velocity/3600:.2f} km/s）</td></tr>'
        f'<tr><th>☀️ 照明状態</th><td>{visibility_label}</td></tr>'
        f'<tr><th>📡 観測フットプリント直径</th><td class="tel-value">{html.escape(footprint_str)}</td></tr>'
        f'<tr><th>🕐 取得時刻（UTC）</th><td class="tel-value">{dt_utc}</td></tr>'
        '</tbody>'
        '</table>'
        '<p>'
        f'🗺️ 地図で確認: '
        f'<a href="{safe_osm_url}" target="_blank" rel="noopener">OpenStreetMap</a> / '
        f'<a href="{safe_gmaps_url}" target="_blank" rel="noopener">Google Maps</a>'
        '</p>'
        '<p><small>※ ISSは約90分で地球を1周します。このページを再読み込みすると最新の位置が表示されます。</small></p>'
        f'<div class="source">データ出典: <ul>{source_items}</ul></div>'
    )
    return html_out

