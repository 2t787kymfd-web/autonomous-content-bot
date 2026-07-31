"""kind_generator.py が自動生成したプラグイン: world_clock"""

import requests
import html
from datetime import datetime

KIND_NAME = "world_clock"
KEYWORDS = ["世界時計", "world clock", "現在時刻", "タイムゾーン", "timezone", "都市時刻", "時差"]
CATEGORY = "天文・暦"

# 主要都市とタイムゾーン識別子のマッピング
CITY_TIMEZONES = [
    ("東京", "Asia/Tokyo"),
    ("ニューヨーク", "America/New_York"),
    ("ロンドン", "Europe/London"),
    ("パリ", "Europe/Paris"),
    ("ドバイ", "Asia/Dubai"),
    ("シンガポール", "Asia/Singapore"),
    ("シドニー", "Australia/Sydney"),
    ("ロサンゼルス", "America/Los_Angeles"),
    ("上海", "Asia/Shanghai"),
    ("ムンバイ", "Asia/Kolkata"),
]


def _fetch_worldtimeapi(tz: str) -> dict:
    """worldtimeapi.org からタイムゾーン情報を取得する。"""
    url = f"https://worldtimeapi.org/api/timezone/{tz}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data


def _fetch_timeapi_io(tz: str) -> dict:
    """timeapi.io からタイムゾーン情報を取得する(代替)。"""
    url = f"https://timeapi.io/api/Time/current/zone?timeZone={tz}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data


def _parse_worldtimeapi(data: dict) -> str:
    """worldtimeapi.org レスポンスから日時文字列を抽出する。"""
    # datetime フィールド例: "2024-01-15T14:30:45.123456+09:00"
    dt_str = data.get("datetime", "")
    if not dt_str:
        raise ValueError("datetimeフィールドが見つかりません")
    # 小数秒を除去して変換
    dt_str_clean = dt_str[:19]  # "2024-01-15T14:30:45"
    dt = datetime.strptime(dt_str_clean, "%Y-%m-%dT%H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse_timeapi_io(data: dict) -> str:
    """timeapi.io レスポンスから日時文字列を抽出する。"""
    # year, month, day, hour, minute, seconds フィールドがある
    year = data.get("year")
    month = data.get("month")
    day = data.get("day")
    hour = data.get("hour")
    minute = data.get("minute")
    seconds = data.get("seconds")
    if None in (year, month, day, hour, minute, seconds):
        raise ValueError("日時フィールドが不完全です")
    dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(seconds))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fetch(niche: str) -> tuple:
    """
    researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    主要都市の現在時刻をworldtimeapi.orgまたはtimeapi.ioから取得する。
    """
    results = []
    used_source = None

    for city_name, tz in CITY_TIMEZONES:
        dt_str = None
        # まず worldtimeapi.org を試みる
        try:
            data = _fetch_worldtimeapi(tz)
            dt_str = _parse_worldtimeapi(data)
            if used_source is None:
                used_source = "worldtimeapi"
        except Exception:
            pass

        # 失敗した場合は timeapi.io を試みる
        if dt_str is None:
            try:
                data = _fetch_timeapi_io(tz)
                dt_str = _parse_timeapi_io(data)
                if used_source is None:
                    used_source = "timeapi_io"
            except Exception:
                pass

        if dt_str is not None:
            results.append({
                "city": city_name,
                "timezone": tz,
                "datetime": dt_str,
            })

    if not results:
        raise RuntimeError(
            "全ての情報源(worldtimeapi.org, timeapi.io)からのデータ取得に失敗しました。"
        )

    # サマリー生成(東京時刻を基準に)
    tokyo_entry = next((r for r in results if r["city"] == "東京"), results[0])
    summary = (
        f"主要{len(results)}都市の現在時刻を取得しました。"
        f"東京の現在時刻: {tokyo_entry['datetime']} (JST)"
    )

    sources = [
        "https://worldtimeapi.org/ (WorldTimeAPI - 無料タイムゾーンAPI)",
        "https://timeapi.io/ (TimeAPI.io - 無料タイムゾーンAPI)",
    ]

    raw = {
        "cities": results,
        "fetched_count": len(results),
        "source": used_source,
    }

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """
    tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    """
    cities = raw_data.get("cities", [])
    fetched_count = raw_data.get("fetched_count", 0)

    safe_niche = html.escape(str(niche))

    rows = ""
    for entry in cities:
        safe_city = html.escape(str(entry.get("city", "")))
        safe_tz = html.escape(str(entry.get("timezone", "")))
        safe_dt = html.escape(str(entry.get("datetime", "")))
        rows += (
            f"<tr>"
            f"<td>{safe_city}</td>"
            f"<td>{safe_tz}</td>"
            f"<td><strong>{safe_dt}</strong></td>"
            f"</tr>"
        )

    if not rows:
        rows = "<tr><td colspan=\"3\">データを取得できませんでした。</td></tr>"

    source_items = "".join(
        f"<li><a href=\"{html.escape(s.split(' (')[0])}\" target=\"_blank\" rel=\"noopener\">{html.escape(s)}</a></li>"
        for s in sources
        if s.split(" (")[0].startswith("https://")
    )

    html_fragment = (
        f"<h1>\U0001f555 {safe_niche}</h1>"
        f"<p>世界{html.escape(str(fetched_count))}都市の現在時刻を表示しています。"
        f"データは取得時点のものです。時刻は各都市のローカルタイムです。</p>"
        "<table>"
        "<thead>"
        "<tr><th>都市</th><th>タイムゾーン</th><th>現在時刻</th></tr>"
        "</thead>"
        "<tbody>"
        f"{rows}"
        "</tbody>"
        "</table>"
        "<div class=\"source\">"
        "<p>\u30c7\u30fc\u30bf\u51fa\u5178:</p>"
        f"<ul>{source_items}</ul>"
        "</div>"
    )

    return html_fragment

