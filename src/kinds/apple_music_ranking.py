"""kind_generator.py が自動生成したプラグイン: apple_music_ranking"""

import requests
import json
import html
from datetime import datetime

KIND_NAME = "apple_music_ranking"
KEYWORDS = ["Apple Music", "ランキング", "トップソング", "音楽チャート", "アップルミュージック", "top songs", "music ranking"]
CATEGORY = "エンタメ"

# ニッチ名から国コードを推定するマッピング
COUNTRY_MAP = {
    "日本": "jp",
    "japan": "jp",
    "アメリカ": "us",
    "usa": "us",
    "us": "us",
    "韓国": "kr",
    "korea": "kr",
    "中国": "cn",
    "china": "cn",
    "イギリス": "gb",
    "uk": "gb",
    "フランス": "fr",
    "france": "fr",
    "ドイツ": "de",
    "germany": "de",
    "オーストラリア": "au",
    "australia": "au",
    "カナダ": "ca",
    "canada": "ca",
    "ブラジル": "br",
    "brazil": "br",
    "インド": "in",
    "india": "in",
    "台湾": "tw",
    "taiwan": "tw",
    "タイ": "th",
    "thailand": "th",
}

COUNTRY_LABEL = {
    "jp": "日本",
    "us": "アメリカ",
    "kr": "韓国",
    "cn": "中国",
    "gb": "イギリス",
    "fr": "フランス",
    "de": "ドイツ",
    "au": "オーストラリア",
    "ca": "カナダ",
    "br": "ブラジル",
    "in": "インド",
    "tw": "台湾",
    "th": "タイ",
}

def _detect_country(niche: str) -> str:
    """ニッチ名から国コードを検出する。デフォルトはjp。"""
    niche_lower = niche.lower()
    for key, code in COUNTRY_MAP.items():
        if key.lower() in niche_lower:
            return code
    return "jp"

def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    country_code = _detect_country(niche)
    country_label = COUNTRY_LABEL.get(country_code, country_code.upper())

    url = f"https://rss.marketingtools.apple.com/api/v2/{country_code}/music/most-played/25/songs.json"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    feed = data.get("feed", {})
    results = feed.get("results", [])

    if not results:
        raise RuntimeError(f"Apple Music ({country_label}) のトップソングデータが取得できませんでした。")

    songs = []
    for i, item in enumerate(results[:25], start=1):
        name = item.get("name", "")
        artist_name = item.get("artistName", "")
        artwork_url = item.get("artworkUrl100", "")
        # アートワークURLをhttpsで始まるものだけ採用
        if not artwork_url.startswith("https://"):
            artwork_url = ""
        songs.append({
            "rank": i,
            "name": name,
            "artist": artist_name,
            "artwork_url": artwork_url,
        })

    updated = feed.get("updated", "")
    summary = (
        f"Apple Music {country_label}トップソングランキング: "
        f"1位は「{songs[0]['name']}」({songs[0]['artist']})。"
        f" 全{len(songs)}曲を取得。更新日時: {updated}"
    )
    sources = [
        f"https://rss.marketingtools.apple.com/api/v2/{country_code}/music/most-played/25/songs.json (Apple Music Marketing Tools RSS Feed)"
    ]
    raw = {
        "country_code": country_code,
        "country_label": country_label,
        "songs": songs,
        "updated": updated,
    }
    return summary, sources, raw

def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    country_label = html.escape(str(raw_data.get("country_label", "")))
    updated_raw = raw_data.get("updated", "")
    songs = raw_data.get("songs", [])

    # 更新日時の整形
    try:
        dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        updated_str = dt.strftime("%Y年%m月%d日 %H:%M UTC")
    except Exception:
        updated_str = html.escape(str(updated_raw)) if updated_raw else "不明"

    rows = []
    for song in songs:
        rank = int(song.get("rank", 0))
        name = html.escape(str(song.get("name", "")))
        artist = html.escape(str(song.get("artist", "")))
        artwork_url = song.get("artwork_url", "")

        # アートワーク: httpsで始まる場合のみ表示
        if artwork_url.startswith("https://"):
            safe_artwork = html.escape(artwork_url)
            artwork_tag = f'<img src="{safe_artwork}" alt="{name}" width="60" height="60" loading="lazy" style="border-radius:6px;">'
        else:
            artwork_tag = '<span style="display:inline-block;width:60px;height:60px;background:#333;border-radius:6px;"></span>'

        # 1〜3位は強調
        if rank == 1:
            rank_badge = f'<span style="font-size:1.4em;">🥇</span> <strong class="tel-value">{rank}</strong>'
        elif rank == 2:
            rank_badge = f'<span style="font-size:1.4em;">🥈</span> <strong class="tel-value">{rank}</strong>'
        elif rank == 3:
            rank_badge = f'<span style="font-size:1.4em;">🥉</span> <strong class="tel-value">{rank}</strong>'
        else:
            rank_badge = f'<strong class="tel-value">{rank}</strong>'

        rows.append(
            f'<tr>'
            f'<td style="text-align:center;padding:8px 12px;white-space:nowrap;">{rank_badge}</td>'
            f'<td style="text-align:center;padding:8px;">{artwork_tag}</td>'
            f'<td style="padding:8px 12px;"><strong>{name}</strong></td>'
            f'<td style="padding:8px 12px;color:#aaa;">{artist}</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows)

    source_list = "".join(
        f'<li><a href="{html.escape(s.split(" ")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a></li>'
        for s in sources
    )

    return (
        f'<h1>🎵 Apple Music {country_label} トップソングランキング</h1>'
        f'<p>Apple Music 公式フィードによる{country_label}の最新トップ25曲ランキングです。'
        f'（更新: {updated_str}）</p>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead>'
        '<tr style="border-bottom:2px solid #555;">'
        '<th style="padding:8px 12px;text-align:center;">順位</th>'
        '<th style="padding:8px;text-align:center;">ジャケット</th>'
        '<th style="padding:8px 12px;text-align:left;">曲名</th>'
        '<th style="padding:8px 12px;text-align:left;">アーティスト</th>'
        '</tr>'
        '</thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
        '</div>'
        '<p style="font-size:0.85em;color:#888;margin-top:12px;">'
        '※ジャケット画像・ランキングデータはApple Inc.が提供するRSSフィードから取得しています。'
        '楽曲の再生・購入はApple Musicアプリまたは公式サイトをご利用ください。'
        '</p>'
        '<div class="source">'
        f'<ul>{source_list}</ul>'
        '</div>'
    )

