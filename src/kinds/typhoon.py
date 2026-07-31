"""kind_generator.py が自動生成したプラグイン: typhoon"""

import requests
import html
import datetime

KIND_NAME = "typhoon"
KEYWORDS = ["台風", "typhoon", "進路", "熱帯低気圧", "暴風", "台風情報", "台風予報"]
CATEGORY = "天気・防災"

# 気象庁防災情報XMLフィード
JMA_FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/extra.xml"
JMA_BASE_URL = "https://www.data.jma.go.jp"


def _extract_tag(text: str, tag: str) -> str:
    """タグで囲まれたテキストを抽出する簡易パーサー"""
    open_tag = f"<{tag}"
    close_tag = f"</{tag}>"
    start = text.find(open_tag)
    if start == -1:
        return ""
    # タグ閉じ '>' を探す
    gt = text.find(">", start)
    if gt == -1:
        return ""
    end = text.find(close_tag, gt)
    if end == -1:
        return ""
    return text[gt + 1:end].strip()


def _extract_attr(text: str, attr: str) -> str:
    """タグ内の属性値を抽出する簡易パーサー"""
    key = f'{attr}="'
    start = text.find(key)
    if start == -1:
        return ""
    start += len(key)
    end = text.find('"', start)
    if end == -1:
        return ""
    return text[start:end]


def _parse_feed_entries(feed_text: str) -> list:
    """Atomフィードのentryブロックをパースしてリストを返す"""
    entries = []
    parts = feed_text.split("<entry>")
    for part in parts[1:]:
        end = part.find("</entry>")
        if end != -1:
            block = part[:end]
        else:
            block = part

        title = _extract_tag(block, "title")
        updated = _extract_tag(block, "updated")

        # <link href="..." .../> の href 属性
        link_start = block.find("<link")
        link_href = ""
        if link_start != -1:
            link_end = block.find(">", link_start)
            link_block = block[link_start:link_end + 1]
            link_href = _extract_attr(link_block, "href")

        # content 内の電文番号(id)
        content = _extract_tag(block, "content")
        entry_id = _extract_tag(block, "id")

        entries.append({
            "title": title,
            "updated": updated,
            "link": link_href,
            "id": entry_id,
            "content": content,
        })
    return entries


def _fetch_typhoon_bulletin(url: str) -> dict:
    """個別の台風情報XMLを取得して必要情報を抽出する"""
    if not url.startswith("https://"):
        return {}
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text
    except Exception:
        return {}

    result = {}

    # 台風名・番号
    typhoon_name = ""
    # <jmx_eb:TyphoonNamePart> や <Name> タグを試みる
    for tag in ["Name", "jmx_eb:Name"]:
        val = _extract_tag(text, tag)
        if val:
            typhoon_name = val
            break

    # 発表時刻
    report_datetime = _extract_tag(text, "ReportDateTime")
    if not report_datetime:
        report_datetime = _extract_tag(text, "DateTime")

    # 現在位置
    lat = ""
    lon = ""
    # <jmx_eb:Coordinate> か <Coordinate>
    coord_block_start = text.find("<Coordinate")
    if coord_block_start != -1:
        coord_end = text.find("</Coordinate>", coord_block_start)
        if coord_end != -1:
            coord_text = text[coord_block_start:coord_end + 13]
            coord_val = _extract_tag(coord_text, "Coordinate")
            # ISO 6709形式 例: +27.3+125.8/
            if coord_val:
                result["coordinate_raw"] = coord_val
                # 簡易パース: '+27.3+125.8/' or '-5.0+135.0/'
                cv = coord_val.rstrip("/")
                # 北緯・東経を抽出
                signs = []
                positions = []
                i = 0
                while i < len(cv):
                    if cv[i] in ('+', '-'):
                        j = i + 1
                        while j < len(cv) and cv[j] not in ('+', '-'):
                            j += 1
                        signs.append(cv[i])
                        positions.append(cv[i:j])
                        i = j
                    else:
                        i += 1
                if len(positions) >= 2:
                    lat = positions[0]
                    lon = positions[1]

    result["typhoon_name"] = typhoon_name
    result["report_datetime"] = report_datetime
    result["lat"] = lat
    result["lon"] = lon

    # 中心気圧
    pressure = ""
    # <Pressure> タグ
    p_start = text.find("<Pressure")
    if p_start != -1:
        p_end = text.find("</Pressure>", p_start)
        if p_end != -1:
            p_block = text[p_start:p_end + 11]
            pressure = _extract_tag(p_block, "Pressure")
    result["pressure"] = pressure

    # 最大風速
    wind = ""
    w_start = text.find("<WindSpeed")
    if w_start != -1:
        w_end = text.find("</WindSpeed>", w_start)
        if w_end != -1:
            w_block = text[w_start:w_end + 12]
            wind = _extract_tag(w_block, "WindSpeed")
    result["wind_speed"] = wind

    return result


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    resp = requests.get(JMA_FEED_URL, timeout=15)
    resp.raise_for_status()
    feed_text = resp.text

    entries = _parse_feed_entries(feed_text)
    if not entries:
        raise RuntimeError("気象庁フィードからエントリを取得できませんでした")

    # 台風関連エントリを絞り込む
    typhoon_entries = []
    for e in entries:
        title = e.get("title", "")
        if any(kw in title for kw in ["台風", "熱帯低気圧", "Typhoon", "typhoon"]):
            typhoon_entries.append(e)

    # フィード更新時刻
    feed_updated = _extract_tag(feed_text, "updated")

    bulletins = []
    if typhoon_entries:
        # 最新エントリから詳細取得(最大3件)
        for entry in typhoon_entries[:3]:
            link = entry.get("link", "")
            detail = {}
            if link.startswith("https://"):
                detail = _fetch_typhoon_bulletin(link)
            bulletins.append({
                "title": entry.get("title", ""),
                "updated": entry.get("updated", ""),
                "link": link,
                "detail": detail,
            })

    # フィードタイトル
    feed_title = _extract_tag(feed_text, "title")

    now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    fetch_time = now_jst.strftime("%Y-%m-%d %H:%M JST")

    if typhoon_entries:
        status = f"現在、台風・熱帯低気圧関連情報が{len(typhoon_entries)}件発表されています。"
    else:
        status = "現在、発表中の台風・熱帯低気圧情報はありません。"

    summary = (
        f"気象庁防災情報XMLフィード({fetch_time}取得)。{status}"
        f"フィード全体では{len(entries)}件のエントリがあります。"
    )

    sources = [
        f"{JMA_FEED_URL} (気象庁防災情報XML)",
        "https://www.data.jma.go.jp/developer/xml/feed/ (気象庁XMLデータ)",
    ]

    raw = {
        "feed_title": feed_title,
        "feed_updated": feed_updated,
        "fetch_time": fetch_time,
        "typhoon_count": len(typhoon_entries),
        "total_entries": len(entries),
        "bulletins": bulletins,
        "status": status,
        "recent_entries": [
            {"title": e.get("title", ""), "updated": e.get("updated", ""), "link": e.get("link", "")}
            for e in entries[:10]
        ],
    }

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    fetch_time = html.escape(str(raw_data.get("fetch_time", "")))
    typhoon_count = int(raw_data.get("typhoon_count", 0))
    total_entries = int(raw_data.get("total_entries", 0))
    status = html.escape(str(raw_data.get("status", "")))
    bulletins = raw_data.get("bulletins", [])
    recent_entries = raw_data.get("recent_entries", [])

    # ステータスバッジ
    if typhoon_count > 0:
        badge_class = "badge-danger"
        badge_text = f"⚠️ 台風情報あり ({typhoon_count}件)"
    else:
        badge_class = "badge-safe"
        badge_text = "✅ 現在、台風情報なし"

    out = []
    out.append(f'<h1>🌀 {html.escape(niche)}</h1>')
    out.append('<p>気象庁防災情報XMLフィードをもとに、最新の台風・熱帯低気圧情報をリアルタイムで表示します。</p>')

    out.append('<div class="summary-box">')
    out.append(f'<span class="status-badge {badge_class}">{html.escape(badge_text)}</span>')
    out.append(f'<p class="fetch-time">取得時刻: {fetch_time} &nbsp;|&nbsp; 全情報件数: {total_entries}件</p>')
    out.append(f'<p>{status}</p>')
    out.append('</div>')

    # 台風詳細情報
    if bulletins:
        out.append('<h2>🌀 台風・熱帯低気圧 詳細情報</h2>')
        for b in bulletins:
            title = html.escape(str(b.get("title", "")))
            updated = html.escape(str(b.get("updated", "")))
            link = b.get("link", "")
            safe_link = html.escape(link) if link.startswith("https://") else ""
            detail = b.get("detail", {})

            out.append('<div class="typhoon-card">')
            out.append(f'<h3>📋 {title}</h3>')
            out.append(f'<p class="updated-time">発表時刻: {updated}</p>')

            if detail:
                t_name = html.escape(str(detail.get("typhoon_name", "")))
                report_dt = html.escape(str(detail.get("report_datetime", "")))
                lat = html.escape(str(detail.get("lat", "")))
                lon = html.escape(str(detail.get("lon", "")))
                pressure = html.escape(str(detail.get("pressure", "")))
                wind = html.escape(str(detail.get("wind_speed", "")))

                out.append('<table>')
                out.append('<thead><tr><th>項目</th><th>値</th></tr></thead>')
                out.append('<tbody>')
                if t_name:
                    out.append(f'<tr><td>台風名</td><td>{t_name}</td></tr>')
                if report_dt:
                    out.append(f'<tr><td>報告時刻</td><td>{report_dt}</td></tr>')
                if lat and lon:
                    out.append(f'<tr><td>現在位置(緯度)</td><td>{lat}</td></tr>')
                    out.append(f'<tr><td>現在位置(経度)</td><td>{lon}</td></tr>')
                if pressure:
                    out.append(f'<tr><td>中心気圧</td><td>{pressure} hPa</td></tr>')
                if wind:
                    out.append(f'<tr><td>最大風速</td><td>{wind} m/s</td></tr>')
                out.append('</tbody>')
                out.append('</table>')

            if safe_link:
                out.append(f'<p><a href="{safe_link}" target="_blank" rel="noopener">🔗 気象庁 XML電文を見る</a></p>')
            out.append('</div>')
    else:
        out.append('<div class="no-typhoon-box">')
        out.append('<p>現在、発表中の台風・熱帯低気圧情報はありません。</p>')
        out.append('<p>台風シーズン(主に6月〜10月)に情報が掲載されます。</p>')
        out.append('</div>')

    # 最新防災情報一覧
    if recent_entries:
        out.append('<h2>📡 最新の防災情報一覧(直近10件)</h2>')
        out.append('<table>')
        out.append('<thead><tr><th>情報タイトル</th><th>更新日時</th><th>リンク</th></tr></thead>')
        out.append('<tbody>')
        for entry in recent_entries:
            e_title = html.escape(str(entry.get("title", "")))
            e_updated = html.escape(str(entry.get("updated", "")))
            e_link = entry.get("link", "")
            if e_link.startswith("https://"):
                e_link_html = f'<a href="{html.escape(e_link)}" target="_blank" rel="noopener">詳細</a>'
            else:
                e_link_html = "-"
            out.append(f'<tr><td>{e_title}</td><td>{e_updated}</td><td>{e_link_html}</td></tr>')
        out.append('</tbody>')
        out.append('</table>')

    # 注意事項
    out.append('<div class="notice-box">')
    out.append('<h3>⚠️ ご利用にあたって</h3>')
    out.append('<ul>')
    out.append('<li>本情報は気象庁防災情報XMLフィードを自動取得・表示しています。</li>')
    out.append('<li>最新・正確な情報は必ず<a href="https://www.jma.go.jp/jma/index.html" target="_blank" rel="noopener">気象庁公式サイト</a>でご確認ください。</li>')
    out.append('<li>台風の接近時は気象庁・自治体の避難情報に従ってください。</li>')
    out.append('</ul>')
    out.append('</div>')

    # 出典
    source_items = "".join(
        f'<li><a href="{html.escape(s.split(" (")[0])}" target="_blank" rel="noopener">{html.escape(s)}</a></li>'
        if s.split(" (")[0].startswith("https://") else f"<li>{html.escape(s)}</li>"
        for s in sources
    )
    out.append(f'<div class="source">データ出典:<ul>{source_items}</ul></div>')

    return "\n".join(out)

