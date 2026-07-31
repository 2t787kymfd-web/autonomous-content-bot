"""kind_generator.py が自動生成したプラグイン: global_ip"""

import html
import requests

KIND_NAME = "global_ip"
KEYWORDS = ["グローバルIP", "IPアドレス", "接続元IP", "外部IP", "マイIP", "global ip", "ip address", "my ip"]
CATEGORY = "地理・開発者向け"


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    プライバシー配慮のため、サーバー側ではIPアドレスを取得・保存しない。
    api.ipify.orgのエンドポイント疎通確認のみ行い、実データ取得はクライアント側JSで行う。
    """
    # エンドポイントの疎通確認のみ実施(実際のIPはサーバー側で取得・保存しない)
    resp = requests.get("https://api.ipify.org?format=json", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # 疎通確認できたことを確認("ip"キーが存在すれば正常)
    if "ip" not in data:
        raise RuntimeError("ipify APIからipフィールドを取得できませんでした")

    summary = (
        "グローバルIP確認ツール: ipify.org APIの疎通確認に成功しました。"
        "実際のIPアドレス取得はブラウザ上のクライアントサイドJavaScriptで行い、"
        "サーバー側ではユーザーのIPアドレスをログ・保存しません（プライバシー配慮設計）。"
    )
    sources = ["https://api.ipify.org/ (ipify - A Simple Public IP Address API)"]
    raw = {
        "api_endpoint": "https://api.ipify.org?format=json",
        "api_name": "ipify",
        "api_url": "https://www.ipify.org/",
        "privacy_note": "IPアドレスはブラウザ上でのみ取得・表示され、サーバーには送信・保存されません。",
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    IPアドレスの取得はクライアントサイドJavaScriptで完結させる。
    """
    safe_niche = html.escape(str(niche))
    safe_api_name = html.escape(str(raw_data.get("api_name", "ipify")))
    safe_privacy_note = html.escape(str(raw_data.get("privacy_note", "")))
    api_url = raw_data.get("api_url", "")
    safe_api_url = html.escape(api_url) if api_url.startswith("https://") else "#"
    api_endpoint = raw_data.get("api_endpoint", "")
    safe_api_endpoint = html.escape(api_endpoint) if api_endpoint.startswith("https://") else ""

    source_items = ""
    for s in sources:
        safe_s = html.escape(str(s))
        source_items += f"<li>{safe_s}</li>"

    return (
        f'<h1>🌐 {safe_niche}</h1>'
        '<p>あなたの現在のグローバルIPアドレスを確認できます。'
        'IPアドレスはお使いのブラウザから直接取得・表示されるため、'
        '<strong>サーバー側でログ・保存されることはありません</strong>（プライバシー配慮設計）。</p>'
        '<div style="text-align:center; margin: 2em 0;">'
        '  <div id="ip-result" style="'
        '    font-size: 2.2em; font-weight: bold; letter-spacing: 0.05em;'
        '    padding: 0.6em 1.2em; border-radius: 8px;'
        '    background: #f0f4ff; border: 2px solid #4a6cf7;'
        '    display: inline-block; min-width: 300px;">'
        '    <span id="ip-value" class="tel-value" style="color: #4a6cf7;">取得中…</span>'
        '  </div>'
        '  <br><br>'
        '  <button id="ip-reload-btn" onclick="fetchMyIP()" style="'
        '    padding: 0.5em 1.6em; font-size: 1em; cursor: pointer;'
        '    border-radius: 6px; border: 1px solid #4a6cf7;'
        '    background: #4a6cf7; color: #fff; font-weight: bold;">'
        '    🔄 再取得'
        '  </button>'
        '</div>'
        '<table>'
        '  <thead><tr><th>項目</th><th>内容</th></tr></thead>'
        '  <tbody>'
        '    <tr><td>あなたのIPアドレス</td><td id="ip-table-val" class="tel-value">取得中…</td></tr>'
        '    <tr><td>IPバージョン</td><td id="ip-version">取得中…</td></tr>'
        '    <tr><td>取得日時</td><td id="ip-time" class="tel-value">取得中…</td></tr>'
        '    <tr><td>プライバシー</td>'
        f'      <td>{safe_privacy_note}</td></tr>'
        f'    <tr><td>使用API</td><td><a href="{safe_api_url}" target="_blank" rel="noopener noreferrer">{safe_api_name}</a></td></tr>'
        '  </tbody>'
        '</table>'
        '<h2>💡 グローバルIPアドレスとは？</h2>'
        '<p>グローバルIPアドレスは、インターネット上でお使いのデバイス（またはルーター）を'
        '一意に識別するアドレスです。'
        'Wi-Fi・モバイル回線・VPNの切り替えにより変化することがあります。</p>'
        '<ul>'
        '  <li><strong>IPv4</strong>: 例) 203.0.113.1（32ビット、ドット区切り4つの数字）</li>'
        '  <li><strong>IPv6</strong>: 例) 2001:db8::1（128ビット、コロン区切りの16進数）</li>'
        '  <li><strong>VPN使用時</strong>: VPNサーバーのIPアドレスが表示されます</li>'
        '  <li><strong>共有回線</strong>: 同じWi-Fiを使う複数端末は同一のグローバルIPを持ちます</li>'
        '</ul>'
        '<h2>🔒 プライバシーについて</h2>'
        '<p>このツールでは、IPアドレスの取得・表示はすべてお使いのブラウザ上でのみ行われます。'
        'あなたのIPアドレスはこのサイトのサーバーには送信・記録されません。</p>'
        f'<script>'
        'async function fetchMyIP() {{'
        '  var ipVal = document.getElementById("ip-value");'
        '  var ipTableVal = document.getElementById("ip-table-val");'
        '  var ipVersion = document.getElementById("ip-version");'
        '  var ipTime = document.getElementById("ip-time");'
        '  ipVal.textContent = "取得中…";'
        '  try {{'
        f'    var res = await fetch("{safe_api_endpoint}");'
        '    if (!res.ok) throw new Error("HTTP " + res.status);'
        '    var data = await res.json();'
        '    var ip = data.ip || "取得失敗";'
        '    ipVal.textContent = ip;'
        '    ipTableVal.textContent = ip;'
        '    var ver = ip.indexOf(":") !== -1 ? "IPv6" : "IPv4";'
        '    ipVersion.textContent = ver;'
        '    var now = new Date();'
        '    ipTime.textContent = now.toLocaleString("ja-JP");'
        '  }} catch(e) {{'
        '    ipVal.textContent = "取得失敗: " + e.message;'
        '    ipTableVal.textContent = "取得失敗";'
        '    ipVersion.textContent = "-";'
        '    ipTime.textContent = "-";'
        '  }}'
        '}}'
        'fetchMyIP();'
        '</script>'
        '<div class="source">データ出典: '
        f'<ul>{source_items}</ul>'
        '</div>'
    )

