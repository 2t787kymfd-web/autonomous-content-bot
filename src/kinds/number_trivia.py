"""kind_generator.py が自動生成したプラグイン: number_trivia"""

import requests
import html
import re
import math
from datetime import datetime, timezone, timedelta

KIND_NAME = "number_trivia"
KEYWORDS = ["数字", "豆知識", "雑学", "日付", "トリビア", "number", "trivia", "facts"]
CATEGORY = "国・地域・雑学"


def _jst_now():
    return datetime.now(timezone(timedelta(hours=9)))


def _is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.isqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def _prime_factors(n):
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def _math_facts(n):
    facts = []
    if _is_prime(n):
        facts.append(f"{n} は素数です。")
    else:
        pf = _prime_factors(n)
        facts.append(f"{n} の素因数分解: {' × '.join(str(x) for x in pf)}")
    if math.isqrt(n) ** 2 == n:
        facts.append(f"{n} は完全平方数です（{math.isqrt(n)}²）。")
    digits = [int(d) for d in str(n)]
    facts.append(f"各桁の和: {sum(digits)}")
    facts.append(f"約数の個数: {sum(1 for i in range(1, n+1) if n % i == 0) if n <= 10000 else '(大きすぎるため省略)'}")
    return facts


def _day_of_year(dt):
    return dt.timetuple().tm_yday


def _week_number(dt):
    return dt.isocalendar()[1]


def _fetch_wikipedia_on_this_day(month, day):
    """Wikipedia APIから「今日の出来事」を取得する"""
    url = f"https://ja.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "autonomous-content-bot/1.0"})
        resp.raise_for_status()
        data = resp.json()
        events = data.get("events", [])
        results = []
        # 新しい順に並べて最大5件
        events_sorted = sorted(events, key=lambda e: e.get("year", 0), reverse=True)
        for ev in events_sorted[:5]:
            year = ev.get("year", "")
            text = ev.get("text", "").strip()
            if text:
                results.append({"year": year, "text": text})
        return results
    except Exception:
        return []


def _fetch_wikipedia_on_this_day_en(month, day):
    """英語版Wikipedia APIから「今日の出来事」を取得する（日本語版フォールバック）"""
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "autonomous-content-bot/1.0"})
        resp.raise_for_status()
        data = resp.json()
        events = data.get("events", [])
        results = []
        events_sorted = sorted(events, key=lambda e: e.get("year", 0), reverse=True)
        for ev in events_sorted[:5]:
            year = ev.get("year", "")
            text = ev.get("text", "").strip()
            # 英語テキストを200文字でカット
            if text:
                results.append({"year": year, "text": text[:200]})
        return results
    except Exception:
        return []


def fetch(niche: str) -> tuple:
    now = _jst_now()
    month = now.month
    day = now.day
    year = now.year
    doy = _day_of_year(now)  # 年通算日
    week_no = _week_number(now)

    # Wikipedia「今日の出来事」取得
    events = _fetch_wikipedia_on_this_day(month, day)
    source_label = "ja.wikipedia.org"
    if not events:
        events = _fetch_wikipedia_on_this_day_en(month, day)
        source_label = "en.wikipedia.org"

    # 数学的豆知識（今日の「月」「日」「年通算日」について）
    math_day = _math_facts(day)
    math_doy = _math_facts(doy)

    # データが全くない場合は例外
    if not events and not math_day:
        raise RuntimeError(f"{month}月{day}日の豆知識データを取得できませんでした。")

    summary_parts = [f"{year}年{month}月{day}日（年通算{doy}日目、第{week_no}週）の豆知識。"]
    if events:
        summary_parts.append(f"今日の出来事: {events[0]['year']}年 - {events[0]['text'][:80]}")
    summary_parts.append(f"{day}の数学的性質: {'; '.join(math_day[:2])}")
    summary = " / ".join(summary_parts)

    sources = [f"https://{source_label}/ (Wikipedia - On This Day)"]

    raw = {
        "date": f"{year}-{month:02d}-{day:02d}",
        "month": month,
        "day": day,
        "year": year,
        "day_of_year": doy,
        "week_number": week_no,
        "weekday_ja": ["月", "火", "水", "木", "金", "土", "日"][now.weekday()],
        "days_left_in_year": (366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365) - doy,
        "math_facts_day": math_day,
        "math_facts_doy": math_doy,
        "events": events,
        "source_label": source_label,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    date_str = html.escape(str(raw_data.get("date", "")))
    month = raw_data.get("month", "")
    day = raw_data.get("day", "")
    year = raw_data.get("year", "")
    doy = raw_data.get("day_of_year", "")
    week_no = raw_data.get("week_number", "")
    weekday_ja = html.escape(str(raw_data.get("weekday_ja", "")))
    days_left = raw_data.get("days_left_in_year", "")
    math_day = raw_data.get("math_facts_day", [])
    math_doy = raw_data.get("math_facts_doy", [])
    events = raw_data.get("events", [])
    source_label = html.escape(str(raw_data.get("source_label", "wikipedia.org")))

    # ヘッダー
    out = []
    out.append(f'<h1>🔢 数字・日付の豆知識</h1>')
    out.append(f'<p>今日 <strong>{html.escape(str(year))}年{html.escape(str(month))}月{html.escape(str(day))}日（{weekday_ja}曜日）</strong> にまつわる数字のトリビアと歴史的出来事をまとめました。</p>')

    # 日付サマリーカード
    out.append('<h2>📅 今日の数字サマリー</h2>')
    out.append('<table>')
    out.append('<thead><tr><th>項目</th><th>値</th><th>メモ</th></tr></thead>')
    out.append('<tbody>')
    out.append(f'<tr><td>今日の日付</td><td class="tel-value">{html.escape(str(year))}年{html.escape(str(month))}月{html.escape(str(day))}日</td><td>{weekday_ja}曜日</td></tr>')
    out.append(f'<tr><td>年通算日</td><td class="tel-value">{html.escape(str(doy))} 日目</td><td class="tel-value">年末まであと {html.escape(str(days_left))} 日</td></tr>')
    out.append(f'<tr><td>週番号（ISO）</td><td class="tel-value">第 {html.escape(str(week_no))} 週</td><td>ISO 8601 基準</td></tr>')
    out.append('</tbody></table>')

    # 「日」の数学的豆知識
    out.append(f'<h2>🧮 「{html.escape(str(day))}」の数学的性質</h2>')
    if math_day:
        out.append('<ul>')
        for fact in math_day:
            out.append(f'<li>{html.escape(str(fact))}</li>')
        out.append('</ul>')
    else:
        out.append('<p>データなし</p>')

    # 「年通算日」の数学的豆知識
    out.append(f'<h2>🧮 「{html.escape(str(doy))}」（年通算日）の数学的性質</h2>')
    if math_doy:
        out.append('<ul>')
        for fact in math_doy:
            out.append(f'<li>{html.escape(str(fact))}</li>')
        out.append('</ul>')
    else:
        out.append('<p>データなし</p>')

    # 今日の出来事（Wikipedia）
    out.append(f'<h2>📖 {html.escape(str(month))}月{html.escape(str(day))}日 の歴史的出来事</h2>')
    if events:
        out.append('<table>')
        out.append('<thead><tr><th>西暦</th><th>出来事</th></tr></thead>')
        out.append('<tbody>')
        for ev in events:
            ev_year = html.escape(str(ev.get("year", "")))
            ev_text = html.escape(str(ev.get("text", "")))
            out.append(f'<tr><td class="tel-value">{ev_year}年</td><td>{ev_text}</td></tr>')
        out.append('</tbody></table>')
    else:
        out.append('<p>今日の出来事データを取得できませんでした。</p>')

    # 出典
    source_url = f"https://{raw_data.get('source_label', 'ja.wikipedia.org')}/"
    safe_url = source_url if source_url.startswith("https://") else "https://ja.wikipedia.org/"
    out.append(f'<div class="source">データ出典: <a href="{html.escape(safe_url)}" target="_blank" rel="noopener">{source_label} (Wikipedia On This Day API)</a> ／ 数学的性質はプログラムで計算</div>')

    return "\n".join(out)

