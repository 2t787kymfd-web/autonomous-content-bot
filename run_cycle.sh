#!/bin/bash
# cron等から呼び出す実行ラッパー。
# venvの有効化と.envの読み込みを行ってから1サイクル実行する。
set -euo pipefail
cd "$(dirname "$0")"

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
