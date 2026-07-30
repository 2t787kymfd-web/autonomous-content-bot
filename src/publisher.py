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

import os
import re
import subprocess
from datetime import datetime, timezone

from .ads import ADSENSE_HEAD_SNIPPET
from .theme import SITE_CSS, site_footer, site_header

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def publish_article(title: str, content_markdown: str, output_dir: str, dry_run: bool) -> str:
    """テキスト記事を簡易HTMLに包んで公開する。記事ごとに新しいslugを発行する
    (同一ニッチでも内容が変わるたびに新規ページとして品質ゲートの対象にするため)。"""
    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{ADSENSE_HEAD_SNIPPET}
<style>{SITE_CSS}</style>
</head>
<body>
{site_header()}
<main>
  <div class="card">
  <h1>📰 {title}</h1>
  <pre style="white-space: pre-wrap; font-family: inherit;">{content_markdown}</pre>
  </div>
</main>
{site_footer()}
</body>
</html>
"""
    slug = f"{slugify(title)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return _write(slug, html, output_dir, dry_run)


def publish_tool(title: str, full_html: str, output_dir: str, dry_run: bool) -> str:
    """tool_builder.py が組み立てた完成済みHTML(インタラクティブツール)をそのまま公開する。

    ツールは「同じニッチの最新レート/価格に更新する」のが目的であり、記事のような
    量産スパムのリスクは無い(むしろ更新されない方が実利用上の問題になる)ため、
    ニッチ名だけの安定したslug(タイムスタンプ無し)を使い、毎サイクル同じURLを
    上書き更新する。
    """
    slug = slugify(title)
    return _write(slug, full_html, output_dir, dry_run)


def _write(slug: str, html: str, output_dir: str, dry_run: bool) -> str:
    path = os.path.join(output_dir, f"{slug}.html")

    if dry_run:
        print(f"[publisher] dry_run のため実際には書き出しません: {path}")
        return slug

    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[publisher] 公開しました: {path}")
    _git_publish(path)
    return slug


def _git_publish(path: str) -> None:
    """GitHub Pages(mainブランチのoutput_dir配下)へ変更をpushする。"""
    try:
        subprocess.run(
            ["git", "-C", REPO_ROOT, "add", path],
            check=True, capture_output=True, text=True,
        )
        commit = subprocess.run(
            ["git", "-C", REPO_ROOT, "commit", "-m", f"publish: {os.path.basename(path)}"],
            capture_output=True, text=True,
        )
        if commit.returncode != 0:
            if "nothing to commit" in commit.stdout:
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
