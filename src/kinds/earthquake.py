"""kind_generator.py が自動生成したプラグイン: earthquake"""

import requests
from datetime import datetime, timezone

KIND_NAME = "earthquake"
KEYWORDS = ["地震", "震度", "地震情報", "seismic", "earthquake", "震源", "マグニチュード"]


def fetch(niche: str) -> tuple:
    """
    researcher.py の契約:
    (summary: str, sources: list, raw_data: dict) を返す。
    USGS Earthquake API から直近72時間のM4.5以上の地震データを取得する。
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "minmagnitude": "4.5",
        "orderby": "time",
        "limit": "20",
        "starttime": _hours_ago_iso(72),
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    count = len(features)
    max_mag = max((f["properties"]["mag"] or 0.0 for f in features), default=0.0)

    events = []
    for f in features:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [None, None, None])
        ts = props.get("time")
        dt_str = ""
        if ts:
            dt_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        events.append({
            "place": props.get("place") or "不明",
            "magnitude": props.get("mag"),
            "depth_km": coords[2] if len(coords) > 2 else None,
            "lon": coords[0] if len(coords) > 0 else None,
            "lat": coords[1] if len(coords) > 1 else None,
            "time": dt_str,
            "url": props.get("url") or "",
            "status": props.get("status") or "",
            "tsunami": props.get("tsunami") or 0,
        })

    summary = (
        f"直近72時間のM4.5以上の地震: {count}件。"
        f"最大マグニチュード: {max_mag}。"
        f"データ取得時刻: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}。"
    )
    sources = ["https://earthquake.usgs.gov/fdsnws/event/1/ (USGS Earthquake Hazards Program)"]
    raw = {
        "count": count,
        "max_magnitude": max_mag,
        "events": events,
        "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return summary, sources, raw


def _hours_ago_iso(hours: int) -> str:
    """現在時刻からhours時間前のISO8601文字列を返す(UTC)。"""
    from datetime import timedelta
    dt = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.py の契約:
    ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    <!doctype/<html/<head/<body/<style は一切含めない。
    """
    count = raw_data.get("count", 0)
    max_mag = raw_data.get("max_magnitude", 0.0)
    fetched_at = raw_data.get("fetched_at", "")
    events = raw_data.get("events", [])

    # サマリーカード
    cards_html = (
        '<div class="summary-cards" style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px;">'
        f'<div class="card" style="flex:1;min-width:140px;padding:16px;background:#fff3cd;border-radius:8px;text-align:center;">'
        f'<div style="font-size:2em;font-weight:bold;">{count}</div>'
        f'<div>直近72h 発生件数</div></div>'
        f'<div class="card" style="flex:1;min-width:140px;padding:16px;background:#f8d7da;border-radius:8px;text-align:center;">'
        f'<div style="font-size:2em;font-weight:bold;">M{max_mag}</div>'
        f'<div>最大マグニチュード</div></div>'
        f'<div class="card" style="flex:1;min-width:140px;padding:16px;background:#d1ecf1;border-radius:8px;text-align:center;">'
        f'<div style="font-size:1.1em;font-weight:bold;">{fetched_at}</div>'
        f'<div>データ取得時刻</div></div>'
        '</div>'
    )

    # テーブル行を構築
    rows = []
    for ev in events:
        mag = ev.get("magnitude")
        mag_str = f"{mag:.1f}" if mag is not None else "-"
        # マグニチュードに応じて行の色を変える
        if mag is not None and mag >= 7.0:
            row_style = 'style="background:#f8d7da;"'
        elif mag is not None and mag >= 6.0:
            row_style = 'style="background:#fff3cd;"'
        else:
            row_style = ''

        depth = ev.get("depth_km")
        depth_str = f"{depth:.1f} km" if depth is not None else "-"

        lat = ev.get("lat")
        lon = ev.get("lon")
        coord_str = f"{lat:.2f}, {lon:.2f}" if (lat is not None and lon is not None) else "-"

        tsunami_str = "⚠️ あり" if ev.get("tsunami") else "なし"
        place = ev.get("place", "-")
        time_str = ev.get("time", "-")
        detail_url = ev.get("url", "")
        place_cell = (
            f'<a href="{detail_url}" target="_blank" rel="noopener noreferrer">{place}</a>'
            if detail_url else place
        )

        rows.append(
            f"<tr {row_style}>"
            f"<td>{time_str}</td>"
            f"<td>{place_cell}</td>"
            f"<td style='text-align:center;font-weight:bold;'>{mag_str}</td>"
            f"<td style='text-align:center;'>{depth_str}</td>"
            f"<td style='text-align:center;'>{coord_str}</td>"
            f"<td style='text-align:center;'>{tsunami_str}</td>"
            "</tr>"
        )

    rows_html = "\n".join(rows) if rows else "<tr><td colspan='6'>データなし</td></tr>"

    table_html = (
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:#343a40;color:#fff;">'
        '<th style="padding:10px;text-align:left;">発生日時 (UTC)</th>'
        '<th style="padding:10px;text-align:left;">震源地</th>'
        '<th style="padding:10px;text-align:center;">M</th>'
        '<th style="padding:10px;text-align:center;">深さ</th>'
        '<th style="padding:10px;text-align:center;">緯度, 経度</th>'
        '<th style="padding:10px;text-align:center;">津波</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
        '</div>'
    )

    source_list = ", ".join(sources)
    source_html = f'<div class="source" style="margin-top:20px;font-size:0.85em;color:#666;">データ出典: {source_list}</div>'

    return (
        f'<h1>🌏 {niche}</h1>'
        f'<p>直近72時間以内に世界各地で発生したマグニチュード4.5以上の地震をリアルタイムで表示します。'
        f'行が赤色のものはM7.0以上、黄色はM6.0以上の強い地震です。</p>'
        + cards_html
        + table_html
        + source_html
    )

