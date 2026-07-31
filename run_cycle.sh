#!/bin/bash
# cron等から呼び出す実行ラッパー。
# venvの有効化と.envの読み込みを行ってから1サイクル実行する。
set -euo pipefail
cd "$(dirname "$0")"

# 手動実行がcronの定期実行(30分毎)と重なると、main_loop.pyが2重起動して
# state.json更新やgit pushが競合しうる(実際に発生した)。flockで多重起動を
# 防止する(既に実行中なら即座に終了し、次のcron機会を待つ)。
exec 200>/tmp/autonomous-content-bot-run_cycle.lock
if ! flock -n 200; then
  echo "[run_cycle] 既に実行中のため、このサイクルはスキップします"
  exit 0
fi

# GitHub上でマージされた変更(kind_generatorが作ったPRのマージ含む)を
# 毎サイクル自動で取り込む。失敗してもサイクル自体は止めず、
# 既存のコードのまま続行する(ネットワーク不調等での全断を避けるため)。
git pull --no-edit >/dev/null 2>&1 || echo "[run_cycle] git pullに失敗しましたが処理を続行します"

source .venv/bin/activate

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python3 -m src.main_loop
