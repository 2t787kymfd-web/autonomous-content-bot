"""kind_generator.py が自動生成したプラグイン: public_holidays"""

import requests
import html
from datetime import datetime

KIND_NAME = "public_holidays"
KEYWORDS = ["祝日", "祝祭日", "休日", "ホリデー", "holiday", "public holiday", "各国祝日", "国民の祝日"]
CATEGORY = "国・地域・雑学"

# ニッチ名から国コードを推定するマッピング
NICHE_TO_COUNTRY = {
    "日本": ("JP", "日本"),
    "アメリカ": ("US", "アメリカ合衆国"),
    "米国": ("US", "アメリカ合衆国"),
    "アメリカ合衆国": ("US", "アメリカ合衆国"),
    "イギリス": ("GB", "イギリス"),
    "英国": ("GB", "イギリス"),
    "フランス": ("FR", "フランス"),
    "ドイツ": ("DE", "ドイツ"),
    "イタリア": ("IT", "イタリア"),
    "スペイン": ("ES", "スペイン"),
    "カナダ": ("CA", "カナダ"),
    "オーストラリア": ("AU", "オーストラリア"),
    "中国": ("CN", "中国"),
    "韓国": ("KR", "韓国"),
    "インド": ("IN", "インド"),
    "ブラジル": ("BR", "ブラジル"),
    "ロシア": ("RU", "ロシア"),
    "メキシコ": ("MX", "メキシコ"),
    "オランダ": ("NL", "オランダ"),
    "ベルギー": ("BE", "ベルギー"),
    "スウェーデン": ("SE", "スウェーデン"),
    "ノルウェー": ("NO", "ノルウェー"),
    "デンマーク": ("DK", "デンマーク"),
    "フィンランド": ("FI", "フィンランド"),
    "スイス": ("CH", "スイス"),
    "オーストリア": ("AT", "オーストリア"),
    "ポルトガル": ("PT", "ポルトガル"),
    "ポーランド": ("PL", "ポーランド"),
    "チェコ": ("CZ", "チェコ"),
    "ハンガリー": ("HU", "ハンガリー"),
    "ギリシャ": ("GR", "ギリシャ"),
    "トルコ": ("TR", "トルコ"),
    "アルゼンチン": ("AR", "アルゼンチン"),
    "チリ": ("CL", "チリ"),
    "コロンビア": ("CO", "コロンビア"),
    "タイ": ("TH", "タイ"),
    "シンガポール": ("SG", "シンガポール"),
    "マレーシア": ("MY", "マレーシア"),
    "インドネシア": ("ID", "インドネシア"),
    "フィリピン": ("PH", "フィリピン"),
    "ベトナム": ("VN", "ベトナム"),
    "ニュージーランド": ("NZ", "ニュージーランド"),
    "南アフリカ": ("ZA", "南アフリカ"),
    "エジプト": ("EG", "エジプト"),
    "イスラエル": ("IL", "イスラエル"),
    "アイルランド": ("IE", "アイルランド"),
    "ウクライナ": ("UA", "ウクライナ"),
    "ルーマニア": ("RO", "ルーマニア"),
    "クロアチア": ("HR", "クロアチア"),
    "スロバキア": ("SK", "スロバキア"),
    "スロベニア": ("SI", "スロベニア"),
    "各国": ("JP", "日本"),
}


def _detect_country(niche: str) -> tuple:
    """ニッチ名から国コードと国名を推定する。"""
    for key, val in NICHE_TO_COUNTRY.items():
        if key in niche:
            return val
    return ("JP", "日本")


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    country_code, country_name = _detect_country(niche)
    year = datetime.now().year

    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data or not isinstance(data, list):
        raise RuntimeError(f"{country_name}({year}年)の祝日データが取得できませんでした。")

    today_str = datetime.now().strftime("%Y-%m-%d")
    upcoming = [h for h in data if h.get("date", "") >= today_str]
    next_holiday = upcoming[0] if upcoming else None

    summary_parts = [f"{country_name}の{year}年の祝日は全{len(data)}件です。"]
    if next_holiday:
        summary_parts.append(
            f"次の祝日は{next_holiday.get('date')}「{next_holiday.get('localName', next_holiday.get('name', ''))}」です。"
        )

    summary = "".join(summary_parts)
    sources = ["https://date.nager.at/ (Nager.Date - Public Holiday API)"]
    raw = {
        "country_code": country_code,
        "country_name": country_name,
        "year": year,
        "holidays": data,
        "today": today_str,
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    country_name = html.escape(str(raw_data.get("country_name", "")))
    country_code = html.escape(str(raw_data.get("country_code", "")))
    year = int(raw_data.get("year", datetime.now().year))
    holidays = raw_data.get("holidays", [])
    today_str = raw_data.get("today", datetime.now().strftime("%Y-%m-%d"))

    rows = []
    for h in holidays:
        date_val = str(h.get("date", ""))
        local_name = html.escape(str(h.get("localName", "")))
        name_en = html.escape(str(h.get("name", "")))
        types_list = h.get("types", [])
        h_type = html.escape(", ".join(types_list) if isinstance(types_list, list) else str(types_list))
        is_past = date_val < today_str
        is_today = date_val == today_str

        if is_today:
            row_class = ' class="today-row"'
            badge = ' <span class="badge today-badge">本日</span>'
        elif is_past:
            row_class = ' class="past-row"'
            badge = ''
        else:
            row_class = ''
            badge = ''

        safe_date = html.escape(date_val)
        rows.append(
            f'<tr{row_class}>'
            f'<td class="tel-value">{safe_date}{badge}</td>'
            f'<td><strong>{local_name}</strong></td>'
            f'<td>{name_en}</td>'
            f'<td>{h_type}</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows) if rows else '<tr><td colspan="4">データなし</td></tr>'
    total = len(holidays)
    remaining = sum(1 for h in holidays if str(h.get("date", "")) >= today_str)

    source_links = ""
    for s in sources:
        safe_s = html.escape(s)
        parts = s.split(" ", 1)
        url_part = parts[0]
        label_part = parts[1].strip("()") if len(parts) > 1 else url_part
        if url_part.startswith("https://"):
            source_links += f'<a href="{html.escape(url_part)}" target="_blank" rel="noopener">{html.escape(label_part)}</a> '
        else:
            source_links += safe_s + " "

    nager_url = f"https://date.nager.at/PublicHoliday/Country/{country_code}"

    html_out = (
        f'<h1>🗓️ {html.escape(niche)}</h1>'
        f'<p>{country_name}の<strong class="tel-value">{year}年</strong>の祝日一覧です。'
        f'全<strong class="tel-value">{total}</strong>件中、本日以降の祝日は<strong class="tel-value">{remaining}</strong>件です。</p>'
        '<div class="summary-box">'
        f'<span>対象国: <strong>{country_name}</strong> ({country_code})</span>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;<span>対象年: <strong class="tel-value">{year}年</strong></span>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;<span>祝日総数: <strong class="tel-value">{total}件</strong></span>'
        '</div>'
        '<table>'
        '<thead><tr>'
        '<th>日付</th>'
        '<th>祝日名(現地語)</th>'
        '<th>祝日名(英語)</th>'
        '<th>種別</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
        f'<p><a href="{html.escape(nager_url)}" target="_blank" rel="noopener">'
        f'Nager.Dateで{country_name}の祝日詳細を見る ↗</a></p>'
        f'<div class="source">データ出典: {source_links}</div>'
    )
    return html_out

