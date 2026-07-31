"""kind_generator.py が自動生成したプラグイン: today_in_history"""

import requests
import html
import datetime
import re

KIND_NAME = "today_in_history"
KEYWORDS = ["今日は何の日", "歴史", "出来事", "記念日", "on this day", "today in history"]
CATEGORY = "国・地域・雑学"


def fetch(niche: str) -> tuple:
    """
    Wikimedia On This Day Feed (英語版) から本日の歴史的出来事・記念日を取得する。
    月日は必ず2桁ゼロ埋めで渡す。
    """
    today = datetime.date.today()
    month = today.strftime("%m")
    day = today.strftime("%d")

    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{month}/{day}"
    headers = {
        "User-Agent": "autonomous-content-bot/1.0 (educational; contact via github)"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # events: 歴史的出来事
    events = data.get("events", [])
    # holidays: 祝日・記念日
    holidays = data.get("holidays", [])
    # births: 誕生日
    births = data.get("births", [])
    # deaths: 命日
    deaths = data.get("deaths", [])

    if not events and not holidays and not births and not deaths:
        raise RuntimeError(f"今日({month}/{day})の出来事データが1件も取得できませんでした。")

    # 代表的な出来事を最大10件
    selected_events = []
    for e in events[:10]:
        year = e.get("year", "")
        text = e.get("text", "")
        pages = e.get("pages", [])
        page_url = ""
        page_title = ""
        if pages:
            p = pages[0]
            page_url = p.get("content_urls", {}).get("desktop", {}).get("page", "")
            page_title = p.get("title", "")
        selected_events.append({
            "year": year,
            "text": text,
            "page_url": page_url,
            "page_title": page_title,
        })

    # 記念日を最大5件
    selected_holidays = []
    for h in holidays[:5]:
        text = h.get("text", "")
        pages = h.get("pages", [])
        page_url = ""
        if pages:
            page_url = pages[0].get("content_urls", {}).get("desktop", {}).get("page", "")
        selected_holidays.append({"text": text, "page_url": page_url})

    # 誕生日を最大5件
    selected_births = []
    for b in births[:5]:
        year = b.get("year", "")
        text = b.get("text", "")
        selected_births.append({"year": year, "text": text})

    # 命日を最大5件
    selected_deaths = []
    for d in deaths[:5]:
        year = d.get("year", "")
        text = d.get("text", "")
        selected_deaths.append({"year": year, "text": text})

    summary = (
        f"{month}月{day}日の今日は何の日: "
        f"歴史的出来事{len(events)}件、記念日{len(holidays)}件、"
        f"誕生日{len(births)}件、命日{len(deaths)}件が記録されています。"
        f"代表的な出来事: {events[0].get('text', '') if events else '(なし)'}"
    )

    sources = [
        f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{month}/{day} (Wikimedia On This Day Feed)"
    ]

    raw = {
        "month": month,
        "day": day,
        "events": selected_events,
        "holidays": selected_holidays,
        "births": selected_births,
        "deaths": selected_deaths,
        "events_total": len(events),
        "holidays_total": len(holidays),
    }

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    month = html.escape(str(raw_data.get("month", "")))
    day = html.escape(str(raw_data.get("day", "")))
    events = raw_data.get("events", [])
    holidays = raw_data.get("holidays", [])
    births = raw_data.get("births", [])
    deaths = raw_data.get("deaths", [])

    # ヘッダー
    out = [
        f'<h1>\U0001f4da {month}月{day}日は何の日？</h1>',
        f'<p>{html.escape(str(int(month)))}月{html.escape(str(int(day)))}日に起きた歴史的出来事や記念日を、'
        f'Wikimedia(Wikipedia英語版)のデータからご紹介します。</p>',
    ]

    # 記念日・祝日セクション
    if holidays:
        out.append('<h2>\U0001f389 記念日・祝日</h2>')
        out.append('<ul>')
        for h in holidays:
            text = html.escape(str(h.get("text", "")))
            page_url = h.get("page_url", "")
            safe_url = page_url if isinstance(page_url, str) and page_url.startswith("https://") else ""
            if safe_url:
                out.append(f'<li><a href="{html.escape(safe_url)}" target="_blank" rel="noopener">{text}</a></li>')
            else:
                out.append(f'<li>{text}</li>')
        out.append('</ul>')

    # 歴史的出来事セクション
    if events:
        out.append('<h2>\U0001f4dc 歴史的出来事</h2>')
        out.append('<div class="table-wrap"><table>')
        out.append('<thead><tr><th>年</th><th>出来事</th><th>詳細</th></tr></thead>')
        out.append('<tbody>')
        for e in events:
            year = html.escape(str(e.get("year", "")))
            text = html.escape(str(e.get("text", "")))
            page_url = e.get("page_url", "")
            safe_url = page_url if isinstance(page_url, str) and page_url.startswith("https://") else ""
            page_title = html.escape(str(e.get("page_title", "")))
            if safe_url:
                link_cell = f'<a href="{html.escape(safe_url)}" target="_blank" rel="noopener">{page_title if page_title else "Wikipedia"}</a>'
            else:
                link_cell = "-"
            out.append(f'<tr><td class="tel-value">{year}</td><td>{text}</td><td>{link_cell}</td></tr>')
        out.append('</tbody></table></div>')

    # 誕生日セクション
    if births:
        out.append('<h2>\U0001f382 この日生まれた人物</h2>')
        out.append('<ul>')
        for b in births:
            year = html.escape(str(b.get("year", "")))
            text = html.escape(str(b.get("text", "")))
            out.append(f'<li><span class="year-badge tel-value">{year}年</span> {text}</li>')
        out.append('</ul>')

    # 命日セクション
    if deaths:
        out.append('<h2>\U0001f54a\ufe0f この日亡くなった人物</h2>')
        out.append('<ul>')
        for d in deaths:
            year = html.escape(str(d.get("year", "")))
            text = html.escape(str(d.get("text", "")))
            out.append(f'<li><span class="year-badge tel-value">{year}年</span> {text}</li>')
        out.append('</ul>')

    # 出典
    safe_sources = []
    for s in sources:
        safe_sources.append(html.escape(str(s)))
    out.append('<div class="source">データ出典: ' + " / ".join(safe_sources) + '</div>')

    return "\n".join(out)

