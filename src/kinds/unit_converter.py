"""kind_generator.py が自動生成したプラグイン: unit_converter"""

import requests

import html
import json
from datetime import datetime

KIND_NAME = "unit_converter"
KEYWORDS = ["単位換算", "単位変換", "長さ", "重さ", "温度", "面積", "体積", "速度", "unit", "converter", "変換"]
CATEGORY = "生活計算"

# 単位換算テーブル定義
_UNIT_TABLE = {
    "長さ": {
        "単位": ["メートル (m)", "キロメートル (km)", "センチメートル (cm)", "ミリメートル (mm)", "マイル (mi)", "ヤード (yd)", "フィート (ft)", "インチ (in)", "海里 (nmi)"],
        "to_base": [1, 1000, 0.01, 0.001, 1609.344, 0.9144, 0.3048, 0.0254, 1852],
        "base": "メートル"
    },
    "重さ": {
        "単位": ["キログラム (kg)", "グラム (g)", "ミリグラム (mg)", "トン (t)", "ポンド (lb)", "オンス (oz)", "カラット (ct)"],
        "to_base": [1, 0.001, 0.000001, 1000, 0.45359237, 0.028349523125, 0.0002],
        "base": "キログラム"
    },
    "温度": {
        "単位": ["摂氏 (℃)", "華氏 (℉)", "ケルビン (K)"],
        "to_base": None,
        "base": "摂氏"
    },
    "面積": {
        "単位": ["平方メートル (m²)", "平方キロメートル (km²)", "平方センチメートル (cm²)", "平方ミリメートル (mm²)", "ヘクタール (ha)", "アール (a)", "平方フィート (ft²)", "平方インチ (in²)", "平方マイル (mi²)", "エーカー (ac)", "坪"],
        "to_base": [1, 1e6, 0.0001, 0.000001, 10000, 100, 0.09290304, 0.00064516, 2589988.110336, 4046.8564224, 3.305785],
        "base": "平方メートル"
    },
    "体積": {
        "単位": ["リットル (L)", "ミリリットル (mL)", "立方メートル (m³)", "立方センチメートル (cm³)", "ガロン(米) (gal)", "クォート(米) (qt)", "パイント(米) (pt)", "カップ(米) (cup)", "液量オンス(米) (fl oz)"],
        "to_base": [1, 0.001, 1000, 0.001, 3.785411784, 0.946352946, 0.473176473, 0.2365882365, 0.0295735295625],
        "base": "リットル"
    },
    "速度": {
        "単位": ["メートル毎秒 (m/s)", "キロメートル毎時 (km/h)", "マイル毎時 (mph)", "ノット (kn)", "フィート毎秒 (ft/s)"],
        "to_base": [1, 0.27777778, 0.44704, 0.51444444, 0.3048],
        "base": "メートル毎秒"
    }
}


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    このkindは外部APIを使わず単位換算テーブルをそのままraw_dataとして返す。"""
    categories = list(_UNIT_TABLE.keys())
    if not categories:
        raise RuntimeError("単位換算テーブルの読み込みに失敗しました")

    total_units = sum(len(v["単位"]) for v in _UNIT_TABLE.values())
    summary = (
        f"単位換算ツール: {len(categories)}カテゴリ ({', '.join(categories)}) 合計{total_units}単位に対応。"
        f"クライアントサイドJavaScriptによるリアルタイム換算。取得日時: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
    )
    sources = ["単位換算テーブル (内部定義・国際単位系 SI準拠)"]
    raw = {
        "categories": categories,
        "total_units": total_units,
        "table": _UNIT_TABLE,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    safe_niche = html.escape(str(niche))
    generated_at = html.escape(str(raw_data.get("generated_at", "")))
    table = raw_data.get("table", _UNIT_TABLE)

    # カテゴリ選択ボタン
    cat_buttons = ""
    for cat in table.keys():
        safe_cat = html.escape(str(cat))
        cat_buttons += f'<button class="uc-cat-btn" onclick="ucSelectCat(\'{safe_cat}\')">{safe_cat}</button>\n'

    # カテゴリごとの単位リスト (JSON埋め込み)
    # 温度は特殊処理フラグ付き
    cat_data_obj = {}
    for cat, info in table.items():
        cat_data_obj[cat] = {
            "units": info["単位"],
            "to_base": info["to_base"],
            "base": info["base"],
            "is_temp": (cat == "温度")
        }
    cat_data_json = json.dumps(cat_data_obj, ensure_ascii=False)

    # 出典
    source_items = "".join(
        f"<li>{html.escape(str(s))}</li>" for s in sources
    )

    html_out = f"""
<h1>📐 {safe_niche}</h1>
<p>長さ・重さ・温度・面積・体積・速度など{html.escape(str(len(table)))}カテゴリの単位をリアルタイムで換算します。
値を入力するだけで自動的に全単位の換算結果を表示します。</p>

<div class="uc-wrap">
  <div class="uc-cat-row">
    {cat_buttons}
  </div>

  <div class="uc-main">
    <div class="uc-input-row">
      <label for="uc-value">換算する値:</label>
      <input type="number" id="uc-value" value="1" step="any"
             oninput="ucConvert()" style="width:160px;font-size:1.1em;padding:4px 8px;">
      <select id="uc-from-unit" onchange="ucConvert()"
              style="font-size:1.05em;padding:4px 8px;"></select>
    </div>

    <table id="uc-result-table">
      <thead><tr><th>単位</th><th>換算結果</th></tr></thead>
      <tbody id="uc-result-body"></tbody>
    </table>
  </div>
</div>

<p class="uc-note">※ 換算はすべてブラウザ内で行われます。通信は発生しません。</p>
<p style="font-size:0.85em;color:#888;">最終更新: {generated_at}</p>

<div class="source">データ出典:<ul>{source_items}</ul></div>

<script>
(function(){{
  var CAT_DATA = {cat_data_json};
  var currentCat = Object.keys(CAT_DATA)[0];

  function getEl(id){{ return document.getElementById(id); }}

  window.ucSelectCat = function(cat) {{
    currentCat = cat;
    // ボタン強調
    document.querySelectorAll('.uc-cat-btn').forEach(function(b){{
      b.classList.toggle('active', b.textContent === cat);
    }});
    // fromUnitセレクト更新
    var sel = getEl('uc-from-unit');
    sel.innerHTML = '';
    var units = CAT_DATA[cat].units;
    units.forEach(function(u, i){{
      var opt = document.createElement('option');
      opt.value = i;
      opt.textContent = u;
      sel.appendChild(opt);
    }});
    ucConvert();
  }};

  window.ucConvert = function() {{
    var val = parseFloat(getEl('uc-value').value);
    if (isNaN(val)) {{ getEl('uc-result-body').innerHTML = '<tr><td colspan="2">有効な数値を入力してください</td></tr>'; return; }}
    var cat = CAT_DATA[currentCat];
    var fromIdx = parseInt(getEl('uc-from-unit').value);
    var tbody = getEl('uc-result-body');
    tbody.innerHTML = '';
    if (cat.is_temp) {{
      // 温度特殊換算
      var results = convertTemp(val, fromIdx, cat.units);
      cat.units.forEach(function(u, i){{
        var tr = document.createElement('tr');
        if (i === fromIdx) tr.classList.add('uc-from-row');
        tr.innerHTML = '<td>' + escHtml(u) + '</td><td><strong>' + formatNum(results[i]) + '</strong></td>';
        tbody.appendChild(tr);
      }});
    }} else {{
      // 線形換算: 入力値をbase単位に変換してから各単位へ
      var baseVal = val * cat.to_base[fromIdx];
      cat.units.forEach(function(u, i){{
        var converted = baseVal / cat.to_base[i];
        var tr = document.createElement('tr');
        if (i === fromIdx) tr.classList.add('uc-from-row');
        tr.innerHTML = '<td>' + escHtml(u) + '</td><td><strong>' + formatNum(converted) + '</strong></td>';
        tbody.appendChild(tr);
      }});
    }}
  }};

  function convertTemp(val, fromIdx, units) {{
    // 0:℃, 1:℉, 2:K
    var celsius;
    if (fromIdx === 0) celsius = val;
    else if (fromIdx === 1) celsius = (val - 32) * 5 / 9;
    else celsius = val - 273.15;
    return [
      celsius,
      celsius * 9 / 5 + 32,
      celsius + 273.15
    ];
  }}

  function formatNum(n) {{
    if (!isFinite(n)) return '∞';
    var abs = Math.abs(n);
    if (abs === 0) return '0';
    if (abs >= 1e15 || (abs < 1e-6 && abs > 0)) {{
      return n.toExponential(6);
    }}
    // 有効数字9桁程度
    var str = parseFloat(n.toPrecision(9)).toString();
    return str;
  }}

  function escHtml(s) {{
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}

  // 初期化
  document.addEventListener('DOMContentLoaded', function(){{
    var firstCat = Object.keys(CAT_DATA)[0];
    ucSelectCat(firstCat);
  }});
  // DOMContentLoadedが既に発火済みの場合に備えて即時実行も
  if (document.readyState === 'complete' || document.readyState === 'interactive') {{
    var firstCat = Object.keys(CAT_DATA)[0];
    ucSelectCat(firstCat);
  }}
}})();
</script>
"""
    return html_out

