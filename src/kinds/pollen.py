"""kind_generator.py が自動生成したプラグイン: pollen"""

import requests
import html
from datetime import datetime, timezone, timedelta

KIND_NAME = "pollen"
KEYWORDS = ["花粉", "花粉症", "飛散", "スギ", "ヒノキ", "pollen", "飛散量", "アレルギー"]
CATEGORY = "天気・防災"

# 主要都市の緯度経度
CITY_COORDS = {
    "東京": (35.6895, 139.6917, "東京"),
    "大阪": (34.6937, 135.5023, "大阪"),
    "名古屋": (35.1815, 136.9066, "名古屋"),
    "札幌": (43.0618, 141.3545, "札幌"),
    "福岡": (33.5904, 130.4017, "福岡"),
    "仙台": (38.2682, 140.8694, "仙台"),
    "広島": (34.3853, 132.4553, "広島"),
    "京都": (35.0116, 135.7681, "京都"),
    "横浜": (35.4437, 139.6380, "横浜"),
    "神戸": (34.6901, 135.1956, "神戸"),
    "千葉": (35.6074, 140.1065, "千葉"),
    "さいたま": (35.8616, 139.6455, "さいたま"),
    "熊本": (32.7898, 130.7417, "熊本"),
    "長野": (36.6486, 138.1948, "長野"),
    "新潟": (37.9026, 139.0232, "新潟"),
}

def _get_city(niche: str):
    for key, val in CITY_COORDS.items():
        if key in niche:
            return val
    return (35.6895, 139.6917, "東京")  # デフォルト

def _level_label(value: float) -> str:
    """花粉飛散量を日本語レベルに変換 (grains/m³)"""
    if value < 10:
        return "少ない"
    elif value < 50:
        return "やや多い"
    elif value < 200:
        return "多い"
    else:
        return "非常に多い"

def _level_emoji(value: float) -> str:
    if value < 10:
        return "🟢"
    elif value < 50:
        return "🟡"
    elif value < 200:
        return "🟠"
    else:
        return "🔴"

def fetch(niche: str) -> tuple:
    lat, lon, city_name = _get_city(niche)

    pollen_vars = [
        "alder_pollen",
        "birch_pollen",
        "grass_pollen",
        "mugwort_pollen",
        "olive_pollen",
        "ragweed_pollen",
    ]
    hourly_params = ",".join(pollen_vars)

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": hourly_params,
        "timezone": "Asia/Tokyo",
        "forecast_days": 3,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    # 現在時刻(JST)から直近72時間分を取得
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    now_str = now_jst.strftime("%Y-%m-%dT%H:00")

    # 直近の時刻インデックスを探す
    current_idx = 0
    for i, t in enumerate(times):
        if t <= now_str:
            current_idx = i

    # 現在時刻の各花粉値を取得
    current_values = {}
    for var in pollen_vars:
        vals = hourly.get(var, [])
        v = vals[current_idx] if current_idx < len(vals) else None
        current_values[var] = v if v is not None else 0.0

    # 今後24時間(8ステップ×3h or 24ステップ)の最大値
    forecast_hours = 24
    end_idx = min(current_idx + forecast_hours, len(times))
    forecast_rows = []
    for i in range(current_idx, end_idx, 3):  # 3時間おき
        if i >= len(times):
            break
        row = {"time": times[i]}
        for var in pollen_vars:
            vals = hourly.get(var, [])
            row[var] = vals[i] if i < len(vals) else 0.0
        forecast_rows.append(row)

    # 代表的な花粉(grass_pollenとbirch_pollenで日本の状況を近似)
    # 日本ではスギ・ヒノキが主だがAPIにはgrass/birch/alderで代替
    main_value = max(
        current_values.get("alder_pollen", 0) or 0,
        current_values.get("birch_pollen", 0) or 0,
        current_values.get("grass_pollen", 0) or 0,
    )
    level = _level_label(main_value)

    summary = (
        f"{city_name}の現在の花粉飛散情報: "
        f"代表花粉量 {main_value:.1f} grains/m³ ({level})。"
        f"ハンノキ花粉 {current_values.get('alder_pollen', 0):.1f}、"
        f"シラカバ花粉 {current_values.get('birch_pollen', 0):.1f}、"
        f"イネ科花粉 {current_values.get('grass_pollen', 0):.1f}。"
    )
    sources = ["https://air-quality-api.open-meteo.com/ (Open-Meteo Air Quality API)"]
    raw = {
        "city": city_name,
        "lat": lat,
        "lon": lon,
        "current_values": current_values,
        "main_value": main_value,
        "level": level,
        "forecast_rows": forecast_rows,
        "pollen_vars": pollen_vars,
        "fetched_at": now_jst.strftime("%Y-%m-%d %H:%M JST"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    city = html.escape(str(raw_data.get("city", "東京")))
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    main_value = raw_data.get("main_value", 0.0)
    level = html.escape(str(raw_data.get("level", "-")))
    current_values = raw_data.get("current_values", {})
    forecast_rows = raw_data.get("forecast_rows", [])

    emoji = _level_emoji(main_value)

    # 花粉種別の日本語名マッピング
    var_labels = {
        "alder_pollen": "ハンノキ花粉",
        "birch_pollen": "シラカバ花粉",
        "grass_pollen": "イネ科花粉",
        "mugwort_pollen": "ヨモギ花粉",
        "olive_pollen": "オリーブ花粉",
        "ragweed_pollen": "ブタクサ花粉",
    }

    # 現在の花粉種別テーブル
    current_rows_html = ""
    for var, label in var_labels.items():
        val = current_values.get(var, 0.0) or 0.0
        lv = _level_label(val)
        em = _level_emoji(val)
        current_rows_html += (
            f"<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td class='num tel-value'>{val:.1f}</td>"
            f"<td>{em} {html.escape(lv)}</td>"
            f"</tr>"
        )

    # 予報テーブル(3時間おき最大8行)
    forecast_html = ""
    for row in forecast_rows[:8]:
        t = html.escape(str(row.get("time", "")))
        # 時刻を見やすく整形
        try:
            dt = datetime.strptime(t, "%Y-%m-%dT%H:%M")
            t_disp = dt.strftime("%m/%d %H時")
        except Exception:
            t_disp = t
        # 全花粉の最大値
        max_v = max((row.get(var) or 0.0) for var in var_labels)
        em = _level_emoji(max_v)
        lv = _level_label(max_v)
        # 代表3種
        alder = row.get("alder_pollen") or 0.0
        birch = row.get("birch_pollen") or 0.0
        grass = row.get("grass_pollen") or 0.0
        forecast_html += (
            f"<tr>"
            f"<td class='tel-value'>{html.escape(t_disp)}</td>"
            f"<td class='num tel-value'>{alder:.1f}</td>"
            f"<td class='num tel-value'>{birch:.1f}</td>"
            f"<td class='num tel-value'>{grass:.1f}</td>"
            f"<td>{em} {html.escape(lv)}</td>"
            f"</tr>"
        )

    # 凡例
    legend_html = (
        "<ul class='legend'>"
        "<li>🟢 <strong>少ない</strong>: 0〜9 grains/m³</li>"
        "<li>🟡 <strong>やや多い</strong>: 10〜49 grains/m³</li>"
        "<li>🟠 <strong>多い</strong>: 50〜199 grains/m³</li>"
        "<li>🔴 <strong>非常に多い</strong>: 200以上 grains/m³</li>"
        "</ul>"
    )

    source_str = html.escape(sources[0]) if sources else ""

    return (
        f"<h1>🌿 {html.escape(niche)} 花粉飛散情報</h1>"
        f"<p>地域: <strong>{city}</strong> &nbsp;|&nbsp; 取得日時: {fetched_at}</p>"
        f"<div class='summary-box'>"
        f"<p>現在の花粉飛散レベル: <strong>{emoji} {level}</strong>"
        f" (代表値 {main_value:.1f} grains/m³)</p>"
        f"</div>"
        f"<h2>🔬 花粉種別の現在値</h2>"
        f"<table>"
        f"<thead><tr><th>花粉の種類</th><th>飛散量 (grains/m³)</th><th>レベル</th></tr></thead>"
        f"<tbody>{current_rows_html}</tbody>"
        f"</table>"
        f"<h2>📅 今後24時間の予報(3時間ごと)</h2>"
        f"<table>"
        f"<thead><tr><th>時刻</th><th>ハンノキ</th><th>シラカバ</th><th>イネ科</th><th>総合レベル</th></tr></thead>"
        f"<tbody>{forecast_html}</tbody>"
        f"</table>"
        f"<h2>📊 飛散レベルの目安</h2>"
        f"{legend_html}"
        f"<p class='note'>※ 提供APIはヨーロッパ気象モデルベースのため、日本固有のスギ・ヒノキ花粉は"
        f"シラカバ・ハンノキ花粉として近似表示されます。実際の飛散状況は気象庁・各地環境省発表情報も"
        f"合わせてご確認ください。</p>"
        f"<div class='source'>データ出典: <a href='https://open-meteo.com/' rel='noopener'>Open-Meteo Air Quality API</a>"
        f" ({html.escape(source_str)})</div>"
    )

