"""kind_generator.py が自動生成したプラグイン: postal_code"""

import requests
import html
import re

KIND_NAME = "postal_code"
KEYWORDS = ["郵便番号", "住所検索", "postal code", "zip code", "zipcloud", "番地", "市区町村"]
CATEGORY = "生活計算"

# 動作確認済みの郵便番号: 1000001 → 東京都千代田区千代田
DEFAULT_ZIP = "1000001"


def _extract_zip(niche: str) -> str:
    """ニッチ文字列から郵便番号(7桁数字)を抽出する。見つからなければデフォルトを返す。"""
    digits = re.sub(r"[^0-9]", "", niche)
    if len(digits) == 7:
        return digits
    if len(digits) >= 7:
        return digits[:7]
    return DEFAULT_ZIP


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    zip_code = _extract_zip(niche)

    url = "https://zipcloud.ibsnet.co.jp/api/search"
    resp = requests.get(url, params={"zipcode": zip_code, "limit": 20}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results")
    if not results:
        raise RuntimeError(
            f"郵便番号 {zip_code} の住所が見つかりませんでした (zipcloud API: results=null)"
        )

    rows = []
    for r in results:
        zip7 = r.get("zipcode", "")
        pref = r.get("address1", "")
        city = r.get("address2", "")
        town = r.get("address3", "")
        pref_kana = r.get("kana1", "")
        city_kana = r.get("kana2", "")
        town_kana = r.get("kana3", "")
        rows.append({
            "zipcode": zip7,
            "address": f"{pref}{city}{town}",
            "kana": f"{pref_kana}{city_kana}{town_kana}",
            "pref": pref,
            "city": city,
            "town": town,
        })

    summary = (
        f"郵便番号 {zip_code} の検索結果: {len(rows)}件。"
        f"最初の住所: {rows[0]['address']}({rows[0]['kana']})"
    )
    sources = ["https://zipcloud.ibsnet.co.jp/ (zipcloud 郵便番号検索API)"]
    raw = {
        "zip_code": zip_code,
        "rows": rows,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    zip_code = html.escape(str(raw_data.get("zip_code", "")))
    rows = raw_data.get("rows", [])

    # --- 結果テーブル ---
    table_rows = ""
    for r in rows:
        z = html.escape(str(r.get("zipcode", "")))
        addr = html.escape(str(r.get("address", "")))
        kana = html.escape(str(r.get("kana", "")))
        table_rows += (
            f"<tr>"
            f"<td class='tel-value'>〒{z}</td>"
            f"<td>{addr}</td>"
            f"<td>{kana}</td>"
            f"</tr>"
        )

    result_table = (
        "<table>"
        "<thead><tr><th>郵便番号</th><th>住所</th><th>読み仮名</th></tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table>"
    ) if table_rows else "<p>該当する住所が見つかりませんでした。</p>"

    # --- インタラクティブ検索フォーム ---
    form_html = (
        "<div class='tool-section'>"
        "<h2>郵便番号で住所を検索</h2>"
        "<p>7桁の郵便番号を入力してください（ハイフンあり・なし両方対応）。</p>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;'>"
        "<input id='zip-input' type='text' placeholder='例: 1000001 または 100-0001'"
        " maxlength='8' style='padding:8px 12px;font-size:1rem;border:1px solid #ccc;"
        "border-radius:4px;width:200px;' />"
        "<button onclick='doSearch()' style='padding:8px 18px;font-size:1rem;"
        "background:#0066cc;color:#fff;border:none;border-radius:4px;cursor:pointer;'>"
        "検索</button>"
        "</div>"
        "<div id='zip-result' style='margin-top:16px;'></div>"
        "</div>"
        "<script>"
        "function doSearch(){"
        "  var raw=document.getElementById('zip-input').value;"
        "  var code=raw.replace(/[^0-9]/g,'');"
        "  if(code.length!==7){"
        "    document.getElementById('zip-result').innerHTML="
        "      '<p style=color:red>7桁の数字を入力してください。</p>';"
        "    return;"
        "  }"
        "  var el=document.getElementById('zip-result');"
        "  el.innerHTML='<p>検索中...</p>';"
        "  fetch('https://zipcloud.ibsnet.co.jp/api/search?zipcode='+code+'&limit=20')"
        "    .then(function(r){return r.json();})"
        "    .then(function(d){"
        "      if(!d.results||d.results.length===0){"
        "        el.innerHTML='<p style=color:red>該当する住所が見つかりませんでした。</p>';"
        "        return;"
        "      }"
        "      var html='<table><thead><tr><th>郵便番号</th><th>住所</th><th>読み仮名</th></tr></thead><tbody>';"
        "      d.results.forEach(function(r){"
        "        var z=r.zipcode||'';"
        "        var addr=(r.address1||'')+(r.address2||'')+(r.address3||'');"
        "        var kana=(r.kana1||'')+(r.kana2||'')+(r.kana3||'');"
        "        html+='<tr><td>\u3012'+escHtml(z)+'</td><td>'+escHtml(addr)+'</td><td>'+escHtml(kana)+'</td></tr>';"
        "      });"
        "      html+='</tbody></table>';"
        "      el.innerHTML=html;"
        "    })"
        "    .catch(function(e){"
        "      el.innerHTML='<p style=color:red>通信エラーが発生しました。</p>';"
        "    });"
        "}"
        "function escHtml(s){"
        "  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;');"
        "}"
        "document.getElementById('zip-input').addEventListener('keydown',function(e){"
        "  if(e.key==='Enter')doSearch();"
        "});"
        "</script>"
    )

    # --- 出典 ---
    source_html = "<div class='source'>データ出典: "
    source_parts = []
    for s in sources:
        parts = s.split(" ", 1)
        src_url = parts[0] if parts else ""
        src_label = parts[1].strip("()") if len(parts) > 1 else src_url
        if src_url.startswith("https://"):
            source_parts.append(
                f'<a href="{html.escape(src_url)}" target="_blank" rel="noopener">'
                f'{html.escape(src_label)}</a>'
            )
        else:
            source_parts.append(html.escape(s))
    source_html += "、".join(source_parts) + "</div>"

    return (
        f"<h1>\U0001f4ee 郵便番号検索: 〒{zip_code}</h1>"
        f"<p>郵便番号 <strong class=\"tel-value\">〒{zip_code}</strong> の検索結果です。{len(rows)}件の住所が見つかりました。</p>"
        + result_table
        + form_html
        + source_html
    )

