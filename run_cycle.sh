#!/bin/bash
# cron等から呼び出す実行ラッパー。
# venvの有効化と.envの読み込みを行ってから1サイクル実行する。
set -euo pipefail
cd "$(dirname "$0")"

source .venv/bin/activate

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python3 -m src.main_loop
