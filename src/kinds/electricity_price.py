"""kind_generator.py が自動生成したプラグイン: electricity_price"""

import requests
import html
import json
from datetime import datetime, timedelta, timezone

KIND_NAME = "electricity_price"
KEYWORDS = ["電気料金", "電力価格", "electricity price", "エネルギーコスト", "kWh", "電気代"]
CATEGORY = "生活計算"

# 入札ゾーンコードと表示名のマッピング
BIDDING_ZONES = [
    ("DE-LU", "ドイツ/ルクセンブルク"),
    ("FR",    "フランス"),
    ("AT",    "オーストリア"),
    ("CH",    "スイス"),
    ("BE",    "ベルギー"),
    ("NL",    "オランダ"),
    ("ES",    "スペイン"),
    ("IT-North", "イタリア北部"),
]

BASE_URL = "https://api.energy-charts.info/price"


def _fetch_zone(bzn: str, date_str: str) -> list:
    """指定ゾーン・日付のDay-Ahead価格リスト(EUR/MWh)を返す。失敗時は空リスト。"""
    params = {
        "bzn": bzn,
        "start": f"{date_str}T00:00+01:00",
        "end":   f"{date_str}T23:00+01:00",
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        prices = data.get("price", [])
        # 価格リストが存在し、数値が入っているものだけ返す
        return [p for p in prices if p is not None]
    except Exception:
        return []


def fetch(niche: str) -> tuple:
    """
    researcher.py契約: (summary: str, sources: list, raw_data: dict) を返す。
    energy-charts.info からEU主要入札ゾーンのDay-Ahead電力スポット価格を取得する。
    """
    # 今日(CET+1基準)の日付文字列
    now_cet = datetime.now(timezone(timedelta(hours=1)))
    today_str = now_cet.strftime("%Y-%m-%d")
    yesterday_str = (now_cet - timedelta(days=1)).strftime("%Y-%m-%d")

    results = []
    for bzn, label in BIDDING_ZONES:
        prices = _fetch_zone(bzn, today_str)
        if not prices:
            # 今日のデータがまだ無い場合は昨日のデータを試みる
            prices = _fetch_zone(bzn, yesterday_str)
        if prices:
            avg_price = sum(prices) / len(prices)
            max_price = max(prices)
            min_price = min(prices)
            results.append({
                "bzn": bzn,
                "label": label,
                "avg_eur_mwh": round(avg_price, 2),
                "max_eur_mwh": round(max_price, 2),
                "min_eur_mwh": round(min_price, 2),
                "hourly_count": len(prices),
                "date": today_str if _fetch_zone(bzn, today_str) else yesterday_str,
            })

    if not results:
        raise RuntimeError(
            "energy-charts.info から全入札ゾーンのデータ取得に失敗しました。"
        )

    # サマリー生成
    de_entry = next((r for r in results if r["bzn"] == "DE-LU"), results[0])
    summary = (
        f"{de_entry['date']} 時点のEU電力Day-Ahead価格({de_entry['label']}): "
        f"平均 {de_entry['avg_eur_mwh']} EUR/MWh、"
        f"最高 {de_entry['max_eur_mwh']} EUR/MWh、"
        f"最低 {de_entry['min_eur_mwh']} EUR/MWh。"
        f"取得ゾーン数: {len(results)}件。"
    )
    sources = [
        "https://api.energy-charts.info/ (Fraunhofer ISE energy-charts.info — 無料公開API)",
        "https://www.energy-charts.info/ (エネルギーチャート公式サイト)",
    ]
    raw = {
        "date": de_entry["date"],
        "zones": results,
        "unit": "EUR/MWh",
        "note": "Day-Ahead電力スポット価格(EPEX SPOT等市場データ)",
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.py契約: <h1>から出典表記までのHTML断片を返す。
    """
    safe_niche = html.escape(str(niche))
    date_str = html.escape(str(raw_data.get("date", "-")))
    unit = html.escape(str(raw_data.get("unit", "EUR/MWh")))
    note = html.escape(str(raw_data.get("note", "")))
    zones = raw_data.get("zones", [])

    # テーブル行を生成
    rows = []
    for z in zones:
        label = html.escape(str(z.get("label", "")))
        bzn   = html.escape(str(z.get("bzn", "")))
        avg   = html.escape(str(z.get("avg_eur_mwh", "-")))
        max_v = html.escape(str(z.get("max_eur_mwh", "-")))
        min_v = html.escape(str(z.get("min_eur_mwh", "-")))
        count = html.escape(str(z.get("hourly_count", "-")))
        rows.append(
            f'<tr>'
            f'<td>{label}</td>'
            f'<td class="tel-value">{bzn}</td>'
            f'<td class="tel-value">{avg}</td>'
            f'<td class="tel-value">{max_v}</td>'
            f'<td class="tel-value">{min_v}</td>'
            f'<td class="tel-value">{count}</td>'
            f'</tr>'
        )
    rows_html = "\n".join(rows) if rows else '<tr><td colspan="6">データなし</td></tr>'

    # 出典リンク
    source_links = []
    for s in sources:
        parts = s.split(" (", 1)
        url = parts[0].strip()
        label_s = parts[1].rstrip(")") if len(parts) > 1 else url
        safe_label_s = html.escape(label_s)
        safe_url = url if url.startswith("https://") else "#"
        source_links.append(f'<a href="{html.escape(safe_url)}" target="_blank" rel="noopener">{safe_label_s}</a>')
    source_html = " / ".join(source_links)

    return (
        f'<h1>⚡ {safe_niche}</h1>'
        f'<p>欧州主要入札ゾーンのDay-Ahead電力スポット価格(卸売市場価格)です。'
        f'データは <strong>{date_str}</strong> 時点。{note}</p>'
        f'<p>単位: <span class="tel-value">{unit}</span>'
        f'（1 EUR/MWh ≈ 0.1円/kWh相当の目安。為替・消費税・系統費用は含みません）</p>'
        f'<table>'
        f'<thead><tr>'
        f'<th>国・地域</th>'
        f'<th>入札ゾーン</th>'
        f'<th>平均 (EUR/MWh)</th>'
        f'<th>最高 (EUR/MWh)</th>'
        f'<th>最低 (EUR/MWh)</th>'
        f'<th>時間帯数</th>'
        f'</tr></thead>'
        f'<tbody>'
        f'{rows_html}'
        f'</tbody>'
        f'</table>'
        f'<div class="source">データ出典: {source_html}</div>'
    )

