"""kind_generator.py が自動生成したプラグイン: policy_rate"""

import requests
import html
import datetime

KIND_NAME = "policy_rate"
KEYWORDS = ["政策金利", "中央銀行", "金利", "FRB", "ECB", "日銀", "BOJ", "金融政策", "policy rate", "interest rate"]
CATEGORY = "金融"

# 主要国の政策金利ベースデータ(静的フォールバック兼補足情報)
_STATIC_RATES = [
    {"country": "アメリカ", "bank": "FRB(連邦準備制度)", "code": "US", "rate": 4.25, "unit": "%", "updated": "2025-01"},
    {"country": "ユーロ圏", "bank": "ECB(欧州中央銀行)", "code": "EU", "rate": 3.15, "unit": "%", "updated": "2025-01"},
    {"country": "日本", "bank": "日本銀行(BOJ)", "code": "JP", "rate": 0.50, "unit": "%", "updated": "2025-01"},
    {"country": "イギリス", "bank": "イングランド銀行(BOE)", "code": "GB", "rate": 4.75, "unit": "%", "updated": "2025-01"},
    {"country": "カナダ", "bank": "カナダ銀行(BOC)", "code": "CA", "rate": 3.25, "unit": "%", "updated": "2025-01"},
    {"country": "オーストラリア", "bank": "豪州準備銀行(RBA)", "code": "AU", "rate": 4.35, "unit": "%", "updated": "2025-01"},
    {"country": "スイス", "bank": "スイス国立銀行(SNB)", "code": "CH", "rate": 0.50, "unit": "%", "updated": "2025-01"},
    {"country": "中国", "bank": "中国人民銀行(PBOC)", "code": "CN", "rate": 3.10, "unit": "%", "updated": "2025-01"},
    {"country": "韓国", "bank": "韓国銀行(BOK)", "code": "KR", "rate": 3.00, "unit": "%", "updated": "2025-01"},
    {"country": "インド", "bank": "インド準備銀行(RBI)", "code": "IN", "rate": 6.50, "unit": "%", "updated": "2025-01"},
    {"country": "ブラジル", "bank": "ブラジル中央銀行(BCB)", "code": "BR", "rate": 13.75, "unit": "%", "updated": "2025-01"},
    {"country": "メキシコ", "bank": "メキシコ銀行(Banxico)", "code": "MX", "rate": 10.00, "unit": "%", "updated": "2025-01"},
    {"country": "ノルウェー", "bank": "ノルウェー銀行(Norges Bank)", "code": "NO", "rate": 4.50, "unit": "%", "updated": "2025-01"},
    {"country": "スウェーデン", "bank": "スウェーデン国立銀行(Riksbank)", "code": "SE", "rate": 2.75, "unit": "%", "updated": "2025-01"},
    {"country": "ニュージーランド", "bank": "NZ準備銀行(RBNZ)", "code": "NZ", "rate": 4.25, "unit": "%", "updated": "2025-01"},
    {"country": "南アフリカ", "bank": "南アフリカ準備銀行(SARB)", "code": "ZA", "rate": 8.00, "unit": "%", "updated": "2025-01"},
    {"country": "トルコ", "bank": "トルコ中央銀行(TCMB)", "code": "TR", "rate": 47.50, "unit": "%", "updated": "2025-01"},
]

# WorldBank APIで取得を試みる国コードと指標
_WB_INDICATOR = "FR.INR.DPST"  # Deposit interest rate (中銀レートの近似)
_WB_COUNTRIES = ["US", "JP", "GB", "CA", "AU", "CH", "CN", "KR", "IN", "BR", "MX", "NO", "SE", "NZ", "ZA", "TR"]


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    wb_data = {}
    wb_ok = False
    wb_year = None

    # WorldBank APIから預金金利データを取得(政策金利の近似値として)
    try:
        country_str = ";".join(_WB_COUNTRIES)
        url = (
            f"https://api.worldbank.org/v2/country/{country_str}/indicator/{_WB_INDICATOR}"
            f"?format=json&mrv=1&per_page=50"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        # WorldBank APIはリスト[metadata, data]の形式
        if isinstance(payload, list) and len(payload) >= 2 and payload[1]:
            for entry in payload[1]:
                code = entry.get("countryiso3166alpha2") or (
                    entry.get("country", {}).get("id", "") if isinstance(entry.get("country"), dict) else ""
                )
                value = entry.get("value")
                year = entry.get("date", "")
                if code and value is not None:
                    wb_data[code] = {"value": float(value), "year": year}
                    wb_ok = True
                    if wb_year is None:
                        wb_year = year
    except Exception:
        pass  # WorldBank失敗時は静的データのみで継続

    # 静的データをベースに、WBデータで補完
    rates = []
    for item in _STATIC_RATES:
        code = item["code"]
        entry = dict(item)
        if code in wb_data:
            entry["wb_rate"] = round(wb_data[code]["value"], 2)
            entry["wb_year"] = wb_data[code]["year"]
        else:
            entry["wb_rate"] = None
            entry["wb_year"] = None
        rates.append(entry)

    if not rates:
        raise RuntimeError("政策金利データの取得に失敗しました")

    # サマリ生成
    today = datetime.date.today().isoformat()
    us_rate = next((r["rate"] for r in rates if r["code"] == "US"), "N/A")
    jp_rate = next((r["rate"] for r in rates if r["code"] == "JP"), "N/A")
    source_note = "WorldBank API補完あり" if wb_ok else "静的データ(2025年1月時点)"
    summary = (
        f"主要{len(rates)}か国の政策金利一覧({today}時点)。"
        f"米国FRB: {us_rate}%、日本銀行: {jp_rate}%。"
        f"データソース: {source_note}。"
    )

    sources = [
        "https://api.worldbank.org/v2/ (World Bank Open Data)",
        "https://www.worldbank.org/ (World Bank)",
    ]

    raw = {
        "rates": rates,
        "wb_ok": wb_ok,
        "wb_year": wb_year,
        "fetched_at": today,
        "count": len(rates),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    rates = raw_data.get("rates", [])
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    wb_ok = raw_data.get("wb_ok", False)
    wb_year = raw_data.get("wb_year", "")
    count = raw_data.get("count", len(rates))

    safe_niche = html.escape(str(niche))

    # データソース注記
    if wb_ok and wb_year:
        data_note = html.escape(f"政策金利は2025年1月時点の公表値。World Bank APIの預金金利({wb_year}年)も参考併記。")
    else:
        data_note = html.escape("政策金利は2025年1月時点の各中央銀行公表値に基づく静的データです。")

    # テーブル行を構築
    rows = []
    for item in rates:
        country = html.escape(str(item.get("country", "")))
        bank = html.escape(str(item.get("bank", "")))
        rate = item.get("rate")
        wb_rate = item.get("wb_rate")
        updated = html.escape(str(item.get("updated", "")))

        # 金利の高低に応じたクラス
        if rate is not None:
            if rate >= 10:
                rate_class = "rate-high"
            elif rate >= 3:
                rate_class = "rate-mid"
            else:
                rate_class = "rate-low"
            rate_str = html.escape(f"{rate:.2f}%")
        else:
            rate_class = ""
            rate_str = "-"

        # WB参考値
        if wb_rate is not None:
            wb_str = html.escape(f"{wb_rate:.2f}%")
        else:
            wb_str = "<span style=\"color:#999\">-</span>"

        rows.append(
            f"<tr>"
            f"<td><strong>{country}</strong></td>"
            f"<td style=\"font-size:0.9em;color:#555\">{bank}</td>"
            f"<td class=\"{rate_class}\" style=\"text-align:right;font-weight:bold;font-size:1.1em\">{rate_str}</td>"
            f"<td style=\"text-align:right;font-size:0.9em;color:#666\">{wb_str}</td>"
            f"<td style=\"text-align:center;font-size:0.85em;color:#888\">{updated}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(rows)

    # 出典リンク
    source_links = []
    for s in sources:
        if "http" in s:
            parts = s.split(" ", 1)
            url_part = parts[0] if parts else ""
            label_part = parts[1].strip("()") if len(parts) > 1 else url_part
            safe_url = html.escape(url_part) if url_part.startswith("https://") else ""
            safe_label = html.escape(label_part)
            if safe_url:
                source_links.append(f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_label}</a>')
            else:
                source_links.append(safe_label)
    sources_html = " / ".join(source_links) if source_links else ""

    return (
        f'<h1>🏦 {safe_niche}</h1>'
        f'<p>FRB・ECB・日銀など主要{html.escape(str(count))}か国・地域の中央銀行政策金利をまとめました。'
        f'金融政策の国際比較にご活用ください。</p>'
        f'<p style="font-size:0.85em;color:#666;">📅 表示日: {fetched_at}　|　{data_note}</p>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead>'
        '<tr style="background:#1a237e;color:#fff;">'
        '<th style="padding:10px 8px;text-align:left;">国・地域</th>'
        '<th style="padding:10px 8px;text-align:left;">中央銀行</th>'
        '<th style="padding:10px 8px;text-align:right;">政策金利</th>'
        '<th style="padding:10px 8px;text-align:right;">参考:預金金利(WB)</th>'
        '<th style="padding:10px 8px;text-align:center;">更新</th>'
        '</tr>'
        '</thead>'
        f'<tbody>\n{rows_html}\n</tbody>'
        '</table>'
        '</div>'
        '<div style="margin-top:16px;padding:12px;background:#fff8e1;border-left:4px solid #ffc107;border-radius:4px;">'
        '<p style="margin:0;font-size:0.9em;">'
        '<strong>⚠️ ご注意:</strong> 政策金利は随時変更されます。最新情報は各中央銀行の公式サイトでご確認ください。'
        'World Bank参考値は統計上の預金金利であり、政策金利と異なる場合があります。'
        '</p>'
        '</div>'
        '<div style="margin-top:12px;padding:8px;background:#e8f5e9;border-radius:4px;">'
        '<p style="margin:0;font-size:0.85em;">'
        '<strong>💡 高金利国:</strong> トルコ・ブラジルなど新興国は高インフレ対策で高金利。'
        '<strong>低金利国:</strong> 日本・スイスはデフレ対策・景気刺激で低金利政策を維持。'
        '</p>'
        '</div>'
        f'<div class="source">データ出典: {sources_html}　|　政策金利は2025年1月時点の各中央銀行公表値</div>'
    )

