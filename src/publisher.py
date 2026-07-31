"""
publisher.py
-------------
生成された記事を静的サイトのHTMLとして書き出す。

実運用では、この後に以下のようなデプロイ処理を追加する:
  - git add/commit/push (GitHub Pages)
  - netlify/vercel CLI 経由のデプロイ
  - S3/Cloud Storage への同期

ここでは "site/" フォルダにHTMLを出力するところまでを実装する。
dry_run モードでは実際のファイル書き出しもログのみに留める。
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Optional

from .ads import ADSENSE_HEAD_SNIPPET
from .theme import NAV_ASSETS_HEAD, PICO_CDN_LINK, SITE_BASE_URL, THEME_CSS_LINK, site_footer, site_header

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def publish_article(title: str, content_markdown: str, output_dir: str, dry_run: bool, kind: str = "") -> str:
    """テキスト記事を簡易HTMLに包んで公開する。記事ごとに新しいslugを発行する
    (同一ニッチでも内容が変わるたびに新規ページとして品質ゲートの対象にするため)。
    カテゴリ別ディレクトリ配下に置く(publish_toolと同じ振り分けルール)。"""
    from .tool_builder import get_category_dir_slug, get_kind_category

    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
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
  <h1>📰 {title}</h1>
  <pre style="white-space: pre-wrap; font-family: inherit;">{content_markdown}</pre>
  </article>
</main>
{site_footer()}
</body>
</html>
"""
    category_dir = get_category_dir_slug(get_kind_category(kind)) if kind else "misc"
    slug = f"{category_dir}/{slugify(title)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    # 記事は同一kindでも複数slug(タイムスタンプ違い)が同時に存在しうる設計のため、
    # publish_toolのような「同一kindは1エントリのみ」のデデュープは適用しない。
    return _write(slug, html, output_dir, dry_run, niche=title, kind=kind, dedupe_by_kind=False)


def publish_tool(title: str, full_html: str, output_dir: str, dry_run: bool, kind: str = "") -> str:
    """tool_builder.py が組み立てた完成済みHTML(インタラクティブツール)をそのまま公開する。

    ツールは「同じニッチの最新レート/価格に更新する」のが目的であり、記事のような
    量産スパムのリスクは無い(むしろ更新されない方が実利用上の問題になる)ため、
    kind名ベースの安定したslug(タイムスタンプ無し)を使い、毎サイクル同じURLを
    上書き更新する。slugはカテゴリ別ディレクトリ配下(例: finance/fx)に
    kind名(英数字、クリーンなURL)で決まる(tool_builder.get_slug_for_kind()と
    同じ計算式を共有し、パスの不整合を防ぐ)。
    """
    from .tool_builder import get_slug_for_kind

    slug = get_slug_for_kind(kind) if kind else slugify(title)
    return _write(slug, full_html, output_dir, dry_run, niche=title, kind=kind)


def _write(
    slug: str, html: str, output_dir: str, dry_run: bool,
    niche: str = "", kind: str = "", dedupe_by_kind: bool = True,
) -> str:
    path = os.path.join(output_dir, f"{slug}.html")

    if dry_run:
        print(f"[publisher] dry_run のため実際には書き出しません: {path}")
        return slug

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[publisher] 公開しました: {path}")
    stale_path = None
    if dedupe_by_kind:
        stale_path = _remove_stale_path_for_kind(slug, kind, output_dir)
    manifest_path = _upsert_manifest(slug, niche, kind, output_dir, dedupe_by_kind=dedupe_by_kind)
    sitemap_path = _regenerate_sitemap(output_dir)
    paths_to_commit = [path, manifest_path, sitemap_path]
    if stale_path:
        paths_to_commit.append(stale_path)
    _git_publish(paths_to_commit)
    return slug


def _remove_stale_path_for_kind(new_slug: str, kind: str, output_dir: str) -> Optional[str]:
    """URLスキーム変更(旧: フラット配置の日本語slug → 新: カテゴリ別ディレクトリ+
    kind名)に伴う移行処理。同じkindの過去のmanifestエントリが新しいslugと
    異なるパスを指していた場合、その旧ファイルを削除し重複公開を防ぐ。
    削除したファイルパスを返す(git addで削除を記録するため。無ければNone)。
    dedupe_by_kind=Trueのツール系公開でのみ呼ばれる(記事は対象外)。"""
    if not kind:
        return None
    manifest_path = os.path.join(output_dir, "assets", MANIFEST_FILENAME)
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    for entry in manifest:
        if entry.get("kind") == kind and entry.get("slug") != new_slug:
            old_path = os.path.join(output_dir, f"{entry['slug']}.html")
            if os.path.exists(old_path):
                os.remove(old_path)
                print(f"[publisher] 旧URLスキームのファイルを削除しました: {old_path}")
                return old_path
    return None


MANIFEST_FILENAME = "manifest.json"


def _upsert_manifest(
    slug: str, niche: str, kind: str, output_dir: str, dedupe_by_kind: bool = True,
) -> str:
    """ハンバーガーメニュー(nav.js)がカテゴリ別一覧を組み立てるための
    docs/assets/manifest.json を更新する。同一slugは新規追加せず上書きする
    (state.pyのcontent_corpusと同じupsertパターン)。published_atは初回公開時刻を
    保持する(毎サイクルのデータ更新のたびに「新着」扱いにならないようにするため)。
    updated_atは逆に毎回「今」に更新する(ヘッダーのテレメトリ表示
    「最終更新: ...」用。published_atとは異なる目的のフィールド)。"""
    from .tool_builder import get_kind_category

    assets_dir = os.path.join(output_dir, "assets")
    manifest_path = os.path.join(assets_dir, MANIFEST_FILENAME)

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = []

    existing = next((e for e in manifest if e.get("slug") == slug), None)
    now = datetime.now(timezone.utc).isoformat()
    published_at = existing["published_at"] if existing else now

    entry = {
        "slug": slug,
        "niche": niche,
        "category": get_kind_category(kind) if kind else "その他",
        "kind": kind,
        "published_at": published_at,
        "updated_at": now,
    }
    # 同一slugのエントリに加え、dedupe_by_kind=True(ツール公開)の場合は
    # 同一kindの「旧slug」エントリ(URLスキーム移行前の名残)も取り除く。
    # 記事(publish_article)はdedupe_by_kind=Falseで呼ばれ、同一kindでも
    # 複数slug(タイムスタンプ違い)が同時に存在しうる設計を壊さない。
    if dedupe_by_kind and kind:
        manifest = [e for e in manifest if e.get("slug") != slug and e.get("kind") != kind]
    else:
        manifest = [e for e in manifest if e.get("slug") != slug]
    manifest.append(entry)

    os.makedirs(assets_dir, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest_path


_STATIC_PAGES = ["index.html", "about.html", "privacy.html"]


def _regenerate_sitemap(output_dir: str) -> str:
    """公開のたびにmanifest.jsonからdocs/sitemap.xmlを再生成する。
    検索エンジンのクロール対象を明示するため(robots.txtから参照される)。"""
    manifest_path = os.path.join(output_dir, "assets", MANIFEST_FILENAME)
    manifest = []
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    urls = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for page in _STATIC_PAGES:
        urls.append((f"{SITE_BASE_URL}/{page}", today))
    for entry in manifest:
        slug = entry.get("slug")
        if not slug:
            continue
        lastmod = str(entry.get("updated_at", entry.get("published_at", today)))[:10]
        urls.append((f"{SITE_BASE_URL}/{slug}.html", lastmod))

    body = "\n".join(
        f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>"
        for loc, lastmod in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )

    sitemap_path = os.path.join(output_dir, "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(xml)
    return sitemap_path


def _git_publish(paths: list) -> None:
    """GitHub Pages(mainブランチのoutput_dir配下)へ変更をpushする。
    HTMLファイルとdocs/assets/manifest.jsonの両方をまとめて1コミットにする
    (manifest.jsonだけadd漏れすると、ナビ(nav.js)がGitHub Pages上で
    参照するmanifest.jsonが更新されず、公開済みHTMLと不整合になるため)。"""
    try:
        subprocess.run(
            ["git", "-C", REPO_ROOT, "add"] + paths,
            check=True, capture_output=True, text=True,
        )
        commit = subprocess.run(
            ["git", "-C", REPO_ROOT, "commit", "-m", f"publish: {os.path.basename(paths[0])}"],
            capture_output=True, text=True,
        )
        if commit.returncode != 0:
            # gitの「差分無し」メッセージは状況により文言が変わる
            # (working tree全体がcleanな場合と、他に未ステージの変更がある場合とで異なる)
            no_op_markers = ("nothing to commit", "no changes added to commit")
            if any(marker in commit.stdout for marker in no_op_markers):
                return
            print(f"[publisher] git commit失敗: {commit.stdout}{commit.stderr}")
            return
        push = subprocess.run(
            ["git", "-C", REPO_ROOT, "push"],
            capture_output=True, text=True,
        )
        if push.returncode != 0:
            print(f"[publisher] git push失敗: {push.stderr}")
        else:
            print("[publisher] GitHub Pagesへpushしました")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[publisher] git操作に失敗したためpushをスキップしました: {e}")
