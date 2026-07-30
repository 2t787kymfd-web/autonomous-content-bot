"""
theme.py
--------
サイト全体で使い回す共通CSS・ヘッダー/フッターを一箇所で管理する。
tool_builder.py / publisher.py の生成ページ、docs/ 内の静的ページ(index/about/privacy)
の両方から同じ見た目になるよう参照される(静的ページ側は手動でこの内容と同期する)。
"""

SITE_NAME = "データツールハブ"
SITE_TAGLINE = "公開APIの一次データをもとに自動更新される、無料の計算ツール集"

SITE_CSS = """
:root {
  --accent: #4f46e5;
  --accent-light: #eef2ff;
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --accent: #818cf8;
    --accent-light: #1e1b4b;
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --border: #334155;
  }
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans", sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  line-height: 1.7;
}
.site-header {
  background: linear-gradient(135deg, var(--accent), #7c3aed);
  color: white;
  padding: 28px 16px;
  text-align: center;
}
.site-header a { color: white; text-decoration: none; }
.site-header h1 { margin: 0; font-size: 1.5rem; }
.site-header .tagline { margin: 6px 0 0; font-size: 0.9rem; opacity: 0.9; }
.site-nav {
  display: flex; justify-content: center; gap: 20px;
  margin-top: 14px; font-size: 0.85rem;
}
.site-nav a { text-decoration: none; color: white; opacity: 0.85; }
.site-nav a:hover { opacity: 1; text-decoration: underline; }
main {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 16px 60px;
}
h1, h2 { color: var(--text); }
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin: 16px 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.tool-grid { display: grid; gap: 16px; margin: 24px 0; }
.tool-card {
  display: block;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
  text-decoration: none;
  color: var(--text);
  transition: transform 0.15s, box-shadow 0.15s;
}
.tool-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.tool-card .emoji { font-size: 1.6rem; }
.tool-card .title { font-weight: 600; margin: 4px 0 2px; }
.tool-card .desc { font-size: 0.85rem; color: var(--text-muted); }
.row { margin: 16px 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
input, select {
  font-size: 1rem; padding: 8px 10px;
  border: 1px solid var(--border); border-radius: 8px;
  background: var(--card-bg); color: var(--text);
}
.result {
  font-size: 1.5rem; font-weight: 700; color: var(--accent);
  margin-top: 16px;
}
table { width: 100%; border-collapse: collapse; margin: 16px 0; }
td, th { border-bottom: 1px solid var(--border); padding: 8px 6px; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-muted); font-weight: 600; font-size: 0.85rem; }
.source {
  font-size: 0.8rem; color: var(--text-muted);
  margin-top: 24px; padding-top: 16px; border-top: 1px dashed var(--border);
}
.site-footer {
  text-align: center; padding: 24px 16px; color: var(--text-muted);
  font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 40px;
}
.site-footer a { color: var(--text-muted); }
"""


def site_header() -> str:
    return f"""<header class="site-header">
  <a href="/autonomous-content-bot/"><h1>📊 {SITE_NAME}</h1></a>
  <p class="tagline">{SITE_TAGLINE}</p>
  <nav class="site-nav">
    <a href="/autonomous-content-bot/">トップ</a>
    <a href="/autonomous-content-bot/about.html">運営者情報</a>
    <a href="/autonomous-content-bot/privacy.html">プライバシーポリシー</a>
  </nav>
</header>"""


def site_footer() -> str:
    return f"""<footer class="site-footer">
  <a href="/autonomous-content-bot/about.html">運営者情報</a> ・
  <a href="/autonomous-content-bot/privacy.html">プライバシーポリシー</a>
  <p>&copy; {SITE_NAME} — データは自動取得・自動更新されています</p>
</footer>"""
