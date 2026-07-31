"""kind_generator.py が自動生成したプラグイン: stock_index"""

import html
import requests
from datetime import datetime, timezone, timedelta
from typing import Any

KIND_NAME = "stock_index"
KEYWORDS = ["株価指数", "日経平均", "NYダウ", "S&P500", "NASDAQ", "終値", "株式市場", "stock index", "nikkei", "dow jones"]
CATEGORY = "金融"

_INDICES = [
    {"symbol": "^N225",  "label": "日経平均",     "region": "日本"},
    {"symbol": "^DJI",   "label": "NYダウ",       "region": "米国"},
    {"symbol": "^GSPC",  "label": "S&P 500",     "region": "米国"},
    {"symbol": "^IXIC",  "label": "NASDAQ総合",  "region": "米国"},
    {"symbol": "^FTSE",  "label": "FTSE 100",    "region": "英国"},
    {"symbol": "^GDAXI", "label": "DAX",          "region": "ドイツ"},
]

_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; autonomous-content-bot/1.0)",
    "Accept": "application/json",
}


def _fetch_index(symbol: str) -> dict[str, Any]:
    """1銘柄分のデータをYahoo Finance chart APIから取得する。"""
    url = _BASE_URL.format(symbol=symbol)
    resp = requests.get(url, headers=_HEADERS, timeout=15,
                        params={"interval": "1d", "range": "5d"})
    resp.raise_for_status()
    data = resp.json()
    result = data["chart"]["result"][0]
    meta = result["meta"]
    # regularMarketPrice が最新値。previousClose があれば前日終値も取得
    price = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    currency = meta.get("currency", "")
    exchange = meta.get("exchangeName", "")
    ts = meta.get("regularMarketTime")
    if ts:
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
        # JST(+9)で表示
        jst = timezone(timedelta(hours=9))
        dt_str = dt_utc.astimezone(jst).strftime("%Y-%m-%d %H:%M JST")
    else:
        dt_str = "不明"
    change = None
    change_pct = None
    if price is not None and prev_close and prev_close != 0:
        change = price - prev_close
        change_pct = change / prev_close * 100
    return {
        "symbol": symbol,
        "price": price,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "currency": currency,
        "exchange": exchange,
        "datetime": dt_str,
    }


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary, sources, raw_data) を返す。"""
    rows = []
    errors = []
    for idx in _INDICES:
        try:
            row = _fetch_index(idx["symbol"])
            row["label"] = idx["label"]
            row["region"] = idx["region"]
            rows.append(row)
        except Exception as e:
            errors.append(f"{idx['label']}({idx['symbol']}): {e}")

    if not rows:
        raise RuntimeError(f"全指数の取得に失敗しました: {errors}")

    # サマリーテキスト生成
    lines = []
    for r in rows:
        if r["price"] is not None:
            sign = "+" if (r["change"] or 0) >= 0 else ""
            chg_str = ""
            if r["change"] is not None:
                chg_str = f" ({sign}{r['change']:,.2f} / {sign}{r['change_pct']:.2f}%)"
            lines.append(
                f"{r['label']}: {r['price']:,.2f} {r['currency']}{chg_str} [{r['datetime']}]"
            )
    summary = "主要株価指数の最新値:\n" + "\n".join(lines)
    if errors:
        summary += "\n取得エラー: " + "; ".join(errors)

    sources = [
        "https://finance.yahoo.com/ (Yahoo Finance — 非公式APIエンドポイント、無料)"
    ]
    raw = {
        "indices": rows,
        "errors": errors,
        "fetched_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: <h1>から始まるHTML本文断片を返す。"""
    rows: list[dict] = raw_data.get("indices", [])
    errors: list[str] = raw_data.get("errors", [])
    fetched_at: str = raw_data.get("fetched_at", "")

    safe_niche = html.escape(niche)
    safe_fetched = html.escape(fetched_at)

    # テーブルヘッダー
    table_rows = ""
    for r in rows:
        label = html.escape(str(r.get("label", "")))
        region = html.escape(str(r.get("region", "")))
        symbol = html.escape(str(r.get("symbol", "")))
        currency = html.escape(str(r.get("currency", "")))
        exchange = html.escape(str(r.get("exchange", "")))
        dt_str = html.escape(str(r.get("datetime", "-")))

        price = r.get("price")
        change = r.get("change")
        change_pct = r.get("change_pct")

        if price is not None:
            price_str = f"{price:,.2f}"
        else:
            price_str = "-"

        if change is not None and change_pct is not None:
            sign = "+" if change >= 0 else ""
            color = "#d9534f" if change < 0 else "#5cb85c"
            arrow = "▲" if change >= 0 else "▼"
            change_str = (
                f'<span class="tel-value" style="color:{color};font-weight:bold;">'
                f"{arrow} {sign}{change:,.2f} ({sign}{change_pct:.2f}%)"
                f"</span>"
            )
        else:
            change_str = "-"

        yahoo_url = f"https://finance.yahoo.com/quote/{r.get('symbol', '')}"
        safe_yahoo_url = html.escape(yahoo_url)
        link = f'<a href="{safe_yahoo_url}" target="_blank" rel="noopener">{symbol}</a>'

        table_rows += (
            "<tr>"
            f"<td>{label}</td>"
            f"<td>{region}</td>"
            f"<td>{link}</td>"
            f"<td class='tel-value' style='text-align:right;font-weight:bold;'>{html.escape(price_str)} {currency}</td>"
            f"<td style='text-align:right;'>{change_str}</td>"
            f"<td class='tel-value' style='font-size:0.85em;color:#888;'>{dt_str}</td>"
            "</tr>"
        )

    error_html = ""
    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        error_html = f'<p style="color:#c0392b;"><strong>取得エラー:</strong><ul>{error_items}</ul></p>'

    source_items = "".join(
        f'<li><a href="{html.escape(s.split(" ")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a></li>'
        if s.startswith("https://") else f"<li>{html.escape(s)}</li>"
        for s in sources
    )

    return (
        f"<h1>📈 {safe_niche}</h1>"
        "<p>世界主要株価指数の最新値・前日比をまとめています。"
        "データはYahoo Finance APIより取得しています。</p>"
        f'<p class="tel-value" style="font-size:0.9em;color:#555;">更新: {safe_fetched}</p>'
        "<div style='overflow-x:auto;'>"
        "<table>"
        "<thead><tr>"
        "<th>指数名</th><th>地域</th><th>ティッカー</th>"
        "<th style='text-align:right;'>最新値</th>"
        "<th style='text-align:right;'>前日比</th>"
        "<th>時刻</th>"
        "</tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table>"
        "</div>"
        f"{error_html}"
        "<div class='source'>"
        "データ出典:<ul>"
        f"{source_items}"
        "</ul>"
        "<small>※ Yahoo Finance 非公式APIを使用。値は遅延またはリアルタイムの場合があります。投資判断にはご利用の証券会社の情報をご確認ください。</small>"
        "</div>"
    )

