"""kind_generator.py が自動生成したプラグイン: sports_league"""

import requests
import html
from datetime import datetime

KIND_NAME = "sports_league"
KEYWORDS = ["リーグ", "順位表", "試合結果", "サッカー", "スポーツ", "スタンディング", "league", "standings", "football", "soccer", "sports"]
CATEGORY = "スポーツ"

# TheSportsDB テストAPIキー (無料・非商用・読み取り専用)
_API_KEY = "123"
_BASE = f"https://www.thesportsdb.com/api/v1/json/{_API_KEY}"

# ニッチ名→リーグID のマッピング（TheSportsDB のリーグID）
_LEAGUE_MAP = {
    "プレミアリーグ": "4328",
    "ラ・リーガ": "4335",
    "ブンデスリーガ": "4331",
    "セリエA": "4332",
    "リーグ・アン": "4334",
    "Jリーグ": "4346",
    "MLSメジャーリーグサッカー": "4346",
    "エールディヴィジ": "4337",
    "プリメイラリーガ": "4344",
    "スコティッシュプレミアシップ": "4330",
    "主要リーグの順位表": "4328",
    "主要リーグの順位表・直近試合結果": "4328",
    "サッカー順位表": "4328",
    "欧州サッカー順位表": "4328",
    "Jリーグ順位表": "4346",
}

# デフォルトのフォールバックリーグID
_DEFAULT_LEAGUE_ID = "4328"


def _get_league_id(niche: str) -> str:
    """ニッチ名からリーグIDを取得する。"""
    for key, lid in _LEAGUE_MAP.items():
        if key in niche:
            return lid
    return _DEFAULT_LEAGUE_ID


def _get_current_season(league_id: str) -> str:
    """リーグの現在シーズンを取得する。"""
    url = f"{_BASE}/search_all_seasons.php?id={league_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    seasons = data.get("seasons") or []
    if seasons:
        # 最新シーズンを返す
        return seasons[-1].get("strSeason", "2023-2024")
    return "2023-2024"


def fetch(niche: str) -> tuple:
    """TheSportsDB APIから順位表と直近試合結果を取得する。"""
    league_id = _get_league_id(niche)

    # シーズン取得
    try:
        season = _get_current_season(league_id)
    except Exception:
        season = "2023-2024"

    # 順位表の取得
    standings_url = f"{_BASE}/lookuptable.php?l={league_id}&s={season}"
    standings_resp = requests.get(standings_url, timeout=10)
    standings_resp.raise_for_status()
    standings_data = standings_resp.json()
    table = standings_data.get("table") or []

    # 直近の試合結果取得
    events_url = f"{_BASE}/eventsseason.php?id={league_id}&s={season}"
    events_resp = requests.get(events_url, timeout=10)
    events_resp.raise_for_status()
    events_data = events_resp.json()
    all_events = events_data.get("events") or []

    # 実データが1件もない場合は例外を送出
    if not table and not all_events:
        raise RuntimeError(
            f"TheSportsDB APIからリーグID={league_id}のデータを取得できませんでした。"
        )

    # 直近の試合のみ抽出（日付が過去のもの、最大10件）
    today = datetime.utcnow().date()
    past_events = []
    for ev in all_events:
        date_str = ev.get("dateEvent", "")
        if not date_str:
            continue
        try:
            ev_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        score_home = ev.get("intHomeScore")
        score_away = ev.get("intAwayScore")
        if ev_date <= today and score_home is not None and score_away is not None:
            past_events.append(ev)

    # 日付降順でソートして最新10件
    past_events.sort(key=lambda e: e.get("dateEvent", ""), reverse=True)
    recent_events = past_events[:10]

    # 順位表は上位20チームのみ
    top_table = table[:20]

    # リーグ名の取得
    league_name = ""
    if top_table:
        league_name = top_table[0].get("strLeague", "")
    elif recent_events:
        league_name = recent_events[0].get("strLeague", "")

    # サマリー文字列
    summary_parts = []
    if top_table:
        leader = top_table[0]
        summary_parts.append(
            f"順位表首位: {leader.get('strTeam', '不明')} "
            f"({leader.get('intWin', 0)}勝{leader.get('intLoss', 0)}敗)"
        )
    if recent_events:
        latest = recent_events[0]
        summary_parts.append(
            f"直近試合: {latest.get('strHomeTeam', '?')} "
            f"{latest.get('intHomeScore', '?')}-{latest.get('intAwayScore', '?')} "
            f"{latest.get('strAwayTeam', '?')} ({latest.get('dateEvent', '?')})"
        )
    if not summary_parts:
        raise RuntimeError("有効なデータが取得できませんでした。")

    summary = f"{league_name} | " + " / ".join(summary_parts)

    # raw_data（画像URLは一切含めない）
    def _safe_standing(row: dict) -> dict:
        return {
            "rank": row.get("intRank", ""),
            "team": row.get("strTeam", ""),
            "played": row.get("intPlayed", ""),
            "win": row.get("intWin", ""),
            "draw": row.get("intDraw", ""),
            "loss": row.get("intLoss", ""),
            "goals_for": row.get("intGoalsFor", ""),
            "goals_against": row.get("intGoalsAgainst", ""),
            "points": row.get("intPoints", ""),
        }

    def _safe_event(ev: dict) -> dict:
        return {
            "date": ev.get("dateEvent", ""),
            "time": ev.get("strTime", ""),
            "home_team": ev.get("strHomeTeam", ""),
            "away_team": ev.get("strAwayTeam", ""),
            "home_score": ev.get("intHomeScore", ""),
            "away_score": ev.get("intAwayScore", ""),
            "round": ev.get("intRound", ""),
        }

    raw = {
        "league_name": league_name,
        "league_id": league_id,
        "season": season,
        "standings": [_safe_standing(r) for r in top_table],
        "recent_events": [_safe_event(e) for e in recent_events],
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    sources = [
        "https://www.thesportsdb.com/ (TheSportsDB - 無料テストAPI、非商用利用)"
    ]
    return summary, sources, raw


def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """順位表と直近試合結果のHTML断片を返す。"""
    league_name = html.escape(str(raw_data.get("league_name", niche)))
    season = html.escape(str(raw_data.get("season", "")))
    fetched_at = html.escape(str(raw_data.get("fetched_at", "")))
    standings = raw_data.get("standings", [])
    recent_events = raw_data.get("recent_events", [])

    parts = []
    parts.append(f'<h1>🏆 {html.escape(niche)}</h1>')
    parts.append(
        f'<p>リーグ: <strong>{league_name}</strong>　'
        f'シーズン: <strong>{season}</strong>　'
        f'取得日時: {fetched_at}</p>'
    )

    # ---- 順位表セクション ----
    if standings:
        parts.append('<h2>📊 順位表</h2>')
        parts.append('<div class="table-responsive">')
        parts.append('<table>')
        parts.append(
            '<thead><tr>'
            '<th>順位</th>'
            '<th>チーム名</th>'
            '<th>試合</th>'
            '<th>勝</th>'
            '<th>分</th>'
            '<th>負</th>'
            '<th>得点</th>'
            '<th>失点</th>'
            '<th>勝点</th>'
            '</tr></thead>'
        )
        parts.append('<tbody>')
        for row in standings:
            rank = html.escape(str(row.get("rank", "")))
            team = html.escape(str(row.get("team", "")))
            played = html.escape(str(row.get("played", "")))
            win = html.escape(str(row.get("win", "")))
            draw = html.escape(str(row.get("draw", "")))
            loss = html.escape(str(row.get("loss", "")))
            gf = html.escape(str(row.get("goals_for", "")))
            ga = html.escape(str(row.get("goals_against", "")))
            pts = html.escape(str(row.get("points", "")))
            # 上位3チームをハイライト
            try:
                rank_int = int(rank)
            except (ValueError, TypeError):
                rank_int = 99
            row_class = ' class="highlight"' if rank_int <= 3 else ''
            parts.append(
                f'<tr{row_class}>'
                f'<td><strong>{rank}</strong></td>'
                f'<td>{team}</td>'
                f'<td>{played}</td>'
                f'<td>{win}</td>'
                f'<td>{draw}</td>'
                f'<td>{loss}</td>'
                f'<td>{gf}</td>'
                f'<td>{ga}</td>'
                f'<td><strong>{pts}</strong></td>'
                '</tr>'
            )
        parts.append('</tbody></table></div>')
    else:
        parts.append('<p>順位表データを取得できませんでした。</p>')

    # ---- 直近試合結果セクション ----
    if recent_events:
        parts.append('<h2>⚽ 直近の試合結果</h2>')
        parts.append('<div class="table-responsive">')
        parts.append('<table>')
        parts.append(
            '<thead><tr>'
            '<th>試合日</th>'
            '<th>ホーム</th>'
            '<th>スコア</th>'
            '<th>アウェイ</th>'
            '<th>節</th>'
            '</tr></thead>'
        )
        parts.append('<tbody>')
        for ev in recent_events:
            date = html.escape(str(ev.get("date", "")))
            home = html.escape(str(ev.get("home_team", "")))
            away = html.escape(str(ev.get("away_team", "")))
            hs = html.escape(str(ev.get("home_score", "")))
            as_ = html.escape(str(ev.get("away_score", "")))
            rnd = html.escape(str(ev.get("round", "")))
            score_display = f"{hs} - {as_}" if hs != "" and as_ != "" else "- vs -"
            parts.append(
                f'<tr>'
                f'<td>{date}</td>'
                f'<td>{home}</td>'
                f'<td><strong>{score_display}</strong></td>'
                f'<td>{away}</td>'
                f'<td>{rnd}</td>'
                '</tr>'
            )
        parts.append('</tbody></table></div>')
    else:
        parts.append('<p>直近の試合結果データを取得できませんでした。</p>')

    # ---- 注意書き ----
    parts.append(
        '<p><small>※ 表示データはチーム名・順位・勝敗数・得点・試合日時のみです。'
        'ロゴ・バッジ等の画像は著作権対応のため表示していません。</small></p>'
    )

    # ---- 出典 ----
    safe_sources = [html.escape(str(s)) for s in sources]
    sources_html = "、".join(
        f'<a href="{html.escape(s.split(" ")[0])}" rel="noopener noreferrer" target="_blank">{s}</a>'
        if s.split(" ")[0].startswith("https://") else html.escape(s)
        for s in sources
    )
    parts.append(f'<div class="source">データ出典: {sources_html}</div>')

    return "\n".join(parts)

