#!/bin/bash
# cron等から呼び出す実行ラッパー(新kindのAI自動提案)。
# venvの有効化と.envの読み込みを行ってからkind_generatorを1回実行する。
# main_loop.py(run_cycle.sh)とは別枠・週1回程度の頻度で実行する想定。
set -euo pipefail
cd "$(dirname "$0")"

git pull --no-edit >/dev/null 2>&1 || echo "[run_kind_generator] git pullに失敗しましたが処理を続行します"

source .venv/bin/activate

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python3 -m src.kind_generator
