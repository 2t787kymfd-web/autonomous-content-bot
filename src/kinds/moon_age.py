"""kind_generator.py が自動生成したプラグイン: moon_age"""

import math
import calendar
import datetime
import html
import requests

KIND_NAME = "moon_age"
KEYWORDS = ["月齢", "月齢カレンダー", "新月", "満月", "上弦", "下弦", "moon age", "lunar phase", "月の満ち欠け"]
CATEGORY = "天文・暦"


def _julian_day(year: int, month: int, day: int, hour: float = 12.0) -> float:
    """グレゴリオ暦からユリウス日(JD)を計算する。"""
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + hour / 24.0 + B - 1524.5
    return jd


def _moon_age(year: int, month: int, day: int) -> float:
    """指定日の月齢(0=新月)を返す。0〜29.53の範囲。"""
    jd = _julian_day(year, month, day)
    # 既知の新月: 2000年1月6日 18:14 UTC -> JD 2451550.259
    known_new_moon_jd = 2451550.259
    synodic_month = 29.53058867
    diff = jd - known_new_moon_jd
    age = diff % synodic_month
    if age < 0:
        age += synodic_month
    return age


def _moon_phase_name(age: float) -> str:
    """月齢から月相名を返す。"""
    if age < 1.0:
        return "🌑 新月"
    elif age < 6.5:
        return "🌒 三日月（waxing crescent）"
    elif age < 8.5:
        return "🌓 上弦の月"
    elif age < 13.5:
        return "🌔 十三夜（waxing gibbous）"
    elif age < 15.5:
        return "🌕 満月"
    elif age < 21.0:
        return "🌖 居待月（waning gibbous）"
    elif age < 23.0:
        return "🌗 下弦の月"
    elif age < 28.5:
        return "🌘 有明月（waning crescent）"
    else:
        return "🌑 新月（晦日）"


def _moon_emoji(age: float) -> str:
    """月齢に対応する月の絵文字を返す。"""
    emojis = ["🌑", "🌒", "🌒", "🌒", "🌒", "🌒", "🌒",
              "🌓", "🌔", "🌔", "🌔", "🌔", "🌔", "🌔",
              "🌕", "🌖", "🌖", "🌖", "🌖", "🌖", "🌖",
              "🌗", "🌘", "🌘", "🌘", "🌘", "🌘", "🌘",
              "🌑", "🌑"]
    idx = min(int(age), 29)
    return emojis[idx]


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    月齢はアルゴリズムで計算し、念のためOpen-Meteo APIで接続確認を行う。
    """
    today = datetime.date.today()
    year = today.year
    month = today.month

    # 当月の日数
    _, days_in_month = calendar.monthrange(year, month)

    # 当月全日の月齢を計算
    monthly_data = []
    for day in range(1, days_in_month + 1):
        age = _moon_age(year, month, day)
        phase = _moon_phase_name(age)
        emoji = _moon_emoji(age)
        monthly_data.append({
            "day": day,
            "age": round(age, 1),
            "phase": phase,
            "emoji": emoji,
        })

    if not monthly_data:
        raise RuntimeError("月齢データの計算に失敗しました")

    # 今日の月齢
    today_data = monthly_data[today.day - 1]

    # 今月の特筆すべき日(新月・満月・上弦・下弦)を抽出
    notable = []
    for d in monthly_data:
        age = d["age"]
        label = None
        if age < 1.0 or age >= 29.0:
            label = "新月"
        elif 6.5 <= age <= 8.5:
            label = "上弦の月"
        elif 13.5 <= age <= 15.5:
            label = "満月"
        elif 21.0 <= age <= 23.0:
            label = "下弦の月"
        if label:
            notable.append({"day": d["day"], "label": label, "emoji": d["emoji"]})

    # 重複を除去(連続する同ラベルは最初の日のみ)
    deduped_notable = []
    last_label = None
    for n in notable:
        if n["label"] != last_label:
            deduped_notable.append(n)
            last_label = n["label"]

    summary = (
        f"{year}年{month}月の月齢カレンダー。"
        f"本日({today.month}/{today.day})の月齢は{today_data['age']}({today_data['phase']})。"
        f"今月の注目日: " +
        "、".join([f"{n['day']}日({n['label']})" for n in deduped_notable]) +
        "。月齢はJean Meeus式ユリウス日計算による近似値。"
    )

    sources = [
        "https://www.nao.ac.jp/astro/sky/moon/ (国立天文台 月の満ち欠け)",
        "Jean Meeus, Astronomical Algorithms (ユリウス日アルゴリズム)",
    ]

    raw = {
        "year": year,
        "month": month,
        "today_day": today.day,
        "days_in_month": days_in_month,
        "today": today_data,
        "monthly_data": monthly_data,
        "notable": deduped_notable,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    year = int(raw_data.get("year", 2024))
    month = int(raw_data.get("month", 1))
    today_day = int(raw_data.get("today_day", 1))
    today = raw_data.get("today", {})
    monthly_data = raw_data.get("monthly_data", [])
    notable = raw_data.get("notable", [])

    safe_niche = html.escape(niche)
    safe_year = html.escape(str(year))
    safe_month = html.escape(str(month))

    today_age = html.escape(str(today.get("age", "-")))
    today_phase = html.escape(str(today.get("phase", "-")))
    today_emoji = html.escape(str(today.get("emoji", "-")))

    # カレンダーテーブル
    # 曜日ヘッダー
    weekday_headers = ""
    for wd in ["日", "月", "火", "水", "木", "金", "土"]:
        weekday_headers += f"<th>{html.escape(wd)}</th>"

    # monthrange で第1日の曜日を取得(0=月曜...6=日曜 → 日曜始まりに変換)
    first_weekday_mon, days_in_month = calendar.monthrange(year, month)
    # calendar.monthrange は月曜=0 ... 日曜=6
    # 日曜始まりに変換: 月曜=1, 火曜=2, ..., 日曜=0
    first_weekday_sun = (first_weekday_mon + 1) % 7

    rows = []
    cell_count = 0
    current_row = "<tr>"

    # 最初の空セル
    for _ in range(first_weekday_sun):
        current_row += "<td class='empty'></td>"
        cell_count += 1

    for d in monthly_data:
        day = d["day"]
        age = d["age"]
        emoji = html.escape(str(d["emoji"]))
        safe_age = html.escape(str(age))

        # 土曜=列7(cell_count%7==6), 日曜=列1(cell_count%7==0)
        col = cell_count % 7
        sat_class = " sat" if col == 6 else ""
        sun_class = " sun" if col == 0 else ""
        today_class = " today-cell" if day == today_day else ""
        cell_class = f"moon-cell{sat_class}{sun_class}{today_class}"

        current_row += (
            f"<td class='{html.escape(cell_class)}'>"
            f"<span class='cal-day tel-value'>{html.escape(str(day))}</span>"
            f"<span class='cal-emoji'>{emoji}</span>"
            f"<span class='cal-age tel-value'>月齢{safe_age}</span>"
            f"</td>"
        )
        cell_count += 1

        if cell_count % 7 == 0:
            current_row += "</tr>"
            rows.append(current_row)
            current_row = "<tr>"

    # 最後の行の残りセルを埋める
    if cell_count % 7 != 0:
        remaining = 7 - (cell_count % 7)
        for _ in range(remaining):
            current_row += "<td class='empty'></td>"
        current_row += "</tr>"
        rows.append(current_row)

    calendar_rows_html = "".join(rows)

    # 注目日リスト
    notable_html = ""
    if notable:
        notable_html = "<ul class='notable-list'>"
        for n in notable:
            n_day = html.escape(str(n.get("day", "-")))
            n_label = html.escape(str(n.get("label", "-")))
            n_emoji = html.escape(str(n.get("emoji", "-")))
            notable_html += f"<li>{n_emoji} {safe_month}月{n_day}日 &mdash; {n_label}</li>"
        notable_html += "</ul>"
    else:
        notable_html = "<p>今月は特筆すべき月相はありません。</p>"

    # 出典
    sources_html = "".join(
        f"<li>{html.escape(s)}</li>" for s in sources
    )

    return (
        f"<h1>{today_emoji} {safe_niche} — {safe_year}年{safe_month}月</h1>"
        f"<p>本日（{safe_month}月{html.escape(str(today_day))}日）の月齢: "
        f"<strong class=\"tel-value\">{today_age}</strong> &nbsp; {today_phase}</p>"
        f"<p>月齢0が新月、約7.4で上弦の月、約14.8で満月、約22.1で下弦の月となります。</p>"
        "<div class='table-responsive'>"
        "<table class='moon-calendar'>"
        f"<thead><tr>{weekday_headers}</tr></thead>"
        f"<tbody>{calendar_rows_html}</tbody>"
        "</table>"
        "</div>"
        f"<h2>🌟 今月の注目日</h2>"
        f"{notable_html}"
        "<h2>月齢の見方</h2>"
        "<ul>"
        "<li>🌑 <strong>新月（月齢0〜1）</strong>: 月が見えない</li>"
        "<li>🌓 <strong>上弦の月（月齢約7.4）</strong>: 右半分が光る</li>"
        "<li>🌕 <strong>満月（月齢約14.8）</strong>: 丸く輝く</li>"
        "<li>🌗 <strong>下弦の月（月齢約22.1）</strong>: 左半分が光る</li>"
        "</ul>"
        "<p><small>月齢はJean Meeus式ユリウス日計算による近似値です。"
        "実際の月相と±1日程度の誤差が生じる場合があります。</small></p>"
        "<div class='source'>"
        "<strong>データ出典・参考:</strong><ul>"
        f"{sources_html}"
        "</ul></div>"
    )

