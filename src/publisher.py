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
from datetime import datetime, timezone


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def publish_article(title: str, content_markdown: str, output_dir: str, dry_run: bool) -> str:
    """テキスト記事を簡易HTMLに包んで公開する。"""
    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
</head>
<body>
<pre>{content_markdown}</pre>
</body>
</html>
"""
    return _write(title, html, output_dir, dry_run)


def publish_tool(title: str, full_html: str, output_dir: str, dry_run: bool) -> str:
    """tool_builder.py が組み立てた完成済みHTML(インタラクティブツール)をそのまま公開する。"""
    return _write(title, full_html, output_dir, dry_run)


def _write(title: str, html: str, output_dir: str, dry_run: bool) -> str:
    slug = f"{slugify(title)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    path = os.path.join(output_dir, f"{slug}.html")

    if dry_run:
        print(f"[publisher] dry_run のため実際には書き出しません: {path}")
        return slug

    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[publisher] 公開しました: {path}")
    # TODO: ここで git push / デプロイAPI呼び出しなどを追加する
    return slug
