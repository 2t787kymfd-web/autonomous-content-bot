"""kind_generator.py が自動生成したプラグイン: japanese_era"""

import requests

import html
from datetime import datetime

KIND_NAME = "japanese_era"
KEYWORDS = ["元号", "西暦", "和暦", "明治", "大正", "昭和", "平成", "令和", "年号変換", "japanese era", "gengou"]
CATEGORY = "暦・和文化"

# 元号テーブル: (元号名, 読み, 開始西暦年, 開始月, 開始日, 終了西暦年 or None)
ERA_TABLE = [
    ("明治", "Meiji",   1868,  1,  25, 1912),
    ("大正", "Taisho",  1912,  7,  30, 1926),
    ("昭和", "Showa",   1926, 12,  25, 1989),
    ("平成", "Heisei",  1989,  1,   8, 2019),
    ("令和", "Reiwa",   2019,  5,   1, None),
]


def _year_to_eras(western_year: int) -> list:
    """西暦年から対応する元号情報のリストを返す。"""
    results = []
    for era_name, era_roman, start_year, start_month, start_day, end_year in ERA_TABLE:
        if western_year < start_year:
            continue
        if end_year is not None and western_year > end_year:
            continue
        era_year = western_year - start_year + 1
        note = ""
        if western_year == start_year:
            note = f"（{start_month}月{start_day}日以降）"
        if end_year is not None and western_year == end_year:
            if note:
                note += "かつ改元年"
            else:
                note = "（改元年・一部期間のみ）"
        results.append({
            "era_name": era_name,
            "era_roman": era_roman,
            "era_year": era_year,
            "note": note,
            "start_year": start_year,
        })
    return results


def _era_to_western(era_name: str, era_year: int) -> int | None:
    """元号名と元号年から西暦年を返す。"""
    for name, roman, start_year, start_month, start_day, end_year in ERA_TABLE:
        if era_name in (name, roman):
            western = start_year + era_year - 1
            if end_year is not None and western > end_year:
                return None
            return western
    return None


def fetch(niche: str) -> tuple:
    """元号⇔西暦変換テーブルデータを生成して返す。外部APIは使用しない。"""
    current_year = datetime.now().year

    # 現在年と直近数年の変換例を生成
    sample_years = list(range(max(1868, current_year - 5), current_year + 6))
    conversions = []
    for y in sample_years:
        eras = _year_to_eras(y)
        for e in eras:
            conversions.append({
                "western_year": y,
                "era_name": e["era_name"],
                "era_roman": e["era_roman"],
                "era_year": e["era_year"],
                "note": e["note"],
            })

    if not conversions:
        raise RuntimeError("元号変換データの生成に失敗しました。")

    # 元号テーブル全体
    era_list = []
    for era_name, era_roman, start_year, start_month, start_day, end_year in ERA_TABLE:
        era_list.append({
            "era_name": era_name,
            "era_roman": era_roman,
            "start_year": start_year,
            "start_month": start_month,
            "start_day": start_day,
            "end_year": end_year if end_year else current_year,
            "duration": (end_year if end_year else current_year) - start_year + 1,
        })

    current_eras = _year_to_eras(current_year)
    current_era_str = "、".join(
        f"{e['era_name']}{e['era_year']}年" for e in current_eras
    ) if current_eras else "不明"

    summary = (
        f"元号⇔西暦変換ツール。現在（{current_year}年）は{current_era_str}。"
        f"明治元年（1868年）から令和現在まで{len(ERA_TABLE)}つの元号を収録。"
        f"サンプル変換{len(conversions)}件を生成しました。"
    )
    sources = [
        "内閣府「元号一覧」https://www.cao.go.jp/others/gengo/gengo.html (内閣府)"
    ]
    raw = {
        "current_year": current_year,
        "current_era_str": current_era_str,
        "era_list": era_list,
        "sample_conversions": conversions,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    current_year = int(raw_data.get("current_year", datetime.now().year))
    current_era_str = html.escape(str(raw_data.get("current_era_str", "")))
    era_list = raw_data.get("era_list", [])
    generated_at = html.escape(str(raw_data.get("generated_at", "")))

    # 元号テーブルHTML
    era_rows = ""
    for e in era_list:
        name = html.escape(str(e.get("era_name", "")))
        roman = html.escape(str(e.get("era_roman", "")))
        sy = html.escape(str(e.get("start_year", "")))
        sm = html.escape(str(e.get("start_month", "")))
        sd = html.escape(str(e.get("start_day", "")))
        ey_raw = e.get("end_year")
        is_current = (e.get("end_year") == current_year and e.get("era_name") == "令和")
        ey = "現在" if is_current else html.escape(str(ey_raw))
        dur = html.escape(str(e.get("duration", "")))
        era_rows += (
            f"<tr>"
            f"<td><strong>{name}</strong><br><small>{roman}</small></td>"
            f"<td class=\"tel-value\">{sy}年{sm}月{sd}日〜</td>"
            f"<td class=\"tel-value\">{ey}</td>"
            f"<td class=\"tel-value\">{dur}年間</td>"
            f"</tr>"
        )

    # JavaScriptによる双方向変換ツール
    # ERA_TABLEをJSに埋め込む（固定値なのでエスケープ問題なし）
    js_era_data = "["
    for era_name, era_roman, start_year, start_month, start_day, end_year in ERA_TABLE:
        end_val = str(end_year) if end_year else "null"
        js_era_data += (
            f"{{name:'{era_name}',roman:'{era_roman}',"
            f"sy:{start_year},sm:{start_month},sd:{start_day},ey:{end_val}}},"
        )
    js_era_data += "]"

    # 出典HTML
    source_items = ""
    for s in sources:
        safe_s = html.escape(str(s))
        source_items += f"<li>{safe_s}</li>"

    return (
        f'<h1>📅 {html.escape(niche)}</h1>'
        f'<p>明治・大正・昭和・平成・令和の元号と西暦を相互に変換できるツールです。'
        f'現在（{html.escape(str(current_year))}年）は <strong>{current_era_str}</strong> です。</p>'

        '<section>'
        '<h2>🔄 変換ツール</h2>'
        '<div class="tool-box">'

        '<div style="margin-bottom:1.5em;">'
        '<h3>西暦 → 元号</h3>'
        '<label for="w2e_input">西暦年を入力（例: 1989）：</label><br>'
        '<input type="number" id="w2e_input" min="1868" max="2100" placeholder="例: 2024" style="font-size:1.1em;padding:0.3em 0.5em;width:160px;">'
        '<button onclick="convertW2E()" style="margin-left:0.5em;font-size:1.1em;padding:0.3em 1em;">変換</button>'
        '<div id="w2e_result" style="margin-top:0.8em;font-size:1.2em;font-weight:bold;color:#1a56a0;"></div>'
        '</div>'

        '<div>'
        '<h3>元号 → 西暦</h3>'
        '<label for="e2w_era">元号を選択：</label><br>'
        '<select id="e2w_era" style="font-size:1.1em;padding:0.3em 0.5em;">'
        '<option value="明治">明治</option>'
        '<option value="大正">大正</option>'
        '<option value="昭和">昭和</option>'
        '<option value="平成">平成</option>'
        '<option value="令和" selected>令和</option>'
        '</select>'
        '<input type="number" id="e2w_year" min="1" max="100" placeholder="例: 6" style="font-size:1.1em;padding:0.3em 0.5em;width:100px;margin-left:0.5em;">'
        '<span style="font-size:1.1em;">年</span>'
        '<button onclick="convertE2W()" style="margin-left:0.5em;font-size:1.1em;padding:0.3em 1em;">変換</button>'
        '<div id="e2w_result" style="margin-top:0.8em;font-size:1.2em;font-weight:bold;color:#1a56a0;"></div>'
        '</div>'

        '</div>'
        '</section>'

        '<section>'
        '<h2>📋 元号一覧（明治以降）</h2>'
        '<table>'
        '<thead><tr><th>元号</th><th>開始日</th><th>終了年</th><th>期間</th></tr></thead>'
        f'<tbody>{era_rows}</tbody>'
        '</table>'
        '</section>'

        '<section>'
        '<h2>💡 早見表（昭和・平成・令和）</h2>'
        '<table>'
        '<thead><tr><th>西暦</th><th>昭和</th><th>平成</th><th>令和</th></tr></thead>'
        '<tbody id="quick_table"></tbody>'
        '</table>'
        '</section>'

        f'<p style="font-size:0.85em;color:#666;">最終更新: {generated_at}</p>'

        f'<script>'
        f'var ERAS={js_era_data};'
        'function convertW2E(){'
        '  var y=parseInt(document.getElementById("w2e_input").value);'
        '  if(isNaN(y)){document.getElementById("w2e_result").textContent="西暦年を数値で入力してください。";return;}'
        '  var results=[];'
        '  for(var i=0;i<ERAS.length;i++){'
        '    var e=ERAS[i];'
        '    if(y<e.sy) continue;'
        '    if(e.ey!==null && y>e.ey) continue;'
        '    var ey2=y-e.sy+1;'
        '    var note="";'
        '    if(y===e.sy) note="（"+e.sm+"月"+e.sd+"日以降）";'
        '    results.push(e.name+ey2+"年"+note+"（"+e.roman+" "+ey2+"）");'
        '  }'
        '  document.getElementById("w2e_result").textContent=results.length?results.join(" / "):"該当する元号がありません（明治元年以降を入力してください）";'
        '}'
        'function convertE2W(){'
        '  var era=document.getElementById("e2w_era").value;'
        '  var ey=parseInt(document.getElementById("e2w_year").value);'
        '  if(isNaN(ey)||ey<1){document.getElementById("e2w_result").textContent="元号年を正の整数で入力してください。";return;}'
        '  for(var i=0;i<ERAS.length;i++){'
        '    var e=ERAS[i];'
        '    if(e.name===era){'
        '      var w=e.sy+ey-1;'
        '      if(e.ey!==null && w>e.ey){document.getElementById("e2w_result").textContent=era+"は"+ey+"年まで存在しません（最大"+(e.ey-e.sy+1)+"年）";return;}'
        '      document.getElementById("e2w_result").textContent=era+ey+"年 = 西暦"+w+"年";'
        '      return;'
        '    }'
        '  }'
        '  document.getElementById("e2w_result").textContent="元号が見つかりません。";'
        '}'
        'function buildQuickTable(){'
        '  var tb=document.getElementById("quick_table");'
        '  var rows="";'
        '  for(var y=1926;y<=2030;y+=5){'
        '    var sho="",hei="",rei="";'
        '    for(var i=0;i<ERAS.length;i++){'
        '      var e=ERAS[i];'
        '      if(y<e.sy) continue;'
        '      if(e.ey!==null && y>e.ey) continue;'
        '      var ey2=y-e.sy+1;'
        '      if(e.name==="昭和") sho=ey2+"年";'
        '      if(e.name==="平成") hei=ey2+"年";'
        '      if(e.name==="令和") rei=ey2+"年";'
        '    }'
        '    rows+="<tr><td>"+y+"</td><td>"+(sho||"—")+"</td><td>"+(hei||"—")+"</td><td>"+(rei||"—")+"</td></tr>";'
        '  }'
        '  tb.innerHTML=rows;'
        '}'
        'buildQuickTable();'
        '</script>'

        '<div class="source">'
        '<strong>データ出典:</strong>'
        f'<ul>{source_items}</ul>'
        '</div>'
    )

