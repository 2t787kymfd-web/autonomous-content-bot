"""
theme.py
--------
サイト全体で使い回す共通CSS・ヘッダー/フッターを一箇所で管理する。
Pico.css(CDN)+ docs/assets/theme.css(「観測盤」デザイン言語、ダーク基調・
カテゴリ別ゲージカラー・数値表示専用の等幅フォント)をベースに、ヘッダー/
フッターのブランディングとツールページ特有のUI要素(結果表示・出典表記等)
を追加する。
tool_builder.py / publisher.py の生成ページ、docs/ 内の静的ページ
(index/about/privacy)の両方から同じ見た目になるよう参照される
(静的ページ側は手動でこの内容と同期する)。

以前は個々のページの<head>に<style>{SITE_CSS}</style>として直接埋め込んで
いたが、全ページ共通の1つの外部theme.cssへのリンクに統一した(重複を無くし、
ブラウザキャッシュも効くようにするため)。
"""

SITE_NAME = "データツールハブ"

# GitHub Pages(プロジェクトサイト)のベースパス。カテゴリ別サブディレクトリ
# (docs/finance/xxx.html等)が導入されたことで、相対パス"./assets/..."では
# ページの深さによって参照先がズレる(例: docs/finance/配下からは
# "./assets/"はdocs/finance/assets/を指してしまう)。そのため全ての内部リンク・
# アセット参照はこのベースパスからのルート相対パスに統一する
# (ページがどの深さにあっても常に同じ場所を指す)。
SITE_BASE_PATH = "/autonomous-content-bot"
# sitemap.xml等、絶対URLが必須な場面用
SITE_BASE_URL = "https://2t787kymfd-web.github.io" + SITE_BASE_PATH

PICO_CDN_LINK = (
    '<link rel="stylesheet" '
    'href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">'
)

# サイト共通デザイン(観測盤コンセプト: docs/assets/theme.css)の読み込みタグ。
THEME_CSS_LINK = f'<link rel="stylesheet" href="{SITE_BASE_PATH}/assets/theme.css">'

# ハンバーガーメニュー(カテゴリ別ナビゲーション、docs/assets/nav.js)の読み込みタグ。
NAV_ASSETS_HEAD = (
    f'<link rel="stylesheet" href="{SITE_BASE_PATH}/assets/nav.css">\n'
    f'<script defer src="{SITE_BASE_PATH}/assets/nav.js"></script>\n'
    f'<script defer src="{SITE_BASE_PATH}/assets/cards.js"></script>'
)

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
      <li><a href="{SITE_BASE_PATH}/index.html">{_LOGO_SVG}<strong class="logo-text">{SITE_NAME}</strong></a></li>
    </ul>
    <ul>
      <li><a href="{SITE_BASE_PATH}/index.html">トップ</a></li>
      <li><a href="{SITE_BASE_PATH}/about.html">運営者情報</a></li>
      <li><a href="{SITE_BASE_PATH}/privacy.html">プライバシーポリシー</a></li>
    </ul>
  </nav>
</header>"""


def site_footer() -> str:
    return f"""<footer class="site-footer">
  <a href="{SITE_BASE_PATH}/about.html">運営者情報</a> ・
  <a href="{SITE_BASE_PATH}/privacy.html">プライバシーポリシー</a>
  <p>&copy; {SITE_NAME} — データは自動取得・自動更新されています</p>
</footer>"""
