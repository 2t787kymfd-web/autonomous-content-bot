"""kind_generator.py が自動生成したプラグイン: asteroid"""

import requests
import html
from datetime import datetime, timedelta

KIND_NAME = "asteroid"
KEYWORDS = ["小惑星", "asteroid", "地球近傍", "NeoWs", "NASA", "天体", "接近天体", "NEO"]
CATEGORY = "天文・暦"


def fetch(niche: str) -> tuple:
    """
    NASA NeoWs API から直近7日間の地球近傍小惑星データを取得する。
    DEMO_KEY を使用するため APIキー・アカウント登録不要。
    """
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=6)
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        "start_date": today.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "api_key": "DEMO_KEY",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    near_earth_objects = data.get("near_earth_objects", {})
    if not near_earth_objects:
        raise RuntimeError("NASA NeoWs API からデータを取得できませんでした。")

    asteroids = []
    for date_str, objs in sorted(near_earth_objects.items()):
        for obj in objs:
            name = obj.get("name", "不明")
            is_hazardous = obj.get("is_potentially_hazardous_asteroid", False)
            estimated_diameter = obj.get("estimated_diameter", {})
            diam_km = estimated_diameter.get("kilometers", {})
            diam_min = diam_km.get("estimated_diameter_min", None)
            diam_max = diam_km.get("estimated_diameter_max", None)
            close_approaches = obj.get("close_approach_data", [])
            miss_km = None
            velocity_kmh = None
            approach_date = date_str
            if close_approaches:
                ca = close_approaches[0]
                miss_dist = ca.get("miss_distance", {})
                miss_km = miss_dist.get("kilometers", None)
                rel_vel = ca.get("relative_velocity", {})
                velocity_kmh = rel_vel.get("kilometers_per_hour", None)
                approach_date = ca.get("close_approach_date", date_str)
            nasa_url = obj.get("nasa_jpl_url", "")
            asteroids.append({
                "name": name,
                "approach_date": approach_date,
                "is_hazardous": is_hazardous,
                "diam_min_km": round(float(diam_min), 4) if diam_min is not None else None,
                "diam_max_km": round(float(diam_max), 4) if diam_max is not None else None,
                "miss_distance_km": round(float(miss_km)) if miss_km is not None else None,
                "velocity_kmh": round(float(velocity_kmh)) if velocity_kmh is not None else None,
                "nasa_url": nasa_url,
            })

    if not asteroids:
        raise RuntimeError("地球近傍小惑星のデータが0件でした。")

    # 危険度の高いものを先頭に、次に接近日でソート
    asteroids.sort(key=lambda x: (not x["is_hazardous"], x["approach_date"]))

    hazardous_count = sum(1 for a in asteroids if a["is_hazardous"])
    total_count = len(asteroids)
    period = f"{today.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}"

    summary = (
        f"期間 {period} に地球に接近する小惑星は {total_count} 個（うち潜在的危険天体: {hazardous_count} 個）。"
    )
    sources = ["https://api.nasa.gov/neo/rest/v1/feed (NASA NeoWs API)"]
    raw = {
        "period": period,
        "total_count": total_count,
        "hazardous_count": hazardous_count,
        "asteroids": asteroids[:30],  # 最大30件
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    地球近傍小惑星情報ページのHTML本文断片を生成する。
    """
    period = html.escape(str(raw_data.get("period", "")))
    total_count = int(raw_data.get("total_count", 0))
    hazardous_count = int(raw_data.get("hazardous_count", 0))
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    asteroids = raw_data.get("asteroids", [])

    rows = ""
    for a in asteroids:
        name = html.escape(str(a.get("name", "")))
        approach_date = html.escape(str(a.get("approach_date", "")))
        is_hazardous = a.get("is_hazardous", False)
        hazard_label = "<span style=\"color:#e74c3c;font-weight:bold;\">⚠ 危険</span>" if is_hazardous else "<span style=\"color:#27ae60;\">安全</span>"
        diam_min = a.get("diam_min_km")
        diam_max = a.get("diam_max_km")
        if diam_min is not None and diam_max is not None:
            diam_str = html.escape(f"{diam_min} ～ {diam_max} km")
        else:
            diam_str = "-"
        miss_km = a.get("miss_distance_km")
        miss_str = html.escape(f"{miss_km:,} km") if miss_km is not None else "-"
        velocity_kmh = a.get("velocity_kmh")
        vel_str = html.escape(f"{velocity_kmh:,} km/h") if velocity_kmh is not None else "-"
        nasa_url = a.get("nasa_url", "")
        if nasa_url and nasa_url.startswith("https://"):
            link = f'<a href="{html.escape(nasa_url)}" target="_blank" rel="noopener">詳細</a>'
        else:
            link = "-"
        rows += (
            f"<tr>"
            f"<td class=\"tel-value\">{approach_date}</td>"
            f"<td>{name}</td>"
            f"<td>{hazard_label}</td>"
            f"<td class=\"tel-value\">{diam_str}</td>"
            f"<td class=\"tel-value\">{miss_str}</td>"
            f"<td class=\"tel-value\">{vel_str}</td>"
            f"<td>{link}</td>"
            f"</tr>"
        )

    source_links = ""
    for s in sources:
        safe_s = html.escape(str(s))
        # URLを抽出してリンクにする
        if "(" in s:
            url_part = s.split("(")[0].strip()
            label_part = s.split("(")[1].rstrip(")")
        else:
            url_part = s
            label_part = s
        safe_url = html.escape(url_part)
        safe_label = html.escape(label_part)
        if url_part.startswith("https://"):
            source_links += f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_label}</a> '
        else:
            source_links += safe_s + " "

    return (
        f'<h1>☄️ {html.escape(niche)}</h1>'
        f'<p>NASAの地球近傍天体監視システム（NeoWs）が提供する、地球に接近する小惑星の最新情報です。'
        f'「潜在的危険天体」とは、地球との最接近距離が約750万km以内かつ直径140m以上の小惑星です。</p>'
        f'<div class="summary-box">'
        f'<p>📅 対象期間: <strong class="tel-value">{period}</strong></p>'
        f'<p>🪨 接近天体総数: <strong class="tel-value">{total_count} 個</strong>&nbsp;&nbsp;'
        f'⚠️ 潜在的危険天体: <strong style="color:#e74c3c;" class="tel-value">{hazardous_count} 個</strong></p>'
        f'</div>'
        f'<table>'
        f'<thead><tr>'
        f'<th>接近日</th><th>小惑星名</th><th>危険度</th>'
        f'<th>推定直径</th><th>最接近距離</th><th>相対速度</th><th>詳細</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'<p style="font-size:0.85em;color:#888;">最終取得: {fetched_at}</p>'
        f'<div class="source">データ出典: {source_links}</div>'
    )

