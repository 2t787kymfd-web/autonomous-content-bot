"""kind_generator.py が自動生成したプラグイン: rocket_launch"""

import html
import requests
from datetime import datetime, timezone

KIND_NAME = "rocket_launch"
KEYWORDS = ["ロケット", "打ち上げ", "宇宙", "launch", "rocket", "spacecraft", "SpaceX", "NASA", "JAXA"]
CATEGORY = "エンタメ"


def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。"""
    url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/"
    params = {
        "limit": 10,
        "ordering": "net",
        "format": "json"
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if not results:
        raise RuntimeError("ロケット打ち上げ予定データが取得できませんでした。")

    launches = []
    for item in results:
        name = item.get("name", "不明")
        net = item.get("net", "")
        status_name = item.get("status", {}).get("name", "不明")
        status_abbrev = item.get("status", {}).get("abbrev", "")
        mission = item.get("mission") or {}
        mission_name = mission.get("name", "")
        mission_desc = mission.get("description", "")
        pad = item.get("pad", {}) or {}
        pad_name = pad.get("name", "")
        location = pad.get("location", {}) or {}
        location_name = location.get("name", "")
        rocket = item.get("rocket", {}) or {}
        config = rocket.get("configuration", {}) or {}
        rocket_name = config.get("full_name", config.get("name", "不明"))
        lsp = item.get("launch_service_provider", {}) or {}
        agency = lsp.get("name", "")
        image_url = item.get("image", "") or ""
        info_url = item.get("url", "") or ""

        # NETをJSTに変換
        net_jst = ""
        if net:
            try:
                dt_utc = datetime.fromisoformat(net.replace("Z", "+00:00"))
                # UTC+9
                from datetime import timedelta
                dt_jst = dt_utc.astimezone(timezone(timedelta(hours=9)))
                net_jst = dt_jst.strftime("%Y年%m月%d日 %H:%M JST")
            except Exception:
                net_jst = net

        launches.append({
            "name": name,
            "net": net,
            "net_jst": net_jst,
            "status_name": status_name,
            "status_abbrev": status_abbrev,
            "mission_name": mission_name,
            "mission_desc": mission_desc,
            "pad_name": pad_name,
            "location_name": location_name,
            "rocket_name": rocket_name,
            "agency": agency,
            "image_url": image_url if image_url.startswith("https://") else "",
            "info_url": info_url if info_url.startswith("https://") else "",
        })

    summary_lines = [f"直近のロケット打ち上げ予定（{len(launches)}件）:"]
    for lch in launches[:5]:
        summary_lines.append(f"・{lch['name']} / {lch['net_jst']} / {lch['status_name']}")
    summary = "\n".join(summary_lines)

    sources = ["https://ll.thespacedevs.com/ (The Space Devs Launch Library 2)"]
    raw = {"launches": launches, "fetched_at": datetime.now(timezone.utc).isoformat()}
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。"""
    launches = raw_data.get("launches", [])
    fetched_at = raw_data.get("fetched_at", "")

    # 取得時刻の整形
    fetched_str = ""
    if fetched_at:
        try:
            dt = datetime.fromisoformat(fetched_at)
            fetched_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            fetched_str = fetched_at

    # ステータスごとのバッジ色
    status_color_map = {
        "Go": "#2ecc71",
        "TBC": "#f39c12",
        "TBD": "#95a5a6",
        "Success": "#27ae60",
        "Failure": "#e74c3c",
        "Hold": "#e67e22",
        "In Flight": "#3498db",
        "Partial Failure": "#e67e22",
    }

    rows = []
    for lch in launches:
        safe_name = html.escape(str(lch.get("name", "")))
        safe_net_jst = html.escape(str(lch.get("net_jst", "-")))
        safe_rocket = html.escape(str(lch.get("rocket_name", "-")))
        safe_agency = html.escape(str(lch.get("agency", "-")))
        safe_location = html.escape(str(lch.get("location_name", "-")))
        safe_pad = html.escape(str(lch.get("pad_name", "-")))
        safe_mission = html.escape(str(lch.get("mission_name", "-")))
        safe_status = html.escape(str(lch.get("status_name", "-")))
        status_abbrev = lch.get("status_abbrev", "")
        badge_color = status_color_map.get(status_abbrev, "#7f8c8d")
        safe_badge_color = html.escape(badge_color)
        info_url = lch.get("info_url", "")
        if info_url and info_url.startswith("https://"):
            detail_link = f'<a href="{html.escape(info_url)}" target="_blank" rel="noopener">詳細</a>'
        else:
            detail_link = "-"

        rows.append(
            f'<tr>'
            f'<td><strong>{safe_name}</strong></td>'
            f'<td class="tel-value">{safe_net_jst}</td>'
            f'<td><span style="background:{safe_badge_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.85em;">{safe_status}</span></td>'
            f'<td>{safe_rocket}</td>'
            f'<td>{safe_agency}</td>'
            f'<td>{safe_location}<br><small>{safe_pad}</small></td>'
            f'<td>{safe_mission}</td>'
            f'<td>{detail_link}</td>'
            f'</tr>'
        )

    table_body = "\n".join(rows) if rows else "<tr><td colspan='8'>データがありません</td></tr>"

    source_list = "、".join(html.escape(s) for s in sources)

    return (
        f'<h1>🚀 {html.escape(niche)}</h1>'
        f'<p>The Space Devs Launch Library 2 APIから取得した直近のロケット打ち上げ予定です。'
        f'打ち上げ日時はJST（日本標準時）で表示しています。</p>'
        f'<p style="font-size:0.85em;color:#888;">データ取得時刻: {html.escape(fetched_str)}</p>'
        f'<div style="overflow-x:auto;">'
        f'<table>'
        f'<thead><tr>'
        f'<th>ミッション名</th>'
        f'<th>打ち上げ予定日時 (JST)</th>'
        f'<th>ステータス</th>'
        f'<th>ロケット</th>'
        f'<th>機関</th>'
        f'<th>射場</th>'
        f'<th>ミッション</th>'
        f'<th>詳細</th>'
        f'</tr></thead>'
        f'<tbody>{table_body}</tbody>'
        f'</table>'
        f'</div>'
        f'<h2>ステータス凡例</h2>'
        f'<ul>'
        f'<li><span style="background:#2ecc71;color:#fff;padding:1px 6px;border-radius:3px;">Go</span> 打ち上げ確定</li>'
        f'<li><span style="background:#f39c12;color:#fff;padding:1px 6px;border-radius:3px;">TBC</span> 日時確認中</li>'
        f'<li><span style="background:#95a5a6;color:#fff;padding:1px 6px;border-radius:3px;">TBD</span> 日時未定</li>'
        f'<li><span style="background:#e67e22;color:#fff;padding:1px 6px;border-radius:3px;">Hold</span> 延期中</li>'
        f'<li><span style="background:#3498db;color:#fff;padding:1px 6px;border-radius:3px;">In Flight</span> 飛行中</li>'
        f'</ul>'
        f'<div class="source">データ出典: {source_list}</div>'
    )

