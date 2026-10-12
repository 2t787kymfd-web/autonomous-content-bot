"""kind_generator.py が自動生成したプラグイン: fuel_price"""

import requests
import html
import json
from datetime import datetime

KIND_NAME = "fuel_price"
KEYWORDS = ["ガソリン", "燃料", "軽油", "灯油", "燃費", "fuel", "gasoline", "petrol", "price"]
CATEGORY = "生活計算"


def fetch(niche: str) -> tuple:
    """WTI原油先物価格(USD)とUSD/JPY為替レートを取得し、燃費計算用データを返す。"""
    # WTI原油先物価格をYahoo Finance非公式APIから取得
    wti_price_usd = None
    wti_symbol = "CL=F"
    try:
        url_wti = f"https://query1.finance.yahoo.com/v8/finance/chart/{wti_symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp_wti = requests.get(url_wti, headers=headers, timeout=10)
        resp_wti.raise_for_status()
        data_wti = resp_wti.json()
        meta = data_wti["chart"]["result"][0]["meta"]
        wti_price_usd = meta.get("regularMarketPrice") or meta.get("previousClose")
    except Exception:
        wti_price_usd = None

    # Brent原油先物価格も試みる
    brent_price_usd = None
    brent_symbol = "BZ=F"
    try:
        url_brent = f"https://query1.finance.yahoo.com/v8/finance/chart/{brent_symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp_brent = requests.get(url_brent, headers=headers, timeout=10)
        resp_brent.raise_for_status()
        data_brent = resp_brent.json()
        meta_b = data_brent["chart"]["result"][0]["meta"]
        brent_price_usd = meta_b.get("regularMarketPrice") or meta_b.get("previousClose")
    except Exception:
        brent_price_usd = None

    if wti_price_usd is None and brent_price_usd is None:
        raise RuntimeError("WTI・Brent原油価格のいずれも取得できませんでした")

    # USD/JPY為替レートをopen.er-api.comから取得
    usd_jpy = None
    try:
        resp_fx = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        resp_fx.raise_for_status()
        fx_data = resp_fx.json()
        usd_jpy = fx_data["rates"].get("JPY")
    except Exception:
        usd_jpy = None

    # フォールバック: Frankfurter APIでUSD/JPY取得
    if usd_jpy is None:
        try:
            resp_fx2 = requests.get("https://api.frankfurter.app/latest?from=USD&to=JPY", timeout=10)
            resp_fx2.raise_for_status()
            fx_data2 = resp_fx2.json()
            usd_jpy = fx_data2["rates"].get("JPY")
        except Exception:
            usd_jpy = None

    if usd_jpy is None:
        usd_jpy = 150.0  # 最終フォールバック(為替が取れない場合のみ)
        fx_fallback = True
    else:
        fx_fallback = False

    # 日本のガソリン価格の目安を原油価格から概算
    # 日本のレギュラーガソリン価格 ≒ 原油価格(円/バレル) / 159(リットル換算) × 精製マージン係数
    # 実際の日本の小売価格は政府補助金・税金等で変動するため、ここでは原油ベースの参考値として表示
    wti = wti_price_usd if wti_price_usd is not None else 0
    brent = brent_price_usd if brent_price_usd is not None else 0

    # 参考: 原油1バレル=約159リットル、日本のガソリン税等で+90円/L程度
    # ここではあくまで「原油コスト換算」の参考値
    wti_jpy_per_liter = round((wti * usd_jpy) / 159, 1) if wti > 0 else None
    brent_jpy_per_liter = round((brent * usd_jpy) / 159, 1) if brent > 0 else None

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    summary_parts = []
    if wti_price_usd:
        summary_parts.append(f"WTI原油: {wti_price_usd:.2f} USD/バレル")
    if brent_price_usd:
        summary_parts.append(f"Brent原油: {brent_price_usd:.2f} USD/バレル")
    summary_parts.append(f"USD/JPY: {usd_jpy:.2f}")
    summary = "、".join(summary_parts) + f" ({now_str}取得)"

    sources = [
        "https://finance.yahoo.com/ (Yahoo Finance - WTI/Brent原油先物)",
        "https://open.er-api.com/ (Open Exchange Rates - USD/JPY)",
    ]

    raw = {
        "wti_price_usd": wti_price_usd,
        "brent_price_usd": brent_price_usd,
        "usd_jpy": usd_jpy,
        "fx_fallback": fx_fallback,
        "wti_jpy_per_liter": wti_jpy_per_liter,
        "brent_jpy_per_liter": brent_jpy_per_liter,
        "fetched_at": now_str,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    wti_usd = raw_data.get("wti_price_usd")
    brent_usd = raw_data.get("brent_price_usd")
    usd_jpy = raw_data.get("usd_jpy", 150.0)
    wti_jpy_l = raw_data.get("wti_jpy_per_liter")
    brent_jpy_l = raw_data.get("brent_jpy_per_liter")
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    fx_fallback = raw_data.get("fx_fallback", False)

    def fmt_usd(v):
        if v is None:
            return '<td class="tel-value">-</td>'
        return f'<td class="tel-value">{html.escape(f"{v:.2f}")} USD</td>'

    def fmt_jpy_l(v):
        if v is None:
            return '<td class="tel-value">-</td>'
        return f'<td class="tel-value">{html.escape(str(v))} 円/L</td>'

    fx_note = ""
    if fx_fallback:
        fx_note = '<p style="color:orange">⚠ 為替レートの取得に失敗したため、参考値(150円/USD)を使用しています。</p>'

    oil_rows = ""
    if wti_usd is not None:
        oil_rows += (
            f'<tr><td>WTI原油先物</td>'
            f'{fmt_usd(wti_usd)}'
            f'<td class="tel-value">{html.escape(f"{wti_usd * usd_jpy:,.0f}")} 円/バレル</td>'
            f'{fmt_jpy_l(wti_jpy_l)}'
            f'</tr>'
        )
    if brent_usd is not None:
        oil_rows += (
            f'<tr><td>Brent原油先物</td>'
            f'{fmt_usd(brent_usd)}'
            f'<td class="tel-value">{html.escape(f"{brent_usd * usd_jpy:,.0f}")} 円/バレル</td>'
            f'{fmt_jpy_l(brent_jpy_l)}'
            f'</tr>'
        )

    source_links = ""
    for s in sources:
        safe_s = html.escape(s)
        # URLとラベルを分離
        parts = s.split(" (", 1)
        url_part = parts[0].strip()
        label_part = parts[1].rstrip(")") if len(parts) > 1 else url_part
        if url_part.startswith("https://"):
            source_links += f'<a href="{html.escape(url_part)}" target="_blank" rel="noopener">{html.escape(label_part)}</a> '
        else:
            source_links += f'{html.escape(label_part)} '

    return (
        f'<h1>⛽ {html.escape(niche)}</h1>'
        '<p>国際原油先物価格（WTI・Brent）のリアルタイム取得値と、USD/JPY為替レートを使った燃費コスト計算ツールです。'
        '原油コスト換算値は税金・精製コスト・流通コストを含まない参考値です。</p>'
        f'{fx_note}'
        '<h2>📊 国際原油価格（リアルタイム）</h2>'
        '<div class="table-wrapper">'
        '<table>'
        '<thead><tr><th>銘柄</th><th>USD/バレル</th><th>円/バレル</th><th>原油コスト換算 (円/L)</th></tr></thead>'
        f'<tbody>{oil_rows}</tbody>'
        '</table>'
        '</div>'
        f'<p><small>USD/JPY: <span class="tel-value">{html.escape(f"{usd_jpy:.2f}")}</span> 円　取得時刻: {fetched_at}</small></p>'
        '<h2>🚗 燃費コスト計算ツール</h2>'
        '<p>走行距離・燃費・ガソリン価格を入力して、燃料費を自動計算します。</p>'
        '<div class="card" style="max-width:480px">'
        '<table>'
        '<tr><th>走行距離 (km)</th><td><input type="number" id="fc_distance" value="100" min="1" max="100000" style="width:120px"> km</td></tr>'
        '<tr><th>燃費</th><td><input type="number" id="fc_efficiency" value="15" min="1" max="100" step="0.1" style="width:120px"> km/L</td></tr>'
        '<tr><th>ガソリン単価</th><td><input type="number" id="fc_unit_price" value="170" min="50" max="500" style="width:120px"> 円/L</td></tr>'
        '</table>'
        '<button onclick="calcFuel()" style="margin-top:12px;padding:8px 24px">計算する</button>'
        '<div id="fc_result" style="margin-top:16px;font-size:1.2em"></div>'
        '</div>'
        '<script>'
        'function calcFuel(){'
        '  var d=parseFloat(document.getElementById("fc_distance").value)||0;'
        '  var e=parseFloat(document.getElementById("fc_efficiency").value)||1;'
        '  var p=parseFloat(document.getElementById("fc_unit_price").value)||0;'
        '  if(e<=0){document.getElementById("fc_result").innerHTML="燃費を正しく入力してください";return;}'
        '  var liters=d/e;'
        '  var cost=liters*p;'
        '  document.getElementById("fc_result").innerHTML='
        '   "<table><tr><th>必要燃料量</th><td class=\'tel-value\'>"+(liters.toFixed(2))+" L</td></tr>"'
        '   +"<tr><th>燃料費合計</th><td class=\'tel-value\'>"+(cost.toFixed(0))+" 円</td></tr></table>";'
        '}'
        'calcFuel();'
        '</script>'
        '<h2>💡 燃費の目安</h2>'
        '<div class="table-wrapper">'
        '<table>'
        '<thead><tr><th>車種区分</th><th>一般的な燃費目安</th></tr></thead>'
        '<tbody>'
        '<tr><td>軽自動車</td><td class="tel-value">20〜30 km/L</td></tr>'
        '<tr><td>コンパクトカー</td><td class="tel-value">15〜22 km/L</td></tr>'
        '<tr><td>ハイブリッド車</td><td class="tel-value">20〜35 km/L</td></tr>'
        '<tr><td>SUV・ミニバン</td><td class="tel-value">10〜18 km/L</td></tr>'
        '<tr><td>大型トラック</td><td class="tel-value">3〜8 km/L</td></tr>'
        '</tbody>'
        '</table>'
        '</div>'
        '<div class="source">データ出典: '
        + source_links +
        '</div>'
    )

