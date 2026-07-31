"""kind_generator.py が自動生成したプラグイン: sports_standings"""

import requests
import html
import re
from datetime import datetime

KIND_NAME = "sports_standings"
KEYWORDS = ["スポーツ", "リーグ", "順位表", "試合結果", "サッカー", "football", "standings", "league", "sports"]
CATEGORY = "スポーツ"

# OpenLigaDB: https://api.openligadb.de/
# 無料・APIキー不要・HTTPS・ドイツサッカーリーグ公式データ
#
# 注意: シーズン("season")は年ごとに変わるため、AI生成時点の固定値を
# ハードコードすると翌シーズン以降ずっと古いデータのままになってしまう
# (実際にAIが生成した直後のコードは"2024"固定になっており、この修正時点
# (2026年7月)で既に1シーズン分古かった)。ブンデスリーガのシーズンは
# 8月開幕・翌年5月終了のため、_current_season()で「今日が8月以降なら今年、
# それ以外なら前年」を毎回計算する。


def _current_season() -> str:
    today = datetime.utcnow()
    year = today.year if today.month >= 8 else today.year - 1
    return str(year)


LEAGUE_SHORTCUTS = {
    "ブンデスリーガ": {"shortcut": "bl1", "name": "ブンデスリーガ (1部)"},
    "bundesliga": {"shortcut": "bl1", "name": "ブンデスリーガ (1部)"},
    "2部": {"shortcut": "bl2", "name": "ブンデスリーガ2部"},
    "bl2": {"shortcut": "bl2", "name": "ブンデスリーガ2部"},
    "3部": {"shortcut": "bl3", "name": "ブンデスリーガ3部"},
    "bl3": {"shortcut": "bl3", "name": "ブンデスリーガ3部"},
}

DEFAULT_SHORTCUT = {"shortcut": "bl1", "name": "ブンデスリーガ (1部)"}


def _detect_league(niche: str) -> dict:
    niche_lower = niche.lower()
    for key, val in LEAGUE_SHORTCUTS.items():
        if key.lower() in niche_lower:
            base = val
            break
    else:
        base = DEFAULT_SHORTCUT
    return {**base, "season": _current_season()}


def _safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_str(val):
    if val is None:
        return ""
    return str(val)


def _fetch_season(shortcut: str, season: str) -> tuple:
    """1シーズン分の順位表・試合結果を取得する。開幕前(全チーム0試合)の
    場合はstandings_dataを空扱いにして呼び出し元でフォールバックさせる。"""
    base = "https://api.openligadb.de"
    standings_url = f"{base}/getbltable/{shortcut}/{season}"
    matches_url = f"{base}/getmatchdata/{shortcut}/{season}"

    standings_data = []
    matches_data = []
    errors = []

    try:
        resp = requests.get(standings_url, timeout=15)
        resp.raise_for_status()
        standings_data = resp.json()
        # シーズン開幕前は全チームmatches=0で返ってくるため「データ無し」扱いにする
        if standings_data and all(e.get("matches", 0) == 0 for e in standings_data):
            standings_data = []
    except Exception as e:
        errors.append(f"standings: {e}")

    try:
        resp2 = requests.get(matches_url, timeout=15)
        resp2.raise_for_status()
        all_matches = resp2.json()
        # 終了済み試合のみ、最新10件
        finished = [m for m in all_matches if m.get("matchIsFinished", False)]
        matches_data = finished[-10:] if finished else []
    except Exception as e:
        errors.append(f"matches: {e}")

    return standings_data, matches_data, errors


def fetch(niche: str) -> tuple:
    league = _detect_league(niche)
    shortcut = league["shortcut"]
    season = league["season"]
    league_name = league["name"]

    standings_data, matches_data, errors = _fetch_season(shortcut, season)

    # 新シーズン開幕直後で試合データがまだ無い場合、前シーズンの結果に
    # フォールバックする(空のページを公開しないため)
    if not standings_data and not matches_data:
        prev_season = str(int(season) - 1)
        standings_data, matches_data, prev_errors = _fetch_season(shortcut, prev_season)
        if standings_data or matches_data:
            season = prev_season
        else:
            errors.extend(prev_errors)

    if not standings_data and not matches_data:
        raise RuntimeError(f"OpenLigaDB からデータを取得できませんでした: {errors}")

    # 順位表サマリ
    top3 = []
    for entry in standings_data[:3]:
        team = _safe_str(entry.get("teamName", ""))
        pts = _safe_int(entry.get("points"))
        top3.append(f"{team}({pts}pt)")
    top3_str = ", ".join(top3) if top3 else "データなし"

    summary = (
        f"{league_name} の順位表・直近試合結果を取得しました。"
        f"上位3チーム: {top3_str}。"
        f"順位表 {len(standings_data)} チーム、直近試合 {len(matches_data)} 件。"
    )

    sources = [
        "https://api.openligadb.de/ (OpenLigaDB - ドイツサッカーデータ公開API)",
        "https://www.openligadb.de/ (OpenLigaDB 公式サイト)",
    ]

    raw = {
        "league_name": league_name,
        "shortcut": shortcut,
        "season": season,
        "standings": standings_data,
        "recent_matches": matches_data,
    }

    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    league_name = html.escape(_safe_str(raw_data.get("league_name", "リーグ")))
    season = html.escape(_safe_str(raw_data.get("season", "")))
    standings = raw_data.get("standings", [])
    recent_matches = raw_data.get("recent_matches", [])

    parts = []
    parts.append(f'<h1>🏆 {html.escape(niche)}</h1>')
    parts.append(
        f'<p>{league_name} ({season}シーズン) の最新順位表と直近試合結果です。'
        f'データは <a href="https://www.openligadb.de/" rel="noopener noreferrer">OpenLigaDB</a> より取得しています。</p>'
    )

    # --- 順位表 ---
    if standings:
        parts.append('<h2>📊 順位表</h2>')
        parts.append(
            '<table>'
            '<thead><tr>'
            '<th>順位</th>'
            '<th>チーム名</th>'
            '<th>試合数</th>'
            '<th>勝</th>'
            '<th>分</th>'
            '<th>負</th>'
            '<th>得点</th>'
            '<th>失点</th>'
            '<th>得失差</th>'
            '<th>勝点</th>'
            '</tr></thead>'
            '<tbody>'
        )
        for i, entry in enumerate(standings, start=1):
            team = html.escape(_safe_str(entry.get("teamName", "-")))
            matches = _safe_int(entry.get("matches"))
            won = _safe_int(entry.get("won"))
            draw = _safe_int(entry.get("draw"))
            lost = _safe_int(entry.get("lost"))
            goals = _safe_int(entry.get("goals"))
            op_goals = _safe_int(entry.get("opponentGoals"))
            diff = goals - op_goals
            diff_str = html.escape(f"+{diff}" if diff > 0 else str(diff))
            points = _safe_int(entry.get("points"))
            row_class = ""
            if i <= 4:
                row_class = ' class="rank-high"'
            elif i >= len(standings) - 2:
                row_class = ' class="rank-low"'
            parts.append(
                f'<tr{row_class}>'
                f'<td class="tel-value">{html.escape(str(i))}</td>'
                f'<td>{team}</td>'
                f'<td class="tel-value">{html.escape(str(matches))}</td>'
                f'<td class="tel-value">{html.escape(str(won))}</td>'
                f'<td class="tel-value">{html.escape(str(draw))}</td>'
                f'<td class="tel-value">{html.escape(str(lost))}</td>'
                f'<td class="tel-value">{html.escape(str(goals))}</td>'
                f'<td class="tel-value">{html.escape(str(op_goals))}</td>'
                f'<td class="tel-value">{diff_str}</td>'
                f'<td class="tel-value"><strong>{html.escape(str(points))}</strong></td>'
                '</tr>'
            )
        parts.append('</tbody></table>')
        parts.append(
            '<p style="font-size:0.85em;color:#888;">'
            '🔵 上位4位: UEFA Champions League/Europa League圏 / 🔴 下位3位: 降格圏 (目安)'
            '</p>'
        )
    else:
        parts.append('<p>順位表データを取得できませんでした。</p>')

    # --- 直近試合結果 ---
    if recent_matches:
        parts.append('<h2>⚽ 直近試合結果</h2>')
        parts.append(
            '<table>'
            '<thead><tr>'
            '<th>試合日時</th>'
            '<th>ホーム</th>'
            '<th>スコア</th>'
            '<th>アウェイ</th>'
            '<th>節</th>'
            '</tr></thead>'
            '<tbody>'
        )
        # 新しい順に表示
        for match in reversed(recent_matches):
            match_dt_raw = _safe_str(match.get("matchDateTime", ""))
            # ISO8601形式のパース試み
            try:
                dt = datetime.fromisoformat(match_dt_raw.replace("Z", "+00:00"))
                match_dt = dt.strftime("%Y/%m/%d %H:%M")
            except Exception:
                match_dt = html.escape(match_dt_raw[:16]) if match_dt_raw else "-"

            team1 = _safe_str(match.get("team1", {}).get("teamName", "-") if isinstance(match.get("team1"), dict) else "-")
            team2 = _safe_str(match.get("team2", {}).get("teamName", "-") if isinstance(match.get("team2"), dict) else "-")

            # 最終スコア取得 (matchResults から)
            match_results = match.get("matchResults", [])
            score_str = "-"
            for result in match_results:
                if isinstance(result, dict) and result.get("resultTypeID") == 2:
                    p1 = _safe_int(result.get("pointsTeam1"))
                    p2 = _safe_int(result.get("pointsTeam2"))
                    score_str = f"{p1} - {p2}"
                    break
            if score_str == "-" and match_results:
                r = match_results[-1]
                if isinstance(r, dict):
                    p1 = _safe_int(r.get("pointsTeam1"))
                    p2 = _safe_int(r.get("pointsTeam2"))
                    score_str = f"{p1} - {p2}"

            matchday = _safe_int(match.get("group", {}).get("groupOrderID") if isinstance(match.get("group"), dict) else 0)
            matchday_str = f"第{matchday}節" if matchday > 0 else "-"

            parts.append(
                f'<tr>'
                f'<td class="tel-value">{html.escape(match_dt)}</td>'
                f'<td>{html.escape(team1)}</td>'
                f'<td class="tel-value" style="text-align:center;"><strong>{html.escape(score_str)}</strong></td>'
                f'<td>{html.escape(team2)}</td>'
                f'<td>{html.escape(matchday_str)}</td>'
                '</tr>'
            )
        parts.append('</tbody></table>')
    else:
        parts.append('<p>直近の試合結果データを取得できませんでした。</p>')

    # --- 出典 ---
    parts.append('<div class="source">データ出典: ')
    source_links = []
    for src in sources:
        m = re.match(r'^(https://[^\s]+)\s*(.*)$', src)
        if m:
            url = m.group(1).rstrip('/')
            label = m.group(2).strip('()')
            safe_url = html.escape(url) if url.startswith("https://") else "#"
            safe_label = html.escape(label) if label else html.escape(url)
            source_links.append(f'<a href="{safe_url}" rel="noopener noreferrer">{safe_label}</a>')
        else:
            source_links.append(html.escape(src))
    parts.append(" / ".join(source_links))
    parts.append('</div>')

    return "\n".join(parts)

