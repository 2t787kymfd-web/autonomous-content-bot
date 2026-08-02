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


def _fetch_country_songs(country_code: str) -> tuple:
    """1カ国分のトップ25曲を取得する。戻り値: (songs: list, updated: str)"""
    url = f"https://rss.marketingtools.apple.com/api/v2/{country_code}/music/most-played/25/songs.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    feed = data.get("feed", {})
    results = feed.get("results", [])

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
    return songs, feed.get("updated", "")


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    Apple側のRSSフィードにCORSヘッダが無くブラウザから直接fetchできないため
    (postal_code/public_holidays等と違いライブ再取得方式が使えない)、
    対応する全カ国分をここでまとめて取得してraw_dataに埋め込み、
    build_html()側でJSに埋め込んでクライアントサイドの国切り替えに使う。
    一部の国の取得に失敗しても、他の国が1つでも取れていれば継続する。"""
    default_country = _detect_country(niche)

    countries_data = {}
    for code in COUNTRY_LABEL:
        try:
            songs, updated = _fetch_country_songs(code)
            if songs:
                countries_data[code] = {"songs": songs, "updated": updated}
        except Exception as e:
            print(f"[apple_music_ranking] {code} の取得に失敗: {e}")

    if not countries_data:
        raise RuntimeError("Apple Musicのトップソングデータが1件も取得できませんでした。")

    if default_country not in countries_data:
        default_country = next(iter(countries_data))
    default_label = COUNTRY_LABEL.get(default_country, default_country.upper())
    top = countries_data[default_country]["songs"]

    summary = (
        f"Apple Music {default_label}トップソングランキング: "
        f"1位は「{top[0]['name']}」({top[0]['artist']})。"
        f" 対応{len(countries_data)}カ国分のランキングを取得。"
    )
    sources = [
        "https://rss.marketingtools.apple.com/api/v2/ (Apple Music Marketing Tools RSS Feed)"
    ]
    raw = {
        "default_country": default_country,
        "countries": countries_data,
    }
    return summary, sources, raw

def _format_updated(updated_raw: str) -> str:
    try:
        dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        return dt.strftime("%Y年%m月%d日 %H:%M UTC")
    except Exception:
        return html.escape(str(updated_raw)) if updated_raw else "不明"


def _rank_badge(rank: int) -> str:
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank)
    if medal:
        return f'<span style="font-size:1.4em;">{medal}</span> <strong class="tel-value">{rank}</strong>'
    return f'<strong class="tel-value">{rank}</strong>'


def _render_rows(songs: list) -> str:
    rows = []
    for song in songs:
        rank = int(song.get("rank", 0))
        name = html.escape(str(song.get("name", "")))
        artist = html.escape(str(song.get("artist", "")))
        artwork_url = song.get("artwork_url", "")

        if artwork_url.startswith("https://"):
            safe_artwork = html.escape(artwork_url)
            artwork_tag = f'<img src="{safe_artwork}" alt="{name}" width="60" height="60" loading="lazy" style="border-radius:6px;">'
        else:
            artwork_tag = '<span style="display:inline-block;width:60px;height:60px;background:#333;border-radius:6px;"></span>'

        rows.append(
            f'<tr>'
            f'<td style="text-align:center;padding:8px 12px;white-space:nowrap;">{_rank_badge(rank)}</td>'
            f'<td style="text-align:center;padding:8px;">{artwork_tag}</td>'
            f'<td style="padding:8px 12px;"><strong>{name}</strong></td>'
            f'<td style="padding:8px 12px;color:#aaa;">{artist}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    初期表示(デフォルト国)はサーバー側で静的HTMLとして描画し(JS非実行の
    クローラーにも内容が見えるようにするため)、国の切り替えだけはJSで
    行う。Apple側のフィードにCORSヘッダが無くブラウザから直接fetchできない
    ため、対応全カ国分のデータをこのページのJSへ埋め込み、切り替え時は
    ライブ再取得ではなく埋め込み済みデータからテーブルを再構築する。"""
    countries = raw_data.get("countries", {})
    default_country = raw_data.get("default_country", "jp")
    if default_country not in countries and countries:
        default_country = next(iter(countries))

    default_label = html.escape(COUNTRY_LABEL.get(default_country, default_country.upper()))
    default_songs = countries.get(default_country, {}).get("songs", [])
    default_updated = _format_updated(countries.get(default_country, {}).get("updated", ""))

    option_html = "".join(
        f'<option value="{html.escape(code)}"{" selected" if code == default_country else ""}>'
        f'{html.escape(COUNTRY_LABEL.get(code, code.upper()))}</option>'
        for code in countries
    )

    # </script>でHTMLパースが途切れないよう、埋め込みJSON内の"</"はエスケープする
    countries_json = json.dumps(countries, ensure_ascii=False).replace("</", "<\\/")
    labels_json = json.dumps(COUNTRY_LABEL, ensure_ascii=False).replace("</", "<\\/")

    source_list = "".join(
        f'<li><a href="{html.escape(s.split(" ")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a></li>'
        for s in sources
    )

    return (
        f'<h1>🎵 Apple Music <span id="amr-country-heading">{default_label}</span> トップソングランキング</h1>'
        f'<p>Apple Music 公式フィードによる各国の最新トップ25曲ランキングです。'
        f'（更新: <span id="amr-updated">{default_updated}</span>）</p>'
        '<div class="tool-section">'
        '<h2>国を選んで表示</h2>'
        '<select id="amr-country-select" style="padding:8px 12px;font-size:1rem;'
        'border:1px solid #ccc;border-radius:4px;">'
        f'{option_html}'
        '</select>'
        '</div>'
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
        f'<tbody id="amr-tbody">{_render_rows(default_songs)}</tbody>'
        '</table>'
        '</div>'
        '<p style="font-size:0.85em;color:#888;margin-top:12px;">'
        '※ジャケット画像・ランキングデータはApple Inc.が提供するRSSフィードから取得しています。'
        '楽曲の再生・購入はApple Musicアプリまたは公式サイトをご利用ください。'
        '</p>'
        '<div class="source">'
        f'<ul>{source_list}</ul>'
        '</div>'
        '<script>'
        f'var AMR_DATA = {countries_json};'
        f'var AMR_LABELS = {labels_json};'
        'function amrEscHtml(s) {'
        '  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")'
        '    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");'
        '}'
        'function amrRankBadge(rank) {'
        '  var medal = {1:"🥇",2:"🥈",3:"🥉"}[rank];'
        '  var head = medal'
        '    ? "<span style=\\"font-size:1.4em;\\">" + medal + "</span> "'
        '    : "";'
        '  return head + "<strong class=\\"tel-value\\">" + rank + "</strong>";'
        '}'
        'function amrFormatUpdated(raw) {'
        '  if (!raw) return "不明";'
        '  var d = new Date(raw);'
        '  if (isNaN(d.getTime())) return amrEscHtml(raw);'
        '  return d.toLocaleString("ja-JP", {'
        '    year: "numeric", month: "2-digit", day: "2-digit",'
        '    hour: "2-digit", minute: "2-digit", timeZone: "UTC"'
        '  }) + " UTC";'
        '}'
        'function amrRenderCountry(code) {'
        '  var data = AMR_DATA[code];'
        '  if (!data) return;'
        '  var tbody = document.getElementById("amr-tbody");'
        '  var rows = "";'
        '  data.songs.forEach(function (song) {'
        '    var name = amrEscHtml(song.name || "");'
        '    var artist = amrEscHtml(song.artist || "");'
        '    var artwork = song.artwork_url || "";'
        '    var artworkTag = artwork.indexOf("https://") === 0'
        '      ? "<img src=\\"" + amrEscHtml(artwork) + "\\" alt=\\"" + name +'
        '        "\\" width=60 height=60 loading=lazy style=\\"border-radius:6px;\\">"'
        '      : "<span style=\\"display:inline-block;width:60px;height:60px;"'
        '        + "background:#333;border-radius:6px;\\"></span>";'
        '    rows += "<tr>"'
        '      + "<td style=\\"text-align:center;padding:8px 12px;white-space:nowrap;\\">"'
        '      + amrRankBadge(song.rank) + "</td>"'
        '      + "<td style=\\"text-align:center;padding:8px;\\">" + artworkTag + "</td>"'
        '      + "<td style=\\"padding:8px 12px;\\"><strong>" + name + "</strong></td>"'
        '      + "<td style=\\"padding:8px 12px;color:#aaa;\\">" + artist + "</td>"'
        '      + "</tr>";'
        '  });'
        '  tbody.innerHTML = rows;'
        '  document.getElementById("amr-updated").textContent = amrFormatUpdated(data.updated);'
        '  document.getElementById("amr-country-heading").textContent = AMR_LABELS[code] || code.toUpperCase();'
        '}'
        'document.getElementById("amr-country-select").addEventListener("change", function () {'
        '  amrRenderCountry(this.value);'
        '});'
        '</script>'
    )

