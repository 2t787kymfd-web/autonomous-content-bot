"""kind_generator.py が自動生成したプラグイン: calorie_calculator"""

import requests

import html
import json
from datetime import datetime

KIND_NAME = "calorie_calculator"
KEYWORDS = ["カロリー", "calorie", "基礎代謝", "BMR", "消費カロリー", "ダイエット", "栄養", "エネルギー", "TDEE", "ハリス・ベネディクト"]
CATEGORY = "生活計算"


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    外部APIは使用せず、カロリー計算式の定数・係数テーブルを固定データとして返す。"""
    # Mifflin-St Jeor式の係数
    formula_data = {
        "formula_name": "Mifflin-St Jeor式",
        "male": {
            "weight_coeff": 10,
            "height_coeff": 6.25,
            "age_coeff": 5,
            "constant": 5
        },
        "female": {
            "weight_coeff": 10,
            "height_coeff": 6.25,
            "age_coeff": 5,
            "constant": -161
        },
        "activity_levels": [
            {"label": "ほぼ運動なし（デスクワーク中心）", "factor": 1.2},
            {"label": "軽い運動（週1〜3日）", "factor": 1.375},
            {"label": "中程度の運動（週3〜5日）", "factor": 1.55},
            {"label": "激しい運動（週6〜7日）", "factor": 1.725},
            {"label": "非常に激しい運動（アスリート級）", "factor": 1.9}
        ],
        "goal_adjustments": [
            {"label": "減量（-500kcal/日）", "adjustment": -500},
            {"label": "緩やかな減量（-250kcal/日）", "adjustment": -250},
            {"label": "維持", "adjustment": 0},
            {"label": "緩やかな増量（+250kcal/日）", "adjustment": 250},
            {"label": "増量（+500kcal/日）", "adjustment": 500}
        ],
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d")
    }

    if not formula_data.get("activity_levels"):
        raise RuntimeError("カロリー計算式データの構築に失敗しました")

    summary = (
        f"カロリー計算機({formula_data['formula_name']})のデータを構築しました。"
        f"活動レベル{len(formula_data['activity_levels'])}段階、"
        f"目標設定{len(formula_data['goal_adjustments'])}段階に対応。"
        f"生成日: {formula_data['generated_at']}"
    )
    sources = [
        "https://pubmed.ncbi.nlm.nih.gov/2305711/ (Mifflin MD et al., 1990 - Mifflin-St Jeor式原著論文)",
        "https://www.dietitian.or.jp/ (公益社団法人日本栄養士会)"
    ]
    return summary, sources, formula_data


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    safe_niche = html.escape(str(niche))
    formula_name = html.escape(str(raw_data.get("formula_name", "Mifflin-St Jeor式")))
    generated_at = html.escape(str(raw_data.get("generated_at", "")))

    activity_levels = raw_data.get("activity_levels", [])
    activity_options = ""
    for i, level in enumerate(activity_levels):
        label = html.escape(str(level.get("label", "")))
        factor = float(level.get("factor", 1.2))
        activity_options += f'<option value="{factor}">{label}（×{factor}）</option>\n'

    goal_adjustments = raw_data.get("goal_adjustments", [])
    goal_options = ""
    for adj in goal_adjustments:
        label = html.escape(str(adj.get("label", "")))
        adjustment = int(adj.get("adjustment", 0))
        goal_options += f'<option value="{adjustment}">{label}</option>\n'

    sources_html = ""
    for src in sources:
        safe_src = html.escape(str(src))
        # URLとラベルを分離
        if src.startswith("https://"):
            parts = src.split(" ", 1)
            url_part = parts[0] if parts else ""
            label_part = parts[1] if len(parts) > 1 else url_part
            safe_url = html.escape(url_part)
            safe_label_src = html.escape(label_part)
            sources_html += f'<li><a href="{safe_url}" target="_blank" rel="noopener">{safe_label_src}</a></li>'
        else:
            sources_html += f'<li>{safe_src}</li>'

    html_content = f'''<h1>🔥 {safe_niche}</h1>
<p>{formula_name}を使って、あなたの<strong>基礎代謝量（BMR）</strong>と<strong>1日の総消費カロリー（TDEE）</strong>を計算します。
ダイエット・増量・維持など、目標に合わせた摂取カロリーの目安もわかります。</p>

<div class="calc-section">
  <h2>📋 基本情報を入力</h2>
  <table class="input-table">
    <tr>
      <th>性別</th>
      <td>
        <label><input type="radio" name="gender" value="male" checked> 男性</label>
        &nbsp;&nbsp;
        <label><input type="radio" name="gender" value="female"> 女性</label>
      </td>
    </tr>
    <tr>
      <th>年齢</th>
      <td><input type="number" id="age" value="30" min="10" max="100" style="width:80px"> 歳</td>
    </tr>
    <tr>
      <th>身長</th>
      <td><input type="number" id="height" value="170" min="100" max="250" step="0.1" style="width:80px"> cm</td>
    </tr>
    <tr>
      <th>体重</th>
      <td><input type="number" id="weight" value="65" min="30" max="300" step="0.1" style="width:80px"> kg</td>
    </tr>
    <tr>
      <th>活動レベル</th>
      <td>
        <select id="activity">
          {activity_options}
        </select>
      </td>
    </tr>
    <tr>
      <th>目標</th>
      <td>
        <select id="goal">
          {goal_options}
        </select>
      </td>
    </tr>
  </table>
  <button onclick="calculateCalorie()" style="margin-top:12px;padding:10px 28px;font-size:1.1em;background:#e74c3c;color:#fff;border:none;border-radius:6px;cursor:pointer;">🔥 計算する</button>
</div>

<div id="result-section" style="display:none;margin-top:24px;">
  <h2>📊 計算結果</h2>
  <table>
    <thead>
      <tr><th>項目</th><th>値</th><th>説明</th></tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>基礎代謝量（BMR）</strong></td>
        <td id="bmr-result" style="text-align:right;font-weight:bold;">-</td>
        <td>安静時に消費するカロリー</td>
      </tr>
      <tr>
        <td><strong>総消費カロリー（TDEE）</strong></td>
        <td id="tdee-result" style="text-align:right;font-weight:bold;">-</td>
        <td>活動レベルを含む1日の消費量</td>
      </tr>
      <tr>
        <td><strong>目標摂取カロリー</strong></td>
        <td id="target-result" style="text-align:right;font-weight:bold;color:#e74c3c;">-</td>
        <td>目標達成のための1日の摂取量</td>
      </tr>
    </tbody>
  </table>

  <h2 style="margin-top:20px;">🥗 PFCバランスの目安</h2>
  <p>目標摂取カロリーをもとに、三大栄養素の推奨量（標準的な比率）を表示します。</p>
  <table>
    <thead>
      <tr><th>栄養素</th><th>推奨量（g）</th><th>エネルギー（kcal）</th><th>比率</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>🥩 タンパク質（Protein）</td>
        <td id="protein-g" style="text-align:right;">-</td>
        <td id="protein-kcal" style="text-align:right;">-</td>
        <td>25%</td>
      </tr>
      <tr>
        <td>🥑 脂質（Fat）</td>
        <td id="fat-g" style="text-align:right;">-</td>
        <td id="fat-kcal" style="text-align:right;">-</td>
        <td>25%</td>
      </tr>
      <tr>
        <td>🍚 炭水化物（Carbohydrate）</td>
        <td id="carb-g" style="text-align:right;">-</td>
        <td id="carb-kcal" style="text-align:right;">-</td>
        <td>50%</td>
      </tr>
    </tbody>
  </table>

  <div id="advice-box" style="margin-top:16px;padding:12px 16px;background:#fef9e7;border-left:4px solid #f39c12;border-radius:4px;">
    <strong>💡 アドバイス：</strong><span id="advice-text"></span>
  </div>
</div>

<div style="margin-top:24px;padding:12px;background:#f8f9fa;border-radius:6px;">
  <h3>📐 計算式について（{formula_name}）</h3>
  <table>
    <thead><tr><th>性別</th><th>BMR計算式</th></tr></thead>
    <tbody>
      <tr>
        <td>男性</td>
        <td>BMR = (10 × 体重kg) + (6.25 × 身長cm) − (5 × 年齢) + 5</td>
      </tr>
      <tr>
        <td>女性</td>
        <td>BMR = (10 × 体重kg) + (6.25 × 身長cm) − (5 × 年齢) − 161</td>
      </tr>
    </tbody>
  </table>
  <p style="font-size:0.9em;color:#666;">TDEE = BMR × 活動係数 ／ 目標摂取カロリー = TDEE ± 目標調整値</p>
  <p style="font-size:0.85em;color:#888;">※ 本計算はあくまでも目安です。個人差があり、医療・栄養指導の代替にはなりません。</p>
</div>

<script>
function calculateCalorie() {{
  var gender = document.querySelector('input[name="gender"]:checked').value;
  var age = parseFloat(document.getElementById('age').value);
  var height = parseFloat(document.getElementById('height').value);
  var weight = parseFloat(document.getElementById('weight').value);
  var activityFactor = parseFloat(document.getElementById('activity').value);
  var goalAdj = parseFloat(document.getElementById('goal').value);

  if (isNaN(age) || isNaN(height) || isNaN(weight) || age <= 0 || height <= 0 || weight <= 0) {{
    alert('有効な数値を入力してください。');
    return;
  }}

  var bmr;
  if (gender === 'male') {{
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5;
  }} else {{
    bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161;
  }}

  var tdee = bmr * activityFactor;
  var target = tdee + goalAdj;
  if (target < 1000) target = 1000;

  document.getElementById('bmr-result').textContent = Math.round(bmr) + ' kcal';
  document.getElementById('tdee-result').textContent = Math.round(tdee) + ' kcal';
  document.getElementById('target-result').textContent = Math.round(target) + ' kcal';

  // PFCバランス（P:25%, F:25%, C:50%）
  var proteinKcal = target * 0.25;
  var fatKcal = target * 0.25;
  var carbKcal = target * 0.50;
  var proteinG = proteinKcal / 4;
  var fatG = fatKcal / 9;
  var carbG = carbKcal / 4;

  document.getElementById('protein-g').textContent = Math.round(proteinG) + ' g';
  document.getElementById('protein-kcal').textContent = Math.round(proteinKcal) + ' kcal';
  document.getElementById('fat-g').textContent = Math.round(fatG) + ' g';
  document.getElementById('fat-kcal').textContent = Math.round(fatKcal) + ' kcal';
  document.getElementById('carb-g').textContent = Math.round(carbG) + ' g';
  document.getElementById('carb-kcal').textContent = Math.round(carbKcal) + ' kcal';

  // アドバイス
  var advice = '';
  if (goalAdj < 0) {{
    advice = '摂取カロリーを抑えつつ、タンパク質をしっかり摂って筋肉量を維持しましょう。急激な制限は禁物です。';
  }} else if (goalAdj > 0) {{
    advice = '増量期は筋トレと組み合わせることで、脂肪より筋肉を増やしやすくなります。';
  }} else {{
    advice = '体重維持には、毎日の摂取カロリーと消費カロリーのバランスを意識しましょう。';
  }}
  document.getElementById('advice-text').textContent = advice;

  document.getElementById('result-section').style.display = 'block';
  document.getElementById('result-section').scrollIntoView({{behavior: 'smooth'}});
}}
</script>

<div class="source">
  <strong>データ出典・参考文献:</strong>
  <ul>
    {sources_html}
  </ul>
  <small>最終更新: {generated_at}</small>
</div>'''

    return html_content

