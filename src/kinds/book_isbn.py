"""kind_generator.py が自動生成したプラグイン: book_isbn"""

import requests
import json
import html
from datetime import datetime

KIND_NAME = "book_isbn"
KEYWORDS = ["書籍", "ISBN", "本", "図書", "openBD", "書誌情報", "出版"]
CATEGORY = "地理・開発者向け"

# 検索に使うサンプルISBNリスト(ジャンル別・人気書籍)
SAMPLE_ISBNS = [
    "9784065149232",  # 嫌われる勇気
    "9784101092058",  # 人間失格
    "9784167110123",  # 吾輩は猫である
    "9784062748895",  # 坊っちゃん
    "9784003101773",  # こころ
    "9784569825816",  # 影響力の武器
    "9784478025819",  # ゼロ秒思考
    "9784763136497",  # 夢をかなえるゾウ
    "9784344028685",  # コンビニ人間
    "9784101304519",  # 雪国
    "9784167110086",  # 羅生門
    "9784003110287",  # 銀河鉄道の夜
    "9784408536200",  # ハリー・ポッターと賢者の石
    "9784101181776",  # 伊豆の踊子
    "9784062753791",  # 容疑者Xの献身
]


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    # 複数のISBNを試して実データが取れるものを集める
    found_books = []

    # ISBNをバッチ取得(最大10件まとめて取得)
    isbn_batch = ",".join(SAMPLE_ISBNS[:10])
    url = f"https://api.openbd.jp/v1/get?isbn={isbn_batch}&pretty=0"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    for item in data:
        if item is None:
            continue
        summary_obj = item.get("summary", {})
        onix = item.get("onix", {})
        if not summary_obj:
            continue

        title = summary_obj.get("title", "")
        if not title:
            continue

        isbn = summary_obj.get("isbn", "")
        author = summary_obj.get("author", "")
        publisher = summary_obj.get("publisher", "")
        pubdate = summary_obj.get("pubdate", "")
        cover = summary_obj.get("cover", "")

        # 概要テキスト取得
        description = ""
        try:
            col_detail = onix.get("CollateralDetail", {})
            text_contents = col_detail.get("TextContent", [])
            for tc in text_contents:
                if tc.get("TextType") in ("02", "03", "04"):
                    description = tc.get("Text", "")
                    if description:
                        break
            if not description and text_contents:
                description = text_contents[0].get("Text", "")
        except Exception:
            description = ""

        # 価格取得
        price_str = ""
        try:
            product_supply = onix.get("ProductSupply", {})
            supply_detail = product_supply.get("SupplyDetail", {})
            prices = supply_detail.get("Price", [])
            if isinstance(prices, list) and prices:
                amount = prices[0].get("PriceAmount", "")
                if amount:
                    price_str = f"{amount}円"
            elif isinstance(prices, dict):
                amount = prices.get("PriceAmount", "")
                if amount:
                    price_str = f"{amount}円"
        except Exception:
            price_str = ""

        # 出版日フォーマット
        pubdate_fmt = ""
        if pubdate and len(pubdate) >= 6:
            try:
                y = pubdate[:4]
                m = pubdate[4:6]
                d = pubdate[6:8] if len(pubdate) >= 8 else ""
                pubdate_fmt = f"{y}年{m}月" + (f"{d}日" if d else "")
            except Exception:
                pubdate_fmt = pubdate

        found_books.append({
            "isbn": isbn,
            "title": title,
            "author": author,
            "publisher": publisher,
            "pubdate": pubdate_fmt,
            "cover": cover,
            "description": description[:200] if description else "",
            "price": price_str,
        })

    # 残りのISBNも試す
    if len(SAMPLE_ISBNS) > 10:
        isbn_batch2 = ",".join(SAMPLE_ISBNS[10:])
        try:
            url2 = f"https://api.openbd.jp/v1/get?isbn={isbn_batch2}&pretty=0"
            resp2 = requests.get(url2, timeout=15)
            resp2.raise_for_status()
            data2 = resp2.json()
            for item in data2:
                if item is None:
                    continue
                summary_obj = item.get("summary", {})
                onix = item.get("onix", {})
                if not summary_obj:
                    continue
                title = summary_obj.get("title", "")
                if not title:
                    continue
                isbn = summary_obj.get("isbn", "")
                author = summary_obj.get("author", "")
                publisher = summary_obj.get("publisher", "")
                pubdate = summary_obj.get("pubdate", "")
                cover = summary_obj.get("cover", "")
                description = ""
                try:
                    col_detail = onix.get("CollateralDetail", {})
                    text_contents = col_detail.get("TextContent", [])
                    for tc in text_contents:
                        if tc.get("TextType") in ("02", "03", "04"):
                            description = tc.get("Text", "")
                            if description:
                                break
                    if not description and text_contents:
                        description = text_contents[0].get("Text", "")
                except Exception:
                    description = ""
                price_str = ""
                try:
                    product_supply = onix.get("ProductSupply", {})
                    supply_detail = product_supply.get("SupplyDetail", {})
                    prices = supply_detail.get("Price", [])
                    if isinstance(prices, list) and prices:
                        amount = prices[0].get("PriceAmount", "")
                        if amount:
                            price_str = f"{amount}円"
                    elif isinstance(prices, dict):
                        amount = prices.get("PriceAmount", "")
                        if amount:
                            price_str = f"{amount}円"
                except Exception:
                    price_str = ""
                pubdate_fmt = ""
                if pubdate and len(pubdate) >= 6:
                    try:
                        y = pubdate[:4]
                        m = pubdate[4:6]
                        d = pubdate[6:8] if len(pubdate) >= 8 else ""
                        pubdate_fmt = f"{y}年{m}月" + (f"{d}日" if d else "")
                    except Exception:
                        pubdate_fmt = pubdate
                found_books.append({
                    "isbn": isbn,
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "pubdate": pubdate_fmt,
                    "cover": cover,
                    "description": description[:200] if description else "",
                    "price": price_str,
                })
        except Exception:
            pass

    if not found_books:
        raise RuntimeError("openBD APIから書籍データを1件も取得できませんでした")

    titles_sample = "、".join([b["title"] for b in found_books[:3]])
    summary = (
        f"openBD APIから{len(found_books)}件の書籍情報を取得しました。"
        f"収録例: {titles_sample} など。"
        f"タイトル・著者・出版社・出版日・価格・あらすじを掲載。"
    )
    sources = ["https://api.openbd.jp/ (openBD - 書誌情報・書影提供サービス)"]
    raw = {
        "books": found_books,
        "total": len(found_books),
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文のHTML断片を返す。"""
    books = raw_data.get("books", [])
    total = raw_data.get("total", 0)
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))

    source_text = html.escape(sources[0]) if sources else "openBD"

    rows = []
    for book in books:
        isbn = html.escape(str(book.get("isbn", "")))
        title = html.escape(str(book.get("title", "")))
        author = html.escape(str(book.get("author", "")))
        publisher = html.escape(str(book.get("publisher", "")))
        pubdate = html.escape(str(book.get("pubdate", "")))
        price = html.escape(str(book.get("price", "")))
        description = html.escape(str(book.get("description", "")))
        cover_raw = book.get("cover", "")
        # cover URLの安全確認
        cover_img = ""
        if cover_raw and cover_raw.startswith("https://"):
            cover_safe = html.escape(cover_raw)
            cover_img = f'<img src="{cover_safe}" alt="{title}" style="max-width:80px;max-height:110px;object-fit:contain;">'
        else:
            cover_img = '<span style="color:#aaa;font-size:0.8em;">書影なし</span>'

        # Amazonリンク(ISBNから)
        if isbn:
            amazon_url = f"https://www.amazon.co.jp/dp/{isbn}"
            amazon_link = f'<a href="{html.escape(amazon_url)}" target="_blank" rel="noopener">Amazon</a>'
        else:
            amazon_link = "-"

        # 説明文(長い場合は省略)
        desc_html = ""
        if description:
            desc_html = f'<div style="font-size:0.82em;color:#555;margin-top:4px;">{description}</div>'

        rows.append(
            f'<tr>'
            f'<td style="text-align:center;vertical-align:top;padding:6px;">{cover_img}</td>'
            f'<td style="vertical-align:top;padding:6px;">'
            f'<strong>{title}</strong>'
            f'<div style="font-size:0.88em;color:#333;margin-top:2px;">著者: {author if author else "不明"}</div>'
            f'<div style="font-size:0.85em;color:#555;">出版社: {publisher if publisher else "不明"} ／ 発行: {pubdate if pubdate else "不明"}</div>'
            f'<div style="font-size:0.85em;color:#c00;font-weight:bold;" class="tel-value">{price if price else ""}</div>'
            f'{desc_html}'
            f'</td>'
            f'<td style="text-align:center;vertical-align:top;padding:6px;white-space:nowrap;">'
            f'<div style="font-size:0.8em;color:#888;" class="tel-value">{isbn}</div>'
            f'<div style="margin-top:4px;">{amazon_link}</div>'
            f'</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows)

    html_out = (
        f'<h1>📚 {html.escape(niche)}</h1>'
        f'<p>'
        f'openBD APIを利用して日本の書籍情報をISBNコードから検索・表示します。'
        f'タイトル・著者・出版社・価格・あらすじを一覧で確認できます。'
        f'</p>'
        f'<div style="margin-bottom:12px;font-size:0.9em;color:#555;">'
        f'取得件数: <strong class="tel-value">{total}件</strong>　最終取得: {fetched_at}'
        f'</div>'
        f'<div style="overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead>'
        f'<tr style="background:#f0f0f0;">'
        f'<th style="padding:8px;text-align:center;width:90px;">書影</th>'
        f'<th style="padding:8px;text-align:left;">書籍情報</th>'
        f'<th style="padding:8px;text-align:center;width:120px;">ISBN / リンク</th>'
        f'</tr>'
        f'</thead>'
        f'<tbody>'
        f'{rows_html}'
        f'</tbody>'
        f'</table>'
        f'</div>'
        f'<div class="source">'
        f'データ出典: <a href="https://api.openbd.jp/" target="_blank" rel="noopener">openBD</a>'
        f'（出版社・取次が提供する書誌情報・書影を無償提供）'
        f'</div>'
    )
    return html_out

