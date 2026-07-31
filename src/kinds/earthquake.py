"""kind_generator.py が自動生成したプラグイン: earthquake"""

import html
import requests
from datetime import datetime, timezone

KIND_NAME = "earthquake"
KEYWORDS = ["地震", "震災", "地震情報", "seismic", "earthquake", "震度", "マグニチュード", "地震速報"]
CATEGORY = "天気・防災"


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    USGS公開APIから過去24時間のM2.5以上の地震データを取得する。"""
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    total = len(features)

    # 上位10件を取得(magnitudeでソート済みのケースが多いが念のため降順ソート)
    sorted_features = sorted(
        features,
        key=lambda f: f.get("properties", {}).get("mag") or 0,
        reverse=True
    )[:10]

    earthquakes = []
    for f in sorted_features:
        props = f.get("properties", {})
        geo = f.get("geometry", {})
        coords = geo.get("coordinates", [None, None, None])
        mag = props.get("mag")
        place = props.get("place") or "不明"
        time_ms = props.get("time")
        detail_url = props.get("url") or ""
        depth = coords[2] if len(coords) > 2 else None

        if time_ms:
            dt = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        else:
            time_str = "不明"

        earthquakes.append({
            "mag": mag,
            "place": str(place),
            "time": time_str,
            "depth_km": depth,
            "url": detail_url if isinstance(detail_url, str) and detail_url.startswith("https://") else ""
        })

    # 最大規模
    max_mag = earthquakes[0]["mag"] if earthquakes else None
    max_place = earthquakes[0]["place"] if earthquakes else "不明"

    summary = (
        f"過去24時間にM2.5以上の地震が世界で{total}件発生しました。"
        f"最大規模はM{max_mag}（{max_place}）です。"
        f"上位{len(earthquakes)}件を一覧表示しています。"
    )

    sources = [
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson (USGS Earthquake Hazards Program)"
    ]

    raw = {
        "total": total,
        "earthquakes": earthquakes,
        "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    }

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    total = raw_data.get("total", 0)
    earthquakes = raw_data.get("earthquakes", [])
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    safe_niche = html.escape(niche)

    rows = []
    for eq in earthquakes:
        mag = eq.get("mag")
        mag_val = float(mag) if mag is not None else 0.0
        place = html.escape(str(eq.get("place", "不明")))
        time_str = html.escape(str(eq.get("time", "不明")))
        depth = eq.get("depth_km")
        depth_str = html.escape(f"{depth:.1f} km") if depth is not None else html.escape("不明")
        detail_url = eq.get("url", "")

        # マグニチュードに応じた色分け
        if mag_val >= 7.0:
            mag_class = "mag-extreme"
        elif mag_val >= 6.0:
            mag_class = "mag-high"
        elif mag_val >= 5.0:
            mag_class = "mag-mid"
        else:
            mag_class = "mag-low"

        mag_display = html.escape(str(mag)) if mag is not None else "不明"

        if detail_url and detail_url.startswith("https://"):
            link = f'<a href="{html.escape(detail_url)}" target="_blank" rel="noopener">詳細</a>'
        else:
            link = "-"

        rows.append(
            f'<tr>'
            f'<td><span class="mag-badge {mag_class} tel-value">M {mag_display}</span></td>'
            f'<td>{place}</td>'
            f'<td class="tel-value">{time_str}</td>'
            f'<td class="tel-value">{depth_str}</td>'
            f'<td>{link}</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows) if rows else '<tr><td colspan="5">データなし</td></tr>'

    source_items = "".join(
        f'<li>{html.escape(s)}</li>' for s in sources
    )

    return (
        f'<h1>\U0001f30d {safe_niche}</h1>'
        f'<p>過去24時間（M2.5以上）の世界の地震情報をリアルタイムで表示します。'
        f'データはUSGS（米国地質調査所）の公開フィードから取得しています。</p>'
        f'<p>\U0001f4cb 取得件数: <strong class="tel-value">{html.escape(str(total))}件</strong>　'
        f'取得日時: {fetched_at}</p>'
        '<table>'
        '<thead>'
        '<tr>'
        '<th>マグニチュード</th>'
        '<th>発生場所</th>'
        '<th>発生日時 (UTC)</th>'
        '<th>深さ</th>'
        '<th>詳細</th>'
        '</tr>'
        '</thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
        '<div class="source">'
        'データ出典:<ul>'
        f'{source_items}'
        '</ul>'
        '</div>'
    )

