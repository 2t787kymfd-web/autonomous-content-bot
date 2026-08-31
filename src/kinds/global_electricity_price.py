"""kind_generator.py が自動生成したプラグイン: global_electricity_price"""

import requests
import html
import json

KIND_NAME = "global_electricity_price"
KEYWORDS = ["電力料金", "電気代", "electricity price", "energy price", "電力", "kWh", "光熱費", "エネルギー価格"]
CATEGORY = "国・地域・雑学"

# 表示対象の国コードと日本語名
TARGET_COUNTRIES = [
    ("JPN", "日本"),
    ("USA", "アメリカ"),
    ("DEU", "ドイツ"),
    ("FRA", "フランス"),
    ("GBR", "イギリス"),
    ("CHN", "中国"),
    ("KOR", "韓国"),
    ("AUS", "オーストラリア"),
    ("CAN", "カナダ"),
    ("IND", "インド"),
    ("BRA", "ブラジル"),
    ("ZAF", "南アフリカ"),
    ("NOR", "ノルウェー"),
    ("SWE", "スウェーデン"),
    ("SAU", "サウジアラビア"),
]


def _fetch_wb_indicator(indicator: str, countries_str: str) -> dict:
    """World Bank API から指定インジケータの最新値を国コード -> (value, year) で返す。"""
    url = (
        f"https://api.worldbank.org/v2/country/{countries_str}/indicator/{indicator}"
        f"?format=json&mrv=5&per_page=500"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, list) or len(payload) < 2:
        return {}
    records = payload[1] or []
    result = {}
    for rec in records:
        code = rec.get("countryiso3code") or ""
        if not code:
            continue
        val = rec.get("value")
        year = rec.get("date", "")
        if val is not None and code not in result:
            result[code] = (float(val), str(year))
    return result


def fetch(niche: str) -> tuple:
    countries_str = ";".join(c for c, _ in TARGET_COUNTRIES)

    # 一人当たり電力消費量 (kWh/year)
    consumption = _fetch_wb_indicator("EG.USE.ELEC.KH.PC", countries_str)
    # 電力アクセス率 (%)
    access = _fetch_wb_indicator("EG.ELC.ACCS.ZS", countries_str)

    if not consumption and not access:
        raise RuntimeError("World Bank API からデータを取得できませんでした")

    rows = []
    for code, ja_name in TARGET_COUNTRIES:
        cons_val, cons_year = consumption.get(code, (None, "-"))
        acc_val, acc_year = access.get(code, (None, "-"))
        rows.append({
            "code": code,
            "name": ja_name,
            "consumption_kwh": cons_val,
            "consumption_year": cons_year,
            "access_pct": acc_val,
            "access_year": acc_year,
        })

    # サマリー: 消費量最大・最小
    valid_cons = [(r["name"], r["consumption_kwh"]) for r in rows if r["consumption_kwh"] is not None]
    if valid_cons:
        top = max(valid_cons, key=lambda x: x[1])
        bot = min(valid_cons, key=lambda x: x[1])
        summary = (
            f"{niche}のデータを取得しました。"
            f"一人当たり年間電力消費量は {top[0]} が最大({top[1]:,.0f} kWh)、"
            f"{bot[0]} が最小({bot[1]:,.0f} kWh)です。"
        )
    else:
        summary = f"{niche}のデータを取得しました。電力アクセス率データを含みます。"

    sources = [
        "https://api.worldbank.org/v2/ (World Bank Open Data - Electric power consumption & Access to electricity)"
    ]
    raw = {
        "rows": rows,
        "indicator_consumption": "EG.USE.ELEC.KH.PC",
        "indicator_access": "EG.ELC.ACCS.ZS",
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    rows = raw_data.get("rows", [])

    # 消費量でソート（降順）
    sorted_rows = sorted(
        rows,
        key=lambda r: r["consumption_kwh"] if r["consumption_kwh"] is not None else -1,
        reverse=True,
    )

    table_rows = ""
    for i, r in enumerate(sorted_rows, 1):
        name = html.escape(str(r["name"]))
        code = html.escape(str(r["code"]))

        # 消費量
        if r["consumption_kwh"] is not None:
            cons_str = f"{r['consumption_kwh']:,.0f}"
            cons_year = html.escape(str(r["consumption_year"]))
        else:
            cons_str = "-"
            cons_year = "-"

        # アクセス率
        if r["access_pct"] is not None:
            acc_str = f"{r['access_pct']:.1f}"
            acc_year = html.escape(str(r["access_year"]))
        else:
            acc_str = "-"
            acc_year = "-"

        # 消費量に応じたバーグラフ
        max_kwh = 20000.0
        if r["consumption_kwh"] is not None:
            bar_pct = min(100, int(r["consumption_kwh"] / max_kwh * 100))
            bar_html = (
                f'<div style="background:#4a9eff;height:10px;width:{bar_pct}%;'
                f'border-radius:3px;min-width:2px;"></div>'
            )
        else:
            bar_html = '<div style="color:#888;">-</div>'

        table_rows += (
            f'<tr>'
            f'<td class="tel-value" style="text-align:center;">{i}</td>'
            f'<td><strong>{name}</strong> <span style="color:#888;font-size:0.85em;">({code})</span></td>'
            f'<td class="tel-value" style="text-align:right;">{html.escape(cons_str)}</td>'
            f'<td style="padding-left:8px;min-width:120px;">{bar_html}</td>'
            f'<td style="text-align:center;color:#888;font-size:0.85em;">{cons_year}</td>'
            f'<td class="tel-value" style="text-align:right;">{html.escape(acc_str)}</td>'
            f'<td style="text-align:center;color:#888;font-size:0.85em;">{acc_year}</td>'
            f'</tr>'
        )

    source_links = ""
    for s in sources:
        parts = s.split(" (", 1)
        url = parts[0].strip()
        label = parts[1].rstrip(")").strip() if len(parts) > 1 else url
        safe_url = html.escape(url) if url.startswith("https://") else "#"
        safe_label = html.escape(label)
        source_links += f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_label}</a> '

    safe_niche = html.escape(str(niche))

    return (
        f'<h1>⚡ {safe_niche}</h1>'
        '<p>'
        'World Bank Open Data が公開する最新統計をもとに、'
        '主要国の<strong>一人当たり年間電力消費量 (kWh)</strong>と'
        '<strong>電力アクセス率 (%)</strong>を一覧表示します。'
        'データは World Bank API からリアルタイムに取得した最新年値です。'
        '</p>'
        '<div style="overflow-x:auto;">'
        '<table>'
        '<thead><tr>'
        '<th>順位</th>'
        '<th>国</th>'
        '<th>年間消費量<br>(kWh/人)</th>'
        '<th>消費量グラフ</th>'
        '<th>年</th>'
        '<th>電力<br>アクセス率(%)</th>'
        '<th>年</th>'
        '</tr></thead>'
        f'<tbody>{table_rows}</tbody>'
        '</table>'
        '</div>'
        '<p style="margin-top:12px;font-size:0.9em;color:#aaa;">'
        '※ 一人当たり年間電力消費量の最大値は約20,000 kWhをグラフ上限としています。'
        '数値は World Bank が報告する最新利用可能年のものです。'
        '</p>'
        f'<div class="source">データ出典: {source_links}</div>'
    )

