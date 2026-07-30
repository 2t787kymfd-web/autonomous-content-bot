"""
tool_builder.py
-----------------
「記事」ではなく、ブラウザ上で実際に入力・計算できる
インタラクティブなツールページ(HTML+JS)を組み立てる。

AIに直接HTML/JSを生成させると壊れたコードが混ざるリスクが
あるため、ここは決定的(deterministic)なPythonコードで
テンプレートに実データを埋め込む方式にしている。
AIが担当するのは「どのニッチにどのツールを割り当てるか」の
判断(main_loop側)であり、ツール自体の実装は固定テンプレート。
"""

import json
from typing import Dict


def build_fx_converter_html(niche: str, raw_data: Dict, sources: list) -> str:
    rates = raw_data["rates"]          # 例: {"USD": 155.2, "EUR": 168.0, ...}
    target = raw_data["target"]        # "JPY"
    date = raw_data["date"]
    rates_json = json.dumps(rates, ensure_ascii=False)
    source_line = " / ".join(sources)

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{niche}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }}
  h1 {{ font-size: 1.3rem; }}
  .row {{ margin: 12px 0; }}
  input, select {{ font-size: 1rem; padding: 6px; }}
  .result {{ font-size: 1.4rem; font-weight: bold; margin-top: 16px; }}
  .source {{ font-size: 0.8rem; color: #666; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>{niche}</h1>
  <p>基準日: {date} のレートを使った換算ツールです。</p>

  <div class="row">
    <input id="amount" type="number" value="1" step="any">
    <select id="currency"></select>
    <span>→ {target}</span>
  </div>

  <div class="result" id="result"></div>
  <div class="source">データ出典: {source_line}(基準日 {date} 時点)</div>

<script>
  const rates = {rates_json};
  const target = "{target}";

  const select = document.getElementById("currency");
  Object.keys(rates).forEach(code => {{
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = code;
    select.appendChild(opt);
  }});

  function update() {{
    const amount = parseFloat(document.getElementById("amount").value) || 0;
    const code = select.value;
    const rate = rates[code];
    const converted = (amount * rate).toLocaleString(undefined, {{maximumFractionDigits: 2}});
    document.getElementById("result").textContent = `${{amount}} ${{code}} = ${{converted}} ${{target}}`;
  }}

  document.getElementById("amount").addEventListener("input", update);
  select.addEventListener("change", update);
  update();
</script>
</body>
</html>
"""


def build_crypto_dashboard_html(niche: str, raw_data: Dict, sources: list) -> str:
    prices = raw_data["prices"]        # 例: {"bitcoin": {"jpy": ..., "usd": ...}, ...}
    fetched_at = raw_data["fetched_at"]
    prices_json = json.dumps(prices, ensure_ascii=False)
    source_line = " / ".join(sources)

    rows = "\n".join(
        f'<option value="{coin_id}">{coin_id}</option>' for coin_id in prices.keys()
    )

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{niche}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }}
  h1 {{ font-size: 1.3rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  td, th {{ border-bottom: 1px solid #ddd; padding: 6px; text-align: right; }}
  th:first-child, td:first-child {{ text-align: left; }}
  .row {{ margin: 20px 0 8px; }}
  .result {{ font-size: 1.2rem; font-weight: bold; }}
  .source {{ font-size: 0.8rem; color: #666; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>{niche}</h1>
  <p>取得時刻: {fetched_at}(UTC)のスナップショットです。</p>

  <table id="price-table"></table>

  <div class="row">
    <input id="amount" type="number" value="1" step="any">
    <select id="coin">{rows}</select>
    <span>の現在価値:</span>
    <div class="result" id="result"></div>
  </div>

  <div class="source">データ出典: {source_line}</div>

<script>
  const prices = {prices_json};

  const table = document.getElementById("price-table");
  let html = "<tr><th>銘柄</th><th>USD</th><th>JPY</th></tr>";
  for (const [coin, v] of Object.entries(prices)) {{
    html += `<tr><td>${{coin}}</td><td>${{v.usd ?? "-"}}</td><td>${{v.jpy ?? "-"}}</td></tr>`;
  }}
  table.innerHTML = html;

  const coinSelect = document.getElementById("coin");
  function update() {{
    const amount = parseFloat(document.getElementById("amount").value) || 0;
    const coin = coinSelect.value;
    const p = prices[coin];
    const jpy = (amount * (p.jpy ?? 0)).toLocaleString(undefined, {{maximumFractionDigits: 0}});
    const usd = (amount * (p.usd ?? 0)).toLocaleString(undefined, {{maximumFractionDigits: 2}});
    document.getElementById("result").textContent = `≈ ${{jpy}} JPY / ${{usd}} USD`;
  }}
  document.getElementById("amount").addEventListener("input", update);
  coinSelect.addEventListener("change", update);
  update();
</script>
</body>
</html>
"""


def build_tool_html(research) -> str:
    """research.kind に応じて適切なツールを組み立てる。未対応kindはNoneを返す。"""
    if research.kind == "fx":
        return build_fx_converter_html(research.niche, research.raw_data, research.sources)
    if research.kind == "crypto":
        return build_crypto_dashboard_html(research.niche, research.raw_data, research.sources)
    return None
