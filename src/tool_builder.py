"""
tool_builder.py
-----------------
「記事」ではなく、ブラウザ上で実際に入力・計算できる
インタラクティブなツールページ(HTML+JS)を組み立てる。

AIに直接HTML/JSを生成させると壊れたコードが混ざるリスクが
あるため、ここは決定的(deterministic)なPythonコードで
テンプレートに実データを埋め込む方式にしている。
AIが担当するのは「どのニッチにどのツールを割り当てるか」の
判断(main_loop側)であり、ツール自体の実装は固定テンプレート。
"""

import html
import json
import os
from typing import Dict, List, Optional

from .ads import ADSENSE_HEAD_SNIPPET
from .theme import NAV_ASSETS_HEAD, PICO_CDN_LINK, SITE_BASE_PATH, THEME_CSS_LINK, site_footer, site_header


# fx/crypto/weatherはプラグイン(src/kinds/*.py)ではなくこのファイル内の
# 固定テンプレートのため、CATEGORYを定数として持たせる場所が無い。
# そのため専用の小さな辞書で対応する。プラグイン系kindは各ファイルに
# CATEGORY定数を持たせる方式(get_kind_category()側でフォールバックする)。
CORE_KIND_CATEGORIES = {
    "fx": "金融",
    "crypto": "金融",
    "weather": "天気・防災",
}


def get_kind_category(kind_name: str) -> str:
    """kind名からナビゲーションのカテゴリ名を解決する。
    コアkind辞書→プラグインのCATEGORY属性→フォールバック"その他"の順で解決する。"""
    if kind_name in CORE_KIND_CATEGORIES:
        return CORE_KIND_CATEGORIES[kind_name]

    from .researcher import _load_kind_plugins

    for plugin in _load_kind_plugins():
        if kind_name == plugin.KIND_NAME:
            return getattr(plugin, "CATEGORY", "その他")
    return "その他"


# カテゴリ名(日本語)→ 公開先ディレクトリ名(英数字、URLに使う)。
# publisher.pyの出力先決定と、このファイルの関連リンク生成の両方から
# get_slug_for_kind()経由で参照される単一の対応表。
CATEGORY_DIR_SLUGS = {
    "金融": "finance",
    "天気・防災": "weather",
    "天文・暦": "astronomy",
    "生活計算": "life",
    "暦・和文化": "culture",
    "国・地域・雑学": "trivia",
    "地理・開発者向け": "geo",
    "エンタメ": "entertainment",
    "スポーツ": "sports",
}
DEFAULT_CATEGORY_DIR_SLUG = "misc"


def get_category_dir_slug(category: str) -> str:
    return CATEGORY_DIR_SLUGS.get(category, DEFAULT_CATEGORY_DIR_SLUG)


def get_slug_for_kind(kind_name: str) -> str:
    """kind名から、拡張子なしの公開先相対パス(例: "finance/fx")を組み立てる。
    publisher.py(実際のファイル出力先)とtool_builder.py(関連リンク生成)の
    両方が同じ計算式を使うことで、パスの不整合を防ぐ。"""
    category = get_kind_category(kind_name)
    category_dir = get_category_dir_slug(category)
    return f"{category_dir}/{kind_name}"


_MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "docs", "assets", "manifest.json"
)


def _render_related_links(kind_name: str, own_slug: str) -> str:
    """同じカテゴリの他のツールへのリンクを2〜3件、manifest.jsonから読んで
    サーバーサイドで静的HTMLに埋め込む(クライアントサイドJSでのfetchに
    頼らないため、確実に表示されJSTのSEOクロールにも乗る)。"""
    if not os.path.exists(_MANIFEST_PATH):
        return ""
    try:
        with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""

    category = get_kind_category(kind_name)
    candidates = [
        e for e in manifest
        if e.get("category") == category and e.get("slug") != own_slug
    ]
    candidates.sort(key=lambda e: e.get("niche", ""))
    picks = candidates[:3]
    if not picks:
        return ""

    items = "".join(
        f'<li><a href="{SITE_BASE_PATH}/{html.escape(str(e["slug"]))}.html">'
        f'{html.escape(str(e.get("niche", e["slug"])))}</a></li>'
        for e in picks
    )
    return (
        f'<section class="related-tools"><h2>🔗 同じカテゴリの他のツール</h2>'
        f'<ul>{items}</ul></section>'
    )


def _render_description_and_faq(description: str, faq: Optional[List[dict]]) -> str:
    """generator.pyのgenerate_tool_description()が生成した説明文・FAQを
    HTML化する。AI生成テキストなのでhtml.escape()を通す(プレーンテキストの
    想定だが、防御的に処理する)。"""
    if not description and not faq:
        return ""
    parts = []
    if description:
        safe_desc = html.escape(description).replace("\n", "<br>")
        parts.append(f'<section class="tool-description"><p>{safe_desc}</p></section>')
    if faq:
        items = "".join(
            f'<details><summary>{html.escape(item["q"])}</summary>'
            f'<p>{html.escape(item["a"])}</p></details>'
            for item in faq
        )
        parts.append(f'<section class="tool-faq"><h2>よくある質問</h2>{items}</section>')
    return "".join(parts)


def build_fx_converter_html(
    niche: str, raw_data: Dict, sources: list,
    description: str = "", faq: Optional[List[dict]] = None,
) -> str:
    rates = raw_data["rates"]          # 例: {"USD": 155.2, "EUR": 168.0, ...}
    target = raw_data["target"]        # "JPY"
    date = raw_data["date"]
    rates_json = json.dumps(rates, ensure_ascii=False)
    source_line = " / ".join(sources)
    description_html = _render_description_and_faq(description, faq)
    related_html = _render_related_links("fx", get_slug_for_kind("fx"))

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{niche}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{PICO_CDN_LINK}
{ADSENSE_HEAD_SNIPPET}
{NAV_ASSETS_HEAD}
{THEME_CSS_LINK}
</head>
<body>
{site_header()}
<main class="container">
  <article>
  <h1>💱 {niche}</h1>
  {description_html}
  <p>基準日: {date} のレートを使った換算ツールです。</p>

  <div class="row">
    <input id="amount" type="number" value="1" step="any">
    <select id="currency"></select>
    <span>→ {target}</span>
  </div>

  <div class="result tel-value" id="result"></div>
  <div class="source">データ出典: {source_line}(基準日 {date} 時点)</div>
  {related_html}
  </article>
</main>
{site_footer()}

<script>
  const rates = {rates_json};
  const target = "{target}";

  const select = document.getElementById("currency");
  Object.keys(rates).forEach(code => {{
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = code;
    select.appendChild(opt);
  }});

  function update() {{
    const amount = parseFloat(document.getElementById("amount").value) || 0;
    const code = select.value;
    const rate = rates[code];
    const converted = (amount * rate).toLocaleString(undefined, {{maximumFractionDigits: 2}});
    document.getElementById("result").textContent = `${{amount}} ${{code}} = ${{converted}} ${{target}}`;
  }}

  document.getElementById("amount").addEventListener("input", update);
  select.addEventListener("change", update);
  update();
</script>
</body>
</html>
"""


def build_crypto_dashboard_html(
    niche: str, raw_data: Dict, sources: list,
    description: str = "", faq: Optional[List[dict]] = None,
) -> str:
    prices = raw_data["prices"]        # 例: {"bitcoin": {"jpy": ..., "usd": ...}, ...}
    fetched_at = raw_data["fetched_at"]
    prices_json = json.dumps(prices, ensure_ascii=False)
    source_line = " / ".join(sources)
    description_html = _render_description_and_faq(description, faq)
    related_html = _render_related_links("crypto", get_slug_for_kind("crypto"))

    rows = "\n".join(
        f'<option value="{coin_id}">{coin_id}</option>' for coin_id in prices.keys()
    )

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{niche}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{PICO_CDN_LINK}
{ADSENSE_HEAD_SNIPPET}
{NAV_ASSETS_HEAD}
{THEME_CSS_LINK}
</head>
<body>
{site_header()}
<main class="container">
  <article>
  <h1>🪙 {niche}</h1>
  {description_html}
  <p>取得時刻: {fetched_at}(UTC)のスナップショットです。</p>

  <table id="price-table"></table>

  <div class="row">
    <input id="amount" type="number" value="1" step="any">
    <select id="coin">{rows}</select>
    <span>の現在価値:</span>
    <div class="result tel-value" id="result"></div>
  </div>

  <div class="source">データ出典: {source_line}</div>
  {related_html}
  </article>
</main>
{site_footer()}

<script>
  const prices = {prices_json};

  const table = document.getElementById("price-table");
  let html = "<tr><th>銘柄</th><th>USD</th><th>JPY</th></tr>";
  for (const [coin, v] of Object.entries(prices)) {{
    html += `<tr><td>${{coin}}</td><td class="tel-value">${{v.usd ?? "-"}}</td><td class="tel-value">${{v.jpy ?? "-"}}</td></tr>`;
  }}
  table.innerHTML = html;

  const coinSelect = document.getElementById("coin");
  function update() {{
    const amount = parseFloat(document.getElementById("amount").value) || 0;
    const coin = coinSelect.value;
    const p = prices[coin];
    const jpy = (amount * (p.jpy ?? 0)).toLocaleString(undefined, {{maximumFractionDigits: 0}});
    const usd = (amount * (p.usd ?? 0)).toLocaleString(undefined, {{maximumFractionDigits: 2}});
    document.getElementById("result").textContent = `≈ ${{jpy}} JPY / ${{usd}} USD`;
  }}
  document.getElementById("amount").addEventListener("input", update);
  coinSelect.addEventListener("change", update);
  update();
</script>
</body>
</html>
"""


def build_weather_dashboard_html(
    niche: str, raw_data: Dict, sources: list,
    description: str = "", faq: Optional[List[dict]] = None,
) -> str:
    cities = raw_data["cities"]        # 例: {"東京": {"description": "晴れ", "temperature": 28.4, ...}, ...}
    fetched_at = raw_data["fetched_at"]
    # forecast_dateは全都市で同じ日付になる想定(同一サイクル内で取得するため)なので
    # 見出しに1回だけ表示し、行ごとには観測時刻(observed_at、都市により数分ずれうる)を出す
    forecast_date = next(iter(cities.values())).get("forecast_date", "不明") if cities else "不明"
    source_line = " / ".join(sources)
    description_html = _render_description_and_faq(description, faq)
    related_html = _render_related_links("weather", get_slug_for_kind("weather"))

    rows = "\n".join(
        f'<tr><td>{city}</td><td>{d["description"]}</td>'
        f'<td class="tel-value">{d["temperature"]}°C<br><span class="observed-at">{d.get("observed_at", "不明")} JST時点</span></td>'
        f'<td class="tel-value">{d["temp_max"]}°C / {d["temp_min"]}°C</td>'
        f'<td class="tel-value">{d["precipitation_probability"]}%</td></tr>'
        for city, d in cities.items()
    )

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{niche}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{PICO_CDN_LINK}
{ADSENSE_HEAD_SNIPPET}
{NAV_ASSETS_HEAD}
{THEME_CSS_LINK}
</head>
<body>
{site_header()}
<main class="container">
  <article>
  <h1>☀️ {niche}</h1>
  {description_html}
  <p>データ取得: {fetched_at} UTC。各都市の気温は観測時刻(表内に記載、日本時間)時点の値、
  最高/最低気温・降水確率は<strong>{forecast_date}(本日)</strong>の予報値です。</p>

  <table>
    <tr><th>都市</th><th>天気</th><th>気温</th><th>本日の最高/最低</th><th>降水確率</th></tr>
    {rows}
  </table>

  <div class="source">データ出典: {source_line}</div>
  {related_html}
  </article>
</main>
{site_footer()}
</body>
</html>
"""


_CORE_TOOL_KINDS = {"fx", "weather", "crypto"}


def is_tool_kind(kind_name: Optional[str]) -> bool:
    """このkindがbuild_tool_html()でツール(決定的なHTML+JS)を生成できるか。
    main_loop.pyがjudge_niche()の「記事としての差別化」基準をツールに
    適用しない(免除する)かどうかの判定に使う。build_tool_html()自体を
    呼ぶとdescription/FAQ生成(初回はAI呼び出しでコストが発生)まで
    走ってしまうため、判定だけの軽量な代替として用意する。"""
    if kind_name in _CORE_TOOL_KINDS:
        return True
    from .researcher import _load_kind_plugins

    return any(kind_name == plugin.KIND_NAME for plugin in _load_kind_plugins())


def build_tool_html(research, description: str = "", faq: Optional[List[dict]] = None) -> str:
    """research.kind に応じて適切なツールを組み立てる。未対応kindはNoneを返す。"""
    if research.kind == "fx":
        return build_fx_converter_html(research.niche, research.raw_data, research.sources, description, faq)
    if research.kind == "weather":
        return build_weather_dashboard_html(research.niche, research.raw_data, research.sources, description, faq)
    if research.kind == "crypto":
        return build_crypto_dashboard_html(research.niche, research.raw_data, research.sources, description, faq)

    # kind_generator.pyが生成したプラグイン(src/kinds/*.py)にマッチするか確認
    from .researcher import _load_kind_plugins

    for plugin in _load_kind_plugins():
        if research.kind == plugin.KIND_NAME:
            fragment = plugin.build_html(research.niche, research.raw_data, research.sources)
            return _wrap_plugin_fragment(research.niche, fragment, research.kind, description, faq)
    return None


def _wrap_plugin_fragment(
    niche: str, fragment: str, kind_name: str = "",
    description: str = "", faq: Optional[List[dict]] = None,
) -> str:
    """プラグインのbuild_html()は本文の断片だけを返す契約になっているため、
    fx/crypto/weatherの各テンプレートと同じ共通ページシェル(ヘッダー/フッター/
    CSS/広告タグ)で包んで完成品HTMLにする。説明文/FAQはプラグイン自身の
    <h1>直後に挿入したいところだが、fragmentの内部構造はプラグインごとに
    異なりここからは制御できないため、fragment全体(データ表示部分)の
    直後・</article>の直前に配置する(FAQが末尾に来るのは他サイトでも
    一般的なレイアウトのため許容する)。"""
    description_html = _render_description_and_faq(description, faq)
    related_html = _render_related_links(kind_name, get_slug_for_kind(kind_name)) if kind_name else ""
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{niche}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{PICO_CDN_LINK}
{ADSENSE_HEAD_SNIPPET}
{NAV_ASSETS_HEAD}
{THEME_CSS_LINK}
</head>
<body>
{site_header()}
<main class="container">
  <article>
  {fragment}
  {description_html}
  {related_html}
  </article>
</main>
{site_footer()}
</body>
</html>
"""
