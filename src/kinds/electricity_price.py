"""kind_generator.py が自動生成したプラグイン: electricity_price"""

import requests
import html
import json
from datetime import datetime, timezone, timedelta

KIND_NAME = "electricity_price"
KEYWORDS = ["電力", "電気料金", "スポット価格", "JEPX", "電力市場", "electricity", "power price", "energy market"]
CATEGORY = "生活計算"

# 対応国リスト: (country_code, 表示名)
COUNTRY_LIST = [
    ("de", "ドイツ"),
    ("fr", "フランス"),
    ("at", "オーストリア"),
    ("ch", "スイス"),
    ("nl", "オランダ"),
    ("be", "ベルギー"),
    ("es", "スペイン"),
    ("it", "イタリア"),
    ("pl", "ポーランド"),
    ("se", "スウェーデン"),
]


def _fetch_price(country_code: str):
    """energy-charts.info から直近の電力スポット価格を取得する。"""
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=1)).isoformat()
    end = today.isoformat()
    url = (
        f"https://api.energy-charts.info/price"
        f"?bzn={country_code.upper()}&start={start}&end={end}"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data


def fetch(niche: str) -> tuple:
    """
    researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    energy-charts.info API から欧州複数国の電力スポット価格を取得する。
    """
    results = []
    errors = []

    for code, name in COUNTRY_LIST:
        try:
            data = _fetch_price(code)
            prices = data.get("price", [])
            timestamps = data.get("unix_seconds", [])
            if not prices or not timestamps:
                errors.append(f"{name}: データなし")
                continue

            # 最新の有効な価格を取得
            latest_price = None
            latest_ts = None
            for ts, pr in zip(timestamps, prices):
                if pr is not None:
                    latest_price = pr
                    latest_ts = ts

            if latest_price is None:
                errors.append(f"{name}: 有効価格なし")
                continue

            dt = datetime.fromtimestamp(latest_ts, tz=timezone.utc)
            results.append({
                "country_code": code,
                "country_name": name,
                "price_eur_mwh": latest_price,
                "price_eur_kwh": round(latest_price / 1000, 4),
                "timestamp_utc": dt.strftime("%Y-%m-%d %H:%M UTC"),
                "all_prices": prices[-24:],
                "all_timestamps": [datetime.fromtimestamp(t, tz=timezone.utc).strftime("%H:%M") for t in timestamps[-24:]],
            })
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

    if not results:
        raise RuntimeError(
            f"全ての国の電力スポット価格取得に失敗しました。エラー: {'; '.join(errors)}"
        )

    # サマリー作成
    summary_lines = [f"欧州電力スポット価格 (EUR/MWh) — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"]
    for r in results:
        summary_lines.append(
            f"{r['country_name']}: {r['price_eur_mwh']:.2f} EUR/MWh ({r['timestamp_utc']})"
        )
    summary = "\n".join(summary_lines)

    sources = [
        "https://api.energy-charts.info/ (energy-charts.info — Fraunhofer ISE)",
        "https://www.energy-charts.info/ (Energy Charts公式サイト)",
    ]

    raw = {
        "results": results,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "errors": errors,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    """
    results = raw_data.get("results", [])
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    errors = raw_data.get("errors", [])

    safe_niche = html.escape(str(niche))

    rows = []
    for r in results:
        country = html.escape(str(r.get("country_name", "")))
        code = html.escape(str(r.get("country_code", "")).lower())
        price_mwh = r.get("price_eur_mwh", 0)
        price_kwh = r.get("price_eur_kwh", 0)
        ts = html.escape(str(r.get("timestamp_utc", "")))

        # 価格に応じた色分け
        if price_mwh < 0:
            price_class = "price-negative"
        elif price_mwh < 50:
            price_class = "price-low"
        elif price_mwh < 150:
            price_class = "price-mid"
        else:
            price_class = "price-high"

        price_mwh_str = html.escape(f"{price_mwh:.2f}")
        price_kwh_str = html.escape(f"{price_kwh:.4f}")

        # 直近24時間のスパークライン用データ
        all_prices = r.get("all_prices", [])
        all_ts = r.get("all_timestamps", [])
        chart_id = f"chart-{code}"

        # スパークライン: SVG簡易棒グラフ
        spark = _build_sparkline(all_prices, all_ts, chart_id)

        rows.append(
            f'<tr>'
            f'<td><strong>{country}</strong><br><small class="muted">{code.upper()}</small></td>'
            f'<td class="tel-value {price_class}">{price_mwh_str}</td>'
            f'<td class="tel-value">{price_kwh_str}</td>'
            f'<td><span class="muted" style="font-size:0.85em">{ts}</span></td>'
            f'<td>{spark}</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows) if rows else '<tr><td colspan="5">データなし</td></tr>'

    errors_html = ""
    if errors:
        err_items = "".join(f"<li>{html.escape(str(e))}</li>" for e in errors)
        errors_html = f'<details><summary>取得エラー詳細 ({len(errors)}件)</summary><ul>{err_items}</ul></details>'

    source_links = ""
    for s in sources:
        if "(" in s:
            url_part, label_part = s.split("(", 1)
            url_str = url_part.strip()
            label_str = label_part.rstrip(")")
        else:
            url_str = s.strip()
            label_str = s.strip()
        safe_url = html.escape(url_str) if url_str.startswith("https://") else "#"
        safe_label = html.escape(label_str)
        source_links += f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_label}</a> '

    # 価格の説明
    explanation = (
        "<p>欧州の電力卸売市場（Day-Ahead Market）における各国のスポット価格です。"
        "価格はEUR/MWh（メガワット時あたりユーロ）で表示されています。"
        "<strong>マイナス価格</strong>は再生可能エネルギーの余剰供給時に発生します。"
        "データはFraunhofer ISEが運営するEnergy Charts APIから取得しています。</p>"
    )

    legend = (
        '<div class="legend" style="margin:0.5em 0;font-size:0.9em">'
        '<span class="price-negative">■ マイナス価格</span> '
        '<span class="price-low">■ 低価格 (&lt;50)</span> '
        '<span class="price-mid">■ 標準 (50–150)</span> '
        '<span class="price-high">■ 高騰 (&gt;150)</span>'
        '</div>'
    )

    table = (
        f'<table>'
        f'<thead><tr>'
        f'<th>国</th>'
        f'<th>EUR/MWh</th>'
        f'<th>EUR/kWh</th>'
        f'<th>時刻 (UTC)</th>'
        f'<th>直近推移</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )

    return (
        f'<h1>⚡ {safe_niche}</h1>'
        f'{explanation}'
        f'<p class="muted">取得日時: <span class="tel-value">{fetched_at}</span> | '
        f'表示: <span class="tel-value">{len(results)}</span>か国</p>'
        f'{legend}'
        f'{table}'
        f'{errors_html}'
        f'<div class="source">データ出典: {source_links}</div>'
    )


def _build_sparkline(prices: list, timestamps: list, chart_id: str) -> str:
    """直近24時間の電力価格をSVGミニバーチャートで描画する。"""
    if not prices:
        return '<span class="muted">-</span>'

    valid = [(t, p) for t, p in zip(timestamps, prices) if p is not None]
    if not valid:
        return '<span class="muted">-</span>'

    ts_list = [v[0] for v in valid]
    p_list = [v[1] for v in valid]

    w, h = 120, 32
    n = len(p_list)
    p_min = min(p_list)
    p_max = max(p_list)
    p_range = p_max - p_min if p_max != p_min else 1

    bar_w = max(1, w // n)
    bars = []
    for i, (ts, p) in enumerate(zip(ts_list, p_list)):
        bar_h = max(1, int((p - p_min) / p_range * (h - 4)) + 2)
        x = i * bar_w
        y = h - bar_h
        color = "#e74c3c" if p < 0 else ("#2ecc71" if p < 50 else ("#f39c12" if p < 150 else "#c0392b"))
        safe_ts = html.escape(str(ts))
        safe_p = html.escape(f"{p:.1f}")
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w-1}" height="{bar_h}" '
            f'fill="{color}" opacity="0.85">'
            f'<title>{safe_ts} {safe_p} EUR/MWh</title></rect>'
        )

    bars_html = "".join(bars)
    return (
        f'<svg id="{html.escape(chart_id)}" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" style="display:block">'
        f'{bars_html}'
        f'</svg>'
    )

