"""kind_generator.py が自動生成したプラグイン: bmi_calculator"""

import requests

import html
import json

KIND_NAME = "bmi_calculator"
KEYWORDS = ["BMI", "体格指数", "肥満度", "BMI計算", "body mass index", "標準体重", "肥満判定"]
CATEGORY = "生活計算"


def fetch(niche: str) -> tuple:
    """WHOのBMI区分基準を固定リファレンスデータとして返す。"""
    bmi_categories = [
        {"range": "18.5未満", "min": None, "max": 18.5, "label": "低体重（痩せ型）", "label_en": "Underweight", "color": "#3498db"},
        {"range": "18.5〜25未満", "min": 18.5, "max": 25.0, "label": "普通体重", "label_en": "Normal weight", "color": "#2ecc71"},
        {"range": "25〜30未満", "min": 25.0, "max": 30.0, "label": "前肥満（過体重）", "label_en": "Pre-obese", "color": "#f39c12"},
        {"range": "30〜35未満", "min": 30.0, "max": 35.0, "label": "肥満1度", "label_en": "Obese class I", "color": "#e67e22"},
        {"range": "35〜40未満", "min": 35.0, "max": 40.0, "label": "肥満2度", "label_en": "Obese class II", "color": "#e74c3c"},
        {"range": "40以上", "min": 40.0, "max": None, "label": "肥満3度", "label_en": "Obese class III", "color": "#c0392b"},
    ]

    raw = {
        "title": "BMI計算機（体格指数）",
        "categories": bmi_categories,
        "source_name": "WHO (World Health Organization) BMI分類基準",
        "source_url": "https://www.who.int/europe/news-room/fact-sheets/item/a-healthy-lifestyle---who-recommendations",
        "note": "日本肥満学会ではBMI 25以上を肥満と定義。WHOの基準とは一部異なります。",
    }

    summary = (
        f"WHOのBMI区分基準データを取得しました。区分数: {len(bmi_categories)}件。"
        f"低体重(BMI<18.5)、普通体重(18.5-25)、前肥満(25-30)、肥満1-3度(30以上)を含みます。"
    )
    sources = [
        "https://www.who.int/europe/news-room/fact-sheets/item/a-healthy-lifestyle---who-recommendations (WHO ヨーロッパ地域事務局)",
        "https://www.euro.who.int/en/health-topics/disease-prevention/nutrition/a-healthy-lifestyle/body-mass-index-bmi (WHO BMI分類)",
    ]

    if not bmi_categories:
        raise RuntimeError("BMIカテゴリデータの構築に失敗しました。")

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """BMI計算機のHTML断片を返す（クライアントサイドJS計算）。"""
    title = html.escape(str(raw_data.get("title", "BMI計算機")))
    note = html.escape(str(raw_data.get("note", "")))
    source_name = html.escape(str(raw_data.get("source_name", "")))
    source_url = raw_data.get("source_url", "")
    safe_source_url = source_url if source_url.startswith("https://") else "#"

    categories = raw_data.get("categories", [])

    # BMI区分テーブル行を生成
    table_rows = ""
    for cat in categories:
        safe_range = html.escape(str(cat.get("range", "")))
        safe_label = html.escape(str(cat.get("label", "")))
        safe_label_en = html.escape(str(cat.get("label_en", "")))
        color = html.escape(str(cat.get("color", "#333")))
        table_rows += (
            f'<tr>'
            f'<td style="text-align:center;" class="tel-value"><span style="display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;vertical-align:middle;margin-right:4px;"></span>{safe_range}</td>'
            f'<td style="font-weight:bold;color:{color};">{safe_label}</td>'
            f'<td style="color:#888;font-size:0.9em;">{safe_label_en}</td>'
            f'</tr>'
        )

    # カテゴリデータをJSに渡すため安全にシリアライズ
    js_categories = json.dumps(
        [{"min": c.get("min"), "max": c.get("max"), "label": c.get("label", ""), "color": c.get("color", "#333")} for c in categories],
        ensure_ascii=True
    )

    # 出典リスト
    sources_html = ""
    for s in sources:
        safe_s = html.escape(str(s))
        sources_html += f'<li>{safe_s}</li>'

    html_out = f"""
<h1>⚖️ {title}</h1>
<p>身長と体重を入力するだけで、あなたのBMI（体格指数）と肥満度判定を即座に確認できます。
BMIはWHO（世界保健機関）が定める国際標準の体格評価指標です。</p>

<div class="card" style="max-width:480px;margin:0 auto 2em auto;padding:1.5em;background:#f8f9fa;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
  <h2 style="margin-top:0;font-size:1.2em;">📐 BMIを計算する</h2>
  <div style="margin-bottom:1em;">
    <label for="bmi-height" style="display:block;margin-bottom:4px;font-weight:bold;">身長 (cm)</label>
    <input id="bmi-height" type="number" min="50" max="250" step="0.1" placeholder="例: 170" style="width:100%;padding:0.6em;font-size:1.1em;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;">
  </div>
  <div style="margin-bottom:1.2em;">
    <label for="bmi-weight" style="display:block;margin-bottom:4px;font-weight:bold;">体重 (kg)</label>
    <input id="bmi-weight" type="number" min="1" max="500" step="0.1" placeholder="例: 65" style="width:100%;padding:0.6em;font-size:1.1em;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;">
  </div>
  <button onclick="calcBmi()" style="width:100%;padding:0.75em;font-size:1.1em;font-weight:bold;background:#2ecc71;color:#fff;border:none;border-radius:6px;cursor:pointer;">計算する</button>

  <div id="bmi-result" style="display:none;margin-top:1.5em;text-align:center;">
    <div style="font-size:0.95em;color:#555;margin-bottom:4px;">あなたのBMI</div>
    <div id="bmi-value" class="tel-value" style="font-size:3em;font-weight:bold;line-height:1.1;">--</div>
    <div id="bmi-label" style="font-size:1.3em;font-weight:bold;margin:0.3em 0;">--</div>
    <div style="margin-top:1em;font-size:0.9em;color:#555;">
      <span>標準体重: <strong id="bmi-std-weight" class="tel-value">--</strong> kg</span>
      &nbsp;|&nbsp;
      <span>理想との差: <strong id="bmi-diff" class="tel-value">--</strong> kg</span>
    </div>
    <div id="bmi-bar-wrap" style="margin-top:1.2em;">
      <div style="display:flex;height:18px;border-radius:9px;overflow:hidden;">
        <div style="flex:1;background:#3498db;"></div>
        <div style="flex:2;background:#2ecc71;"></div>
        <div style="flex:2;background:#f39c12;"></div>
        <div style="flex:2;background:#e67e22;"></div>
        <div style="flex:2;background:#e74c3c;"></div>
        <div style="flex:2;background:#c0392b;"></div>
      </div>
      <div id="bmi-marker-row" style="position:relative;height:12px;">
        <div id="bmi-marker" style="position:absolute;transform:translateX(-50%);font-size:18px;top:-2px;">▲</div>
      </div>
    </div>
  </div>
  <div id="bmi-error" style="display:none;color:#e74c3c;margin-top:1em;text-align:center;font-weight:bold;"></div>
</div>

<h2>📋 WHOのBMI区分基準</h2>
<table>
  <thead>
    <tr><th>BMI範囲</th><th>判定</th><th>英語表記</th></tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>

<div class="card" style="margin-top:1.5em;padding:1em 1.2em;background:#fff8e1;border-left:4px solid #f39c12;border-radius:6px;">
  <strong>⚠️ 注意:</strong> {note}
</div>

<h2 style="margin-top:2em;">💡 BMIとは？</h2>
<p>BMI（Body Mass Index／体格指数）は、体重(kg)を身長(m)の2乗で割った値です。</p>
<p style="text-align:center;font-size:1.15em;background:#f0f4f8;padding:0.7em;border-radius:6px;"><strong>BMI = 体重(kg) ÷ 身長(m)²</strong></p>
<p>標準体重はBMI=22を基準とし、<strong>標準体重(kg) = 身長(m)² × 22</strong> で算出されます。
BMI=22付近が統計的に最も生活習慣病リスクが低いとされています。</p>

<div class="source">データ出典: <a href="{html.escape(safe_source_url)}" target="_blank" rel="noopener">{source_name}</a>
<ul style="margin:0.5em 0 0 0;font-size:0.9em;">{sources_html}</ul>
</div>

<script>
(function() {{
  var cats = {js_categories};

  function getBmiCategory(bmi) {{
    for (var i = 0; i < cats.length; i++) {{
      var c = cats[i];
      var minOk = (c.min === null || bmi >= c.min);
      var maxOk = (c.max === null || bmi < c.max);
      if (minOk && maxOk) return c;
    }}
    return cats[cats.length - 1];
  }}

  function getBarPercent(bmi) {{
    // バーは BMI 10〜50 の範囲を100%として表示
    var lo = 10, hi = 50;
    var pct = (bmi - lo) / (hi - lo) * 100;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    return pct;
  }}

  window.calcBmi = function() {{
    var resultDiv = document.getElementById('bmi-result');
    var errorDiv = document.getElementById('bmi-error');
    resultDiv.style.display = 'none';
    errorDiv.style.display = 'none';

    var hVal = parseFloat(document.getElementById('bmi-height').value);
    var wVal = parseFloat(document.getElementById('bmi-weight').value);

    if (isNaN(hVal) || isNaN(wVal) || hVal <= 0 || wVal <= 0) {{
      errorDiv.textContent = '身長と体重を正しく入力してください。';
      errorDiv.style.display = 'block';
      return;
    }}
    if (hVal < 50 || hVal > 250) {{
      errorDiv.textContent = '身長は50〜250cmの範囲で入力してください。';
      errorDiv.style.display = 'block';
      return;
    }}
    if (wVal < 1 || wVal > 500) {{
      errorDiv.textContent = '体重は1〜500kgの範囲で入力してください。';
      errorDiv.style.display = 'block';
      return;
    }}

    var hm = hVal / 100;
    var bmi = wVal / (hm * hm);
    var bmiRounded = Math.round(bmi * 10) / 10;
    var stdWeight = Math.round(hm * hm * 22 * 10) / 10;
    var diff = Math.round((wVal - stdWeight) * 10) / 10;
    var diffStr = (diff >= 0 ? '+' : '') + diff;

    var cat = getBmiCategory(bmi);

    document.getElementById('bmi-value').textContent = bmiRounded.toFixed(1);
    document.getElementById('bmi-value').style.color = cat.color;
    document.getElementById('bmi-label').textContent = cat.label;
    document.getElementById('bmi-label').style.color = cat.color;
    document.getElementById('bmi-std-weight').textContent = stdWeight.toFixed(1);
    document.getElementById('bmi-diff').textContent = diffStr;

    var pct = getBarPercent(bmi);
    document.getElementById('bmi-marker').style.left = pct + '%';
    document.getElementById('bmi-marker').style.color = cat.color;

    resultDiv.style.display = 'block';
  }};

  // Enterキーでも計算
  document.getElementById('bmi-height').addEventListener('keydown', function(e) {{ if (e.key === 'Enter') window.calcBmi(); }});
  document.getElementById('bmi-weight').addEventListener('keydown', function(e) {{ if (e.key === 'Enter') window.calcBmi(); }});
}})();
</script>
"""
    return html_out

