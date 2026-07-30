"""kind_generator.py が自動生成したプラグイン: earthquake"""

import requests

KIND_NAME = "earthquake"
KEYWORDS = ["地震", "震度", "地震情報", "earthquake", "seismic", "地震速報", "震源", "マグニチュード"]

import requests
from datetime import datetime, timezone


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    USGS Earthquake GeoJSON Feed APIから直近1ヶ月の重要地震情報を取得する。
    """
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    earthquakes = []
    for f in features[:20]:  # 最大20件
        props = f.get("properties", {})
        geo = f.get("geometry", {})
        coords = geo.get("coordinates", [None, None, None])
        mag = props.get("mag")
        place = props.get("place", "不明")
        time_ms = props.get("time")
        status = props.get("status", "")
        tsunami = props.get("tsunami", 0)
        felt = props.get("felt")
        detail_url = props.get("url", "")

        if time_ms:
            dt = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        else:
            time_str = "不明"

        earthquakes.append({
            "magnitude": mag,
            "place": place,
            "time": time_str,
            "longitude": coords[0],
            "latitude": coords[1],
            "depth_km": coords[2],
            "tsunami": bool(tsunami),
            "felt": felt,
            "status": status,
            "url": detail_url,
        })

    count = len(earthquakes)
    max_mag = max((e["magnitude"] for e in earthquakes if e["magnitude"] is not None), default=0)
    meta = data.get("metadata", {})
    generated_ms = meta.get("generated")
    if generated_ms:
        gen_dt = datetime.fromtimestamp(generated_ms / 1000, tz=timezone.utc)
        generated_str = gen_dt.strftime("%Y-%m-%d %H:%M UTC")
    else:
        generated_str = "不明"

    summary = (
        f"直近1ヶ月の重要地震: 計{count}件。"
        f"最大マグニチュード: M{max_mag:.1f}。"
        f"データ生成日時: {generated_str}。"
        f"出典: USGS Earthquake Hazards Program。"
    )

    sources = [
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson (USGS Earthquake GeoJSON Feed)",
        "https://earthquake.usgs.gov/ (USGS Earthquake Hazards Program)",
    ]

    raw = {
        "earthquakes": earthquakes,
        "count": count,
        "max_magnitude": max_mag,
        "generated": generated_str,
    }

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: 完成品のHTML文字列を返す。"""
    earthquakes = raw_data.get("earthquakes", [])
    count = raw_data.get("count", 0)
    max_mag = raw_data.get("max_magnitude", 0)
    generated = raw_data.get("generated", "不明")

    rows = ""
    for e in earthquakes:
        mag = e["magnitude"]
        if mag is None:
            mag_str = "N/A"
            mag_class = ""
        else:
            mag_str = f"{mag:.1f}"
            if mag >= 8.0:
                mag_class = "mag-extreme"
            elif mag >= 7.0:
                mag_class = "mag-high"
            elif mag >= 6.0:
                mag_class = "mag-mid"
            else:
                mag_class = "mag-low"

        tsunami_badge = '<span class="badge-tsunami">津波あり</span>' if e["tsunami"] else ""
        felt_str = str(e["felt"]) if e["felt"] is not None else "-"
        lat = e["latitude"]
        lon = e["longitude"]
        depth = e["depth_km"]
        lat_str = f"{lat:.3f}" if lat is not None else "-"
        lon_str = f"{lon:.3f}" if lon is not None else "-"
        depth_str = f"{depth:.1f} km" if depth is not None else "-"
        detail_link = f'<a href="{e["url"]}" target="_blank" rel="noopener">詳細</a>' if e["url"] else "-"

        rows += f"""
        <tr>
          <td><span class="mag-badge {mag_class}">{mag_str}</span></td>
          <td>{e['place']}{tsunami_badge}</td>
          <td>{e['time']}</td>
          <td>{lat_str}</td>
          <td>{lon_str}</td>
          <td>{depth_str}</td>
          <td>{felt_str}</td>
          <td>{detail_link}</td>
        </tr>"""

    sources_html = "".join(
        f'<li><a href="{s.split(" (")[0]}" target="_blank" rel="noopener">{s}</a></li>'
        for s in sources
    )

    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{niche} | 地震情報ダッシュボード</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: 'Segoe UI', 'Helvetica Neue', Arial, 'Noto Sans JP', sans-serif;
      background: #0f1117;
      color: #e0e0e0;
    }}
    header {{
      background: linear-gradient(135deg, #1a1f35 0%, #2d1b4e 100%);
      padding: 2rem 1.5rem 1.5rem;
      border-bottom: 2px solid #7b3fe4;
      text-align: center;
    }}
    header h1 {{
      margin: 0 0 0.4rem;
      font-size: 2rem;
      color: #ffffff;
      letter-spacing: 0.02em;
    }}
    header p {{
      margin: 0;
      color: #a0a8c0;
      font-size: 0.9rem;
    }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      justify-content: center;
      padding: 1.5rem 1rem;
    }}
    .stat-card {{
      background: #1e2235;
      border: 1px solid #2e3455;
      border-radius: 12px;
      padding: 1.2rem 2rem;
      text-align: center;
      min-width: 160px;
    }}
    .stat-card .value {{
      font-size: 2rem;
      font-weight: 700;
      color: #9d6fee;
    }}
    .stat-card .label {{
      font-size: 0.8rem;
      color: #7080a0;
      margin-top: 0.3rem;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 1rem 2rem;
    }}
    h2 {{
      color: #c0a8f0;
      border-left: 4px solid #7b3fe4;
      padding-left: 0.8rem;
      margin: 1.5rem 0 1rem;
      font-size: 1.1rem;
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 10px;
      border: 1px solid #2e3455;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }}
    thead tr {{
      background: #1a2040;
      color: #8090c0;
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
    }}
    th, td {{
      padding: 0.7rem 0.9rem;
      text-align: left;
      white-space: nowrap;
    }}
    tbody tr {{
      border-top: 1px solid #1e2540;
      transition: background 0.15s;
    }}
    tbody tr:hover {{
      background: #1a2240;
    }}
    .mag-badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 1rem;
    }}
    .mag-extreme {{ background: #7b0000; color: #ffcccc; }}
    .mag-high    {{ background: #7b3300; color: #ffd8a0; }}
    .mag-mid     {{ background: #3a3300; color: #fff0a0; }}
    .mag-low     {{ background: #1a3a1a; color: #b8f0b8; }}
    .badge-tsunami {{
      display: inline-block;
      margin-left: 0.5rem;
      background: #b00020;
      color: #fff;
      font-size: 0.7rem;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      vertical-align: middle;
      font-weight: 700;
    }}
    a {{ color: #9d8fe0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .sources {{
      margin-top: 2rem;
      padding: 1rem 1.2rem;
      background: #161b2e;
      border-radius: 8px;
      border: 1px solid #2e3455;
      font-size: 0.8rem;
      color: #6070a0;
    }}
    .sources ul {{ margin: 0.5rem 0 0; padding-left: 1.2rem; }}
    .sources li {{ margin-bottom: 0.3rem; }}
    footer {{
      text-align: center;
      color: #404060;
      font-size: 0.75rem;
      padding: 1.5rem;
      border-top: 1px solid #1e2235;
    }}
  </style>
</head>
<body>
  <header>
    <h1>&#x1F30D; {niche}</h1>
    <p>USGS が認定した重要地震（直近1ヶ月）&nbsp;|&nbsp;データ更新: {generated}</p>
  </header>

  <div class="stats">
    <div class="stat-card">
      <div class="value">{count}</div>
      <div class="label">直近1ヶ月の重要地震数</div>
    </div>
    <div class="stat-card">
      <div class="value">M{max_mag:.1f}</div>
      <div class="label">最大マグニチュード</div>
    </div>
  </div>

  <div class="container">
    <h2>&#x26A0;&#xFE0F; 地震リスト（直近1ヶ月・重要地震）</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>M</th>
            <th>場所</th>
            <th>発生日時 (UTC)</th>
            <th>緯度</th>
            <th>経度</th>
            <th>深さ</th>
            <th>体感報告数</th>
            <th>詳細</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>

    <div class="sources">
      <strong>&#x1F4CB; データ出典</strong>
      <ul>{sources_html}</ul>
    </div>
  </div>

  <footer>
    本データは USGS Earthquake Hazards Program の公開フィードを使用しています。
    情報は参考値であり、避難等の判断には各国公式機関の情報をご確認ください。
  </footer>
</body>
</html>"""
    return html

