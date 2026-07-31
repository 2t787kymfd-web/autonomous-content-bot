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

from .ads import ADSENSE_HEAD_SNIPPET
from .theme import NAV_ASSETS_HEAD, PICO_CDN_LINK, SITE_CSS, site_footer, site_header

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def publish_article(title: str, content_markdown: str, output_dir: str, dry_run: bool, kind: str = "") -> str:
    """テキスト記事を簡易HTMLに包んで公開する。記事ごとに新しいslugを発行する
    (同一ニッチでも内容が変わるたびに新規ページとして品質ゲートの対象にするため)。"""
    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{PICO_CDN_LINK}
{ADSENSE_HEAD_SNIPPET}
{NAV_ASSETS_HEAD}
<style>{SITE_CSS}</style>
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
    slug = f"{slugify(title)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return _write(slug, html, output_dir, dry_run, niche=title, kind=kind)


def publish_tool(title: str, full_html: str, output_dir: str, dry_run: bool, kind: str = "") -> str:
    """tool_builder.py が組み立てた完成済みHTML(インタラクティブツール)をそのまま公開する。

    ツールは「同じニッチの最新レート/価格に更新する」のが目的であり、記事のような
    量産スパムのリスクは無い(むしろ更新されない方が実利用上の問題になる)ため、
    ニッチ名だけの安定したslug(タイムスタンプ無し)を使い、毎サイクル同じURLを
    上書き更新する。
    """
    slug = slugify(title)
    return _write(slug, full_html, output_dir, dry_run, niche=title, kind=kind)


def _write(slug: str, html: str, output_dir: str, dry_run: bool, niche: str = "", kind: str = "") -> str:
    path = os.path.join(output_dir, f"{slug}.html")

    if dry_run:
        print(f"[publisher] dry_run のため実際には書き出しません: {path}")
        return slug

    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[publisher] 公開しました: {path}")
    manifest_path = _upsert_manifest(slug, niche, kind, output_dir)
    _git_publish([path, manifest_path])
    return slug


MANIFEST_FILENAME = "manifest.json"


def _upsert_manifest(slug: str, niche: str, kind: str, output_dir: str) -> str:
    """ハンバーガーメニュー(nav.js)がカテゴリ別一覧を組み立てるための
    docs/assets/manifest.json を更新する。同一slugは新規追加せず上書きする
    (state.pyのcontent_corpusと同じupsertパターン)。published_atは初回公開時刻を
    保持する(毎サイクルのデータ更新のたびに「新着」扱いにならないようにするため)。"""
    from .tool_builder import get_kind_category

    assets_dir = os.path.join(output_dir, "assets")
    manifest_path = os.path.join(assets_dir, MANIFEST_FILENAME)

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = []

    existing = next((e for e in manifest if e.get("slug") == slug), None)
    published_at = existing["published_at"] if existing else datetime.now(timezone.utc).isoformat()

    entry = {
        "slug": slug,
        "niche": niche,
        "category": get_kind_category(kind) if kind else "その他",
        "kind": kind,
        "published_at": published_at,
    }
    manifest = [e for e in manifest if e.get("slug") != slug]
    manifest.append(entry)

    os.makedirs(assets_dir, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest_path


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
