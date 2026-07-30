"""
theme.py
--------
サイト全体で使い回す共通CSS・ヘッダー/フッターを一箇所で管理する。
Pico.css(CDN)をベースに、ヘッダー/フッターのブランディングと
ツールページ特有のUI要素(結果表示・出典表記等)を追加する。
tool_builder.py / publisher.py の生成ページ、docs/ 内の静的ページ
(index/about/privacy)の両方から同じ見た目になるよう参照される
(静的ページ側は手動でこの内容と同期する)。
"""

SITE_NAME = "データツールハブ"

PICO_CDN_LINK = (
    '<link rel="stylesheet" '
    'href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">'
)

SITE_CSS = """
:root { --header-bg: #f5f3ff; --header-border: #ddd6fe; --logo-accent: #4f46e5; }
@media (prefers-color-scheme: dark) {
  :root { --header-bg: #1e1b3a; --header-border: #3730a3; --logo-accent: #a5b4fc; }
}
.site-header { background: var(--header-bg); border-bottom: 1px solid var(--header-border); }
.logo-icon { vertical-align: -5px; margin-right: 4px; }
.logo-text { color: var(--logo-accent); font-size: 1.15rem; }
.site-header a { text-decoration: none; }
@media (max-width: 480px) {
  .site-header nav { flex-direction: column; gap: 10px; }
  .site-header nav ul { justify-content: center; flex-wrap: wrap; }
}
.site-footer { text-align: center; padding: 24px 16px; font-size: 0.85rem; }
.row { margin: 16px 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.result { font-size: 1.5rem; font-weight: 700; color: var(--logo-accent); margin-top: 16px; }
.source {
  font-size: 0.8rem; margin-top: 24px; padding-top: 16px;
  border-top: 1px dashed var(--pico-muted-border-color, #ddd);
}
"""

_LOGO_SVG = (
    '<svg class="logo-icon" width="22" height="22" viewBox="0 0 24 24" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<rect x="3" y="12" width="4" height="9" rx="1" fill="#4f46e5"/>'
    '<rect x="10" y="6" width="4" height="15" rx="1" fill="#7c3aed"/>'
    '<rect x="17" y="9" width="4" height="12" rx="1" fill="#4f46e5"/>'
    "</svg>"
)


def site_header() -> str:
    return f"""<header class="container site-header">
  <nav>
    <ul>
      <li><a href="index.html">{_LOGO_SVG}<strong class="logo-text">{SITE_NAME}</strong></a></li>
    </ul>
    <ul>
      <li><a href="index.html">トップ</a></li>
      <li><a href="about.html">運営者情報</a></li>
      <li><a href="privacy.html">プライバシーポリシー</a></li>
    </ul>
  </nav>
</header>"""


def site_footer() -> str:
    return f"""<footer class="site-footer">
  <a href="about.html">運営者情報</a> ・
  <a href="privacy.html">プライバシーポリシー</a>
  <p>&copy; {SITE_NAME} — データは自動取得・自動更新されています</p>
</footer>"""
