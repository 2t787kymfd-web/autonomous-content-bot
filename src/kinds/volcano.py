"""kind_generator.py が自動生成したプラグイン: volcano"""

import requests
import html
import json
from datetime import datetime, timezone
from typing import Any

KIND_NAME = "volcano"
KEYWORDS = ["火山", "噴火", "火山活動", "volcano", "eruption", "溶岩", "火山灰"]
CATEGORY = "天気・防災"

# Smithsonian GVP Weekly Volcanic Activity Report RSS
_GVP_RSS_URL = "https://volcano.si.edu/news/WeeklyVolcanoRSS.xml"
# USGS Volcano Hazards Program - volcanic earthquake events (last 30 days, M1.0+)
_USGS_VOLC_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?format=geojson&orderby=time&limit=10"
    "&minmagnitude=1.0&maxdepth=20"
    "&producttype=volcani-hazard"
)
# Fallback: USGS earthquakes near known volcanic regions (Alaska/Hawaii/Cascades)
# We use a broader query filtered by keyword in place description
_USGS_EQ_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?format=geojson&orderby=time&limit=20"
    "&minmagnitude=1.0"
)


def _parse_rss_items(xml_text: str) -> list:
    """Very lightweight RSS <item> parser — no external XML library needed."""
    items = []
    # Split on <item> boundaries
    parts = xml_text.split("<item>")
    for part in parts[1:]:  # skip text before first <item>
        end = part.find("</item>")
        if end != -1:
            part = part[:end]
        item: dict = {}
        for tag in ("title", "link", "description", "pubDate"):
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"
            s = part.find(start_tag)
            e = part.find(end_tag)
            if s != -1 and e != -1:
                raw = part[s + len(start_tag):e].strip()
                # strip CDATA if present
                if raw.startswith("<![CDATA["):
                    raw = raw[9:]
                    if raw.endswith("]]>"):
                        raw = raw[:-3]
                item[tag] = raw.strip()
        if item.get("title"):
            items.append(item)
    return items


def fetch(niche: str) -> tuple:
    """researcher.py契約: (summary, sources, raw_data) を返す。
    RSS取得に失敗した場合、成功したかのようなsummaryは返さず例外を送出する
    (researcher.py側がこれを捕捉しhas_unique_data=Falseとして安全にスキップする)。"""
    resp = requests.get(_GVP_RSS_URL, timeout=15)
    resp.raise_for_status()
    rss_items = _parse_rss_items(resp.text)

    if not rss_items:
        raise RuntimeError("Smithsonian GVP RSSからレポート項目を取得できませんでした")

    first = rss_items[0]
    title = first.get("title", "(タイトル不明)")
    pub = first.get("pubDate", "")
    summary = (
        f"Smithsonian GVP 週次火山活動レポート（最新 {len(rss_items)} 件）。"
        f"最新ヘッドライン: {title} ({pub})"
    )

    sources = [
        "https://volcano.si.edu/news/WeeklyVolcanoRSS.xml (Smithsonian Global Volcanism Program)",
    ]

    raw: dict = {
        "rss_items": rss_items[:15],  # 最大15件
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.py契約: <h1>から始まるHTML本文断片を返す。"""
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    rss_items: list = raw_data.get("rss_items", [])
    rss_error = raw_data.get("rss_error", "")

    # ---- header ----
    parts = []
    parts.append(f'<h1>🌋 {html.escape(niche)}</h1>')
    parts.append(
        '<p>Smithsonian Global Volcanism Program (GVP) が毎週発行する'
        '世界の火山活動週次レポートをリアルタイムで表示します。'
        '活動中の火山・噴火情報・警戒レベル変更などを確認できます。</p>'
    )
    parts.append(f'<p><small class="tel-value">データ取得日時: {fetched_at}</small></p>')

    # ---- error banner ----
    if rss_error and not rss_items:
        parts.append(
            f'<div style="background:#fff3cd;border:1px solid #ffc107;padding:12px;border-radius:6px;">'
            f'⚠️ データ取得エラー: {html.escape(rss_error)}'
            f'</div>'
        )

    # ---- RSS table ----
    if rss_items:
        parts.append('<h2>📋 週次火山活動レポート 最新一覧</h2>')
        parts.append(
            '<table>'
            '<thead><tr>'
            '<th>#</th>'
            '<th>タイトル / 火山名</th>'
            '<th>公開日</th>'
            '<th>詳細</th>'
            '</tr></thead>'
            '<tbody>'
        )
        for i, item in enumerate(rss_items, 1):
            title = html.escape(str(item.get("title", "(不明)")))
            pub = html.escape(str(item.get("pubDate", "-")))
            link_raw = str(item.get("link", "")).strip()
            if link_raw.startswith("https://"):
                link_cell = f'<a href="{html.escape(link_raw)}" target="_blank" rel="noopener">詳細 ↗</a>'
            elif link_raw.startswith("http://"):
                link_cell = "(http)"
            else:
                link_cell = "-"
            # description snippet (strip HTML tags naively)
            desc_raw = str(item.get("description", ""))
            # remove HTML tags
            clean_desc = ""
            in_tag = False
            for ch in desc_raw:
                if ch == "<":
                    in_tag = True
                elif ch == ">":
                    in_tag = False
                elif not in_tag:
                    clean_desc += ch
            clean_desc = " ".join(clean_desc.split())[:200]
            if clean_desc:
                title_cell = f'<strong>{title}</strong><br><small>{html.escape(clean_desc)}{"…" if len(clean_desc) >= 200 else ""}</small>'
            else:
                title_cell = f'<strong>{title}</strong>'
            row_class = 'class="alt"' if i % 2 == 0 else ''
            parts.append(
                f'<tr {row_class}>'
                f'<td class="tel-value">{i}</td>'
                f'<td>{title_cell}</td>'
                f'<td class="tel-value">{pub}</td>'
                f'<td>{link_cell}</td>'
                f'</tr>'
            )
        parts.append('</tbody></table>')
    else:
        parts.append('<p>現在、表示できる火山活動情報がありません。しばらくしてから再度お試しください。</p>')

    # ---- info box ----
    parts.append(
        '<h2>ℹ️ 火山警戒レベルの目安</h2>'
        '<table>'
        '<thead><tr><th>色/レベル</th><th>意味</th></tr></thead>'
        '<tbody>'
        '<tr><td>🟢 Green / 通常</td><td>火山活動は正常範囲内。噴火の兆候なし。</td></tr>'
        '<tr class="alt"><td>🟡 Yellow / 注意</td><td>火山活動が上昇中。モニタリング強化。</td></tr>'
        '<tr><td>🟠 Orange / 警戒</td><td>噴火の可能性が高まっている。航空・住民注意。</td></tr>'
        '<tr class="alt"><td>🔴 Red / 危険</td><td>噴火が発生中または切迫。航空路閉鎖等の可能性。</td></tr>'
        '</tbody></table>'
    )

    # ---- external links ----
    parts.append(
        '<h2>🔗 関連リンク</h2>'
        '<ul>'
        '<li><a href="https://volcano.si.edu/" target="_blank" rel="noopener">Smithsonian Global Volcanism Program (GVP)</a> — 世界の火山活動データベース</li>'
        '<li><a href="https://volcanoes.usgs.gov/" target="_blank" rel="noopener">USGS Volcano Hazards Program</a> — 米国地質調査所 火山ハザード</li>'
        '<li><a href="https://www.data.jma.go.jp/svd/vois/data/tokyo/STOCK/monthly_v-act_doc/monthly_vact.php" target="_blank" rel="noopener">気象庁 火山活動解説資料</a> — 国内火山の月次レポート</li>'
        '</ul>'
    )

    # ---- sources ----
    sources_html = ""
    for s in sources:
        safe_s = html.escape(str(s))
        # extract URL part
        url_part = str(s).split(" ")[0]
        if url_part.startswith("https://"):
            sources_html += f'<a href="{html.escape(url_part)}" target="_blank" rel="noopener">{safe_s}</a><br>'
        else:
            sources_html += f'{safe_s}<br>'
    parts.append(
        f'<div class="source">データ出典: {sources_html}</div>'
    )

    return "\n".join(parts)

