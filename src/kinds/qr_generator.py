"""kind_generator.py が自動生成したプラグイン: qr_generator"""

import requests

import html
import math

KIND_NAME = "qr_generator"
KEYWORDS = ["QRコード", "QR", "qr code", "qr generator", "二次元バーコード", "URL変換", "テキスト変換"]
CATEGORY = "生活計算"


def fetch(niche: str) -> tuple:
    """
    QRコード生成はクライアントサイドJSで完結するため、サーバー側でAPIを叩く必要はない。
    bmi_calculator等と同じパターンで固定の説明用データを返す。
    """
    summary = (
        "QRコード生成ツール: ユーザーが入力したテキストやURLを"
        "api.qrserver.com (goqr.me) のAPIを利用してQRコード画像に変換するツールです。"
        "ブラウザ上でリアルタイムに生成され、画像としてダウンロードも可能です。"
    )
    sources = [
        "https://api.qrserver.com/ (goqr.me QR Code API - 無料・APIキー不要)"
    ]
    raw = {
        "tool": "QRコード生成ツール",
        "api_endpoint": "https://api.qrserver.com/v1/create-qr-code/",
        "description": "テキスト・URLを入力するとQRコードを即座に生成します。",
        "features": [
            "テキスト・URL・メールアドレス等あらゆる文字列に対応",
            "サイズ変更可能（100px〜1000px）",
            "生成した画像をダウンロード可能",
            "クライアントサイドで完結（入力内容はサーバーに送信されません）"
        ]
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    safe_niche = html.escape(str(niche))
    safe_tool = html.escape(str(raw_data.get("tool", "QRコード生成ツール")))
    safe_desc = html.escape(str(raw_data.get("description", "")))
    features = raw_data.get("features", [])
    features_html = "".join(
        f"<li>{html.escape(str(f))}</li>" for f in features
    )
    source_html = "".join(
        f"<li>{html.escape(str(s))}</li>" for s in sources
    )

    return f"""
<h1>&#x1F4F1; {safe_niche}</h1>
<p>{safe_desc}</p>

<div class="card" style="max-width:600px;margin:0 auto;">
  <div style="margin-bottom:1rem;">
    <label for="qr-input" style="display:block;font-weight:bold;margin-bottom:0.4rem;">&#x2328; テキストまたはURLを入力</label>
    <textarea id="qr-input" rows="4" style="width:100%;padding:0.6rem;font-size:1rem;border:1px solid #ccc;border-radius:6px;resize:vertical;box-sizing:border-box;" placeholder="https://example.com または任意のテキスト"></textarea>
  </div>
  <div style="display:flex;gap:0.8rem;align-items:center;flex-wrap:wrap;margin-bottom:1rem;">
    <label for="qr-size" style="font-weight:bold;">&#x1F4CF; サイズ:</label>
    <select id="qr-size" style="padding:0.4rem 0.8rem;font-size:1rem;border:1px solid #ccc;border-radius:6px;">
      <option value="150">150px（小）</option>
      <option value="200" selected>200px（標準）</option>
      <option value="300">300px（中）</option>
      <option value="400">400px（大）</option>
      <option value="600">600px（特大）</option>
    </select>
    <button id="qr-btn" onclick="generateQR()" style="padding:0.5rem 1.4rem;font-size:1rem;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;">&#x25B6; 生成</button>
    <button id="qr-clear" onclick="clearQR()" style="padding:0.5rem 1rem;font-size:1rem;background:#6b7280;color:#fff;border:none;border-radius:6px;cursor:pointer;">&#x2715; クリア</button>
  </div>
  <div id="qr-error" style="display:none;color:#dc2626;font-weight:bold;margin-bottom:0.8rem;"></div>
  <div id="qr-result" style="display:none;text-align:center;">
    <img id="qr-image" src="" alt="QRコード" style="border:1px solid #e5e7eb;border-radius:8px;max-width:100%;" />
    <div style="margin-top:0.8rem;">
      <a id="qr-download" href="" download="qrcode.png" style="display:inline-block;padding:0.5rem 1.2rem;background:#16a34a;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold;">&#x2B07; ダウンロード (PNG)</a>
    </div>
    <p id="qr-text-preview" style="font-size:0.85rem;color:#6b7280;margin-top:0.6rem;word-break:break-all;"></p>
  </div>
</div>

<h2>&#x2139; 機能説明</h2>
<ul>
{features_html}
</ul>

<h2>&#x1F4D6; 使い方</h2>
<ol>
  <li>テキストエリアにQRコードに変換したいテキストまたはURLを入力します。</li>
  <li>サイズを選択して「生成」ボタンを押します。</li>
  <li>QRコード画像が表示されたら「ダウンロード」ボタンで保存できます。</li>
  <li>スマートフォンのカメラで読み取ると、入力したURLやテキストを確認できます。</li>
</ol>

<script>
function generateQR() {{
  var input = document.getElementById('qr-input').value.trim();
  var size = document.getElementById('qr-size').value;
  var errEl = document.getElementById('qr-error');
  var resultEl = document.getElementById('qr-result');
  var imgEl = document.getElementById('qr-image');
  var dlEl = document.getElementById('qr-download');
  var previewEl = document.getElementById('qr-text-preview');

  errEl.style.display = 'none';
  errEl.textContent = '';

  if (!input) {{
    errEl.textContent = '\u26a0 テキストまたはURLを入力してください。';
    errEl.style.display = 'block';
    resultEl.style.display = 'none';
    return;
  }}

  var encoded = encodeURIComponent(input);
  var url = 'https://api.qrserver.com/v1/create-qr-code/?data=' + encoded + '&size=' + size + 'x' + size + '&format=png&charset-source=UTF-8';

  imgEl.onload = function() {{
    resultEl.style.display = 'block';
  }};
  imgEl.onerror = function() {{
    resultEl.style.display = 'none';
    errEl.textContent = '\u26a0 QRコードの生成に失敗しました。ネットワーク接続を確認してください。';
    errEl.style.display = 'block';
  }};

  imgEl.src = url;
  dlEl.href = url;

  var preview = input.length > 60 ? input.substring(0, 60) + '\u2026' : input;
  previewEl.textContent = '\u5185\u5bb9: ' + preview;
}}

function clearQR() {{
  document.getElementById('qr-input').value = '';
  document.getElementById('qr-result').style.display = 'none';
  document.getElementById('qr-error').style.display = 'none';
  document.getElementById('qr-image').src = '';
  document.getElementById('qr-text-preview').textContent = '';
}}

document.getElementById('qr-input').addEventListener('keydown', function(e) {{
  if (e.ctrlKey && e.key === 'Enter') {{
    generateQR();
  }}
}});
</script>

<div class="source">
  <strong>データ出典:</strong>
  <ul>
  {source_html}
  </ul>
  <small>QRコード画像はapi.qrserver.com（goqr.me）のAPIを利用してブラウザ上でリアルタイム生成されます。入力したテキストはQRコード生成APIにのみ送信されます。</small>
</div>
"""

