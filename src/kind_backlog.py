"""
kind_backlog.py
----------------
新kindの一括拡張を「人間が明示的に起動するバッチ処理」として行う。

main_loop.py の自律6時間サイクル(kind_generator.py)とは別モードであり、
cronには登録しない。kind_backlog.yaml から status: pending の候補を
先頭からN件取り出し、既存の安全なパイプライン
(propose_new_kind(target_niche指定) → validate_plugin_code →
 test_plugin → create_kind_pr)にそのままかける。

6時間の再実行ガード(kind_generator.MIN_INTERVAL_HOURS)は自律ループの
暴走防止用であり、人間が明示的に都度実行するこのバックログ処理には適用しない。

各候補の処理結果(成功/却下いずれも)は kind_backlog.yaml の該当エントリの
status に反映する(done=PR作成成功、skipped=却下。マージするかどうかの
判断自体は人間がGitHub上で行う)。

実行例: python3 -m src.kind_backlog --n 2
"""

import argparse
import os
import subprocess

import yaml

from . import state as state_mod
from .kind_generator import (
    anthropic,
    create_kind_pr,
    create_paid_api_issue,
    is_valid_kind_name,
    propose_new_kind,
    test_plugin,
    validate_plugin_code,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.yaml")
BACKLOG_PATH = os.path.join(REPO_ROOT, "kind_backlog.yaml")


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_backlog() -> dict:
    with open(BACKLOG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _update_status(kind_name_hint: str, new_status: str) -> None:
    """kind_backlog.yamlをyaml.safe_load/dumpで往復させるとコメント・書式が
    失われるため(config.yamlの_append_seed_niche()と同じ理由)、該当候補の
    直後にある最初の`status:`行だけをテキストとして書き換える。"""
    with open(BACKLOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_target_block = False
    for i, line in enumerate(lines):
        # 各候補は "  - kind_name_hint: xxx" のように先頭が"- "付きのため
        # 完全一致ではなくendswithで判定する
        if line.strip().endswith(f"kind_name_hint: {kind_name_hint}"):
            in_target_block = True
            continue
        if in_target_block and line.strip().startswith("status:"):
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f"{indent}status: {new_status}\n"
            break

    with open(BACKLOG_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _commit_and_push_backlog_status(kind_name_hint: str) -> None:
    """kind_backlog.yamlのstatus変更はローカルファイル書き換えだけでは
    GitHub上のリポジトリと乖離したままになる(create_kind_pr()内のPR用ブランチ
    への切り替え・戻しとは別に、mainブランチ上でこのファイルだけをコミットする
    必要がある)。publisher.pyの_git_publish()と同じ理由でここでも都度push する。"""
    try:
        subprocess.run(
            ["git", "-C", REPO_ROOT, "add", BACKLOG_PATH],
            check=True, capture_output=True, text=True,
        )
        commit = subprocess.run(
            ["git", "-C", REPO_ROOT, "commit", "-m", f"kind_backlog: {kind_name_hint}のstatus更新"],
            capture_output=True, text=True,
        )
        if commit.returncode != 0:
            no_op_markers = ("nothing to commit", "no changes added to commit")
            if any(marker in commit.stdout for marker in no_op_markers):
                return
            print(f"[kind_backlog] git commit失敗: {commit.stdout}{commit.stderr}")
            return
        push = subprocess.run(
            ["git", "-C", REPO_ROOT, "push"],
            capture_output=True, text=True,
        )
        if push.returncode != 0:
            print(f"[kind_backlog] git push失敗: {push.stderr}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[kind_backlog] git操作に失敗したためpushをスキップしました: {e}")


def run_backlog(n: int = 1) -> None:
    config = _load_config()
    if not config.get("kind_generator", {}).get("enabled", False):
        print("[kind_backlog] kind_generator.enabled=false のため何もしません")
        return

    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        print("[kind_backlog] ANTHROPIC_API_KEY未設定のため中断します")
        return

    backlog = _load_backlog()
    pending = [c for c in backlog.get("candidates", []) if c.get("status") == "pending"]
    if not pending:
        print("[kind_backlog] status: pending の候補がありません(全て処理済みです)")
        return

    targets = pending[:n]
    print(
        f"[kind_backlog] {len(targets)}件を処理します"
        f"(pending残り: {len(pending)}件中の先頭{len(targets)}件)"
    )

    survival = config["survival"]

    for candidate in targets:
        kind_name_hint = candidate["kind_name_hint"]
        niche_seed = candidate["niche_seed"]
        notes = candidate.get("notes", "")
        category_hint = candidate.get("category", "")

        print(f"\n===== {kind_name_hint} ({niche_seed}) =====")

        st = state_mod.load_state(survival["starting_balance_usd"])
        proposal = propose_new_kind(st, target_niche=niche_seed, target_notes=notes)
        if proposal is None:
            print(
                f"[kind_backlog] '{kind_name_hint}': 提案生成に失敗しました"
                "(AI出力のパースエラー等)。pendingのまま次回に持ち越します。"
            )
            continue

        if not is_valid_kind_name(proposal.kind_name):
            print(
                f"[kind_backlog] '{kind_name_hint}': kind_name不正/重複のため却下: "
                f"{proposal.kind_name!r}"
            )
            _update_status(kind_name_hint, "skipped")
            _commit_and_push_backlog_status(kind_name_hint)
            continue

        if proposal.requires_paid_api:
            url = create_paid_api_issue(proposal)
            print(
                f"[kind_backlog] '{kind_name_hint}': 有料/要登録APIが必要なため"
                f"Issueを作成しました: {url}"
            )
            _update_status(kind_name_hint, "skipped")
            _commit_and_push_backlog_status(kind_name_hint)
            continue

        ok, reason = validate_plugin_code(proposal.plugin_code)
        if not ok:
            print(f"[kind_backlog] '{kind_name_hint}': 静的検証で却下: {reason}")
            _update_status(kind_name_hint, "skipped")
            _commit_and_push_backlog_status(kind_name_hint)
            continue

        ok, output = test_plugin(proposal)
        if not ok:
            print(f"[kind_backlog] '{kind_name_hint}': 動作テストで却下: {output}")
            _update_status(kind_name_hint, "skipped")
            _commit_and_push_backlog_status(kind_name_hint)
            continue

        url = create_kind_pr(proposal, output)
        _update_status(kind_name_hint, "done")
        _commit_and_push_backlog_status(kind_name_hint)

        print(f"[kind_backlog] '{kind_name_hint}': PR作成成功")
        print(f"  PR URL: {url}")
        print(f"  カテゴリ: {category_hint}")
        print(f"  ニッチ名(実装後): {proposal.niche_seed}")
        print(f"  使用API/データ源: {proposal.api_notes}")
        print(f"  動作テスト出力: {output[:300]}")
        print(
            "  ※ html.escape()の網羅性・URL検証等の最終確認は、静的検証"
            "(validate_plugin_code)を通過済みではありますが、人間によるPR"
            "レビュー時に改めて確認してください。"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="新kindバックログを人間主導で処理する")
    parser.add_argument("--n", type=int, default=1, help="今回処理する候補数(既定: 1)")
    args = parser.parse_args()
    run_backlog(n=args.n)


if __name__ == "__main__":
    main()
