"""
kind_generator.py
------------------
AIに新しいデータ種別(kind)のコードを提案・生成させ、安全性を検証した上で
GitHub PRとして提出する(自動マージはしない)。main_loopの30分毎サイクルとは
別に、週1回程度の頻度で実行する想定(cron別枠)。

安全設計:
1. 生成コードは src/kinds/ 配下の独立ファイルに限定する(既存コアへの
   文字列差し込みはしない)
2. ASTベースの静的検証(許可外のimport・eval/exec/os/subprocess等を拒否)
   を通らないコードは一切使用しない
3. 検証を通ったコードも、実際に外部APIを叩くテストに成功しない限り
   PRを作成しない(LLMがAPIを幻覚するリスクへの対策)
4. 人間が明示的にPRをマージするまで、生成コードは本番に一切反映されない
5. config.yaml の kind_generator.enabled が true の場合のみ動作する(opt-in)
"""

import ast
import importlib.util
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import requests
import yaml

try:
    import anthropic
except ImportError:
    anthropic = None

from . import state as state_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.yaml")
KINDS_DIR = os.path.join(REPO_ROOT, "src", "kinds")

GITHUB_OWNER = "2t787kymfd-web"
GITHUB_REPO = "autonomous-content-bot"

CORE_KIND_NAMES = ["fx", "crypto", "weather"]

# 生成コードに許可するimport(requestsは実行時にこちらで注入するため、
# 生成コード側でのimport自体は禁止する)
ALLOWED_IMPORT_MODULES = {"json", "datetime", "typing"}
FORBIDDEN_CALL_NAMES = {"eval", "exec", "compile", "__import__", "open"}
FORBIDDEN_ATTR_ROOTS = {"os", "sys", "subprocess", "socket", "shutil"}

ESTIMATED_COST_PER_KIND_GENERATION_USD = 0.15

PLUGIN_CONTRACT_EXAMPLE = '''
KIND_NAME = "example_kind"
KEYWORDS = ["キーワード1", "キーワード2"]

def fetch(niche: str) -> tuple:
    """researcher.pyの契約: (summary: str, sources: list, raw_data: dict) を返す。
    無料・APIキー不要のREST APIをrequests経由で呼ぶこと。"""
    resp = requests.get("https://example-free-api.example/endpoint", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    summary = "..."   # data_summary/品質ゲート用の日本語テキスト
    sources = ["https://example-free-api.example/ (出典名)"]
    raw = {...}        # build_html が使う構造化データ
    return summary, sources, raw

def build_html(niche: str, raw_data: dict, sources: list) -> str:
    """tool_builder.pyの契約: 完成品のHTML文字列(<!doctype html>から</html>まで)を返す。"""
    return "<!doctype html>...</html>"
'''

SYSTEM_PROMPT = f"""あなたはこのプロジェクト(autonomous-content-bot)の新しいデータ種別
(kind)を提案・実装するエンジニアです。

このプロジェクトは、無料・APIキー不要の公開APIから一次データを取得し、
それを使った実用ツール(HTML+JS)を自動生成・公開する自律ボットです。
既存のkind例: fx(為替、Frankfurter API)、crypto(暗号資産、CoinGecko API)、
weather(天気、Open-Meteo API)。

以下の契約を満たす新しいkindを1つ提案してください:

{PLUGIN_CONTRACT_EXAMPLE}

厳守事項:
- 提案するAPIは無料・アカウント登録不要・APIキー不要でなければならない
  (これが確信できない場合は requires_paid_api=true にして理由を書き、
  コードは生成しないこと)
- 生成コードで使ってよいのは requests, json, datetime, typing のみ
- eval/exec/compile/__import__/open は絶対に使わないこと
- os/sys/subprocess/socket/shutil には一切アクセスしないこと
- 既に対応済みのkindと重複しないこと

回答は必ず次のJSON形式のみで出力してください(他のテキストを含めない):
{{
  "kind_name": "英数字とアンダースコアのみの一意な識別子",
  "niche_seed": "config.yamlのseed_nichesに追加する日本語のニッチ名",
  "keywords": ["ニッチ名とのマッチングに使う日本語/英語キーワードのリスト"],
  "requires_paid_api": false,
  "api_notes": "使用するAPIの説明(requires_paid_api=trueの場合は必要な手続きを記載)",
  "plugin_code": "上記契約を満たす完全なPythonコード(requires_paid_api=falseの場合のみ。それ以外はnull)"
}}
"""


@dataclass
class KindProposal:
    kind_name: str
    niche_seed: str
    keywords: List[str]
    requires_paid_api: bool
    api_notes: str
    plugin_code: Optional[str]


def _existing_kind_names() -> List[str]:
    names = list(CORE_KIND_NAMES)
    if os.path.isdir(KINDS_DIR):
        for fname in os.listdir(KINDS_DIR):
            if fname.endswith(".py") and not fname.startswith("_"):
                names.append(fname[:-3])
    return names


def propose_new_kind() -> Optional[KindProposal]:
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        print("[kind_generator] ANTHROPIC_API_KEY未設定のためスキップ")
        return None

    existing = _existing_kind_names()
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"既に対応済みのkind: {existing}\n"
                    "これらと重複しない新しいkindを1つ提案してください。"
                ),
            }
        ],
    )
    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    try:
        data = json.loads(text)
        return KindProposal(
            kind_name=str(data["kind_name"]),
            niche_seed=str(data["niche_seed"]),
            keywords=[str(k) for k in data["keywords"]],
            requires_paid_api=bool(data["requires_paid_api"]),
            api_notes=str(data.get("api_notes", "")),
            plugin_code=data.get("plugin_code"),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[kind_generator] AI提案のパースに失敗: {e}\n出力: {text[:500]!r}")
        return None


def validate_plugin_code(code: str) -> tuple:
    """生成コードをASTで静的検証する。危険な要素が無いことを確認するまで
    このコードは一切実行・使用してはならない。"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"構文エラー: {e}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = (
                [alias.name.split(".")[0] for alias in node.names]
                if isinstance(node, ast.Import)
                else [(node.module or "").split(".")[0]]
            )
            for mod in module_names:
                if mod not in ALLOWED_IMPORT_MODULES:
                    return False, f"許可されていないimportです: {mod}"

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALL_NAMES:
                return False, f"禁止された関数呼び出しです: {func.id}"

        if isinstance(node, ast.Attribute):
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id in FORBIDDEN_ATTR_ROOTS:
                return False, f"禁止されたモジュールへのアクセスです: {root.id}"

        if isinstance(node, ast.Name) and node.id in FORBIDDEN_CALL_NAMES:
            return False, f"禁止された識別子の使用です: {node.id}"

    required = {"KIND_NAME", "KEYWORDS", "fetch", "build_html"}
    defined = {
        n.name if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) else n.targets[0].id
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        or (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name))
    }
    missing = required - defined
    if missing:
        return False, f"契約に必要な定義が不足しています: {missing}"

    return True, ""


_VALID_KIND_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def is_valid_kind_name(name: str) -> bool:
    """kind_nameはそのままファイル名(src/kinds/{kind_name}.py)・Pythonモジュール名
    として使われるため、パストラバーサルや不正な文字列を防ぐために検証する。"""
    return bool(_VALID_KIND_NAME.match(name)) and name not in CORE_KIND_NAMES


def test_plugin(proposal: KindProposal) -> tuple:
    """検証を通ったコードを実際にモジュールとして読み込み、外部APIへの
    fetch()呼び出しとbuild_html()呼び出しを試す。ここで失敗したら
    (LLMがAPIを幻覚した等)PRは作成しない。"""
    tmp_path = os.path.join(KINDS_DIR, f"_test_{proposal.kind_name}.py")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("import requests\n\n")
            f.write(proposal.plugin_code)

        spec = importlib.util.spec_from_file_location(f"_test_{proposal.kind_name}", tmp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        summary, sources, raw = module.fetch(proposal.niche_seed)
        if not summary:
            return False, "fetch()がdata_summaryを返しませんでした"
        html = module.build_html(proposal.niche_seed, raw, sources)
        if not html or "<html" not in html.lower():
            return False, "build_html()が有効なHTMLを返しませんでした"
        return True, f"fetch()結果: {summary[:200]}\nbuild_html()文字数: {len(html)}"
    except Exception as e:
        return False, f"実行時エラー: {e}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _github_token() -> Optional[str]:
    """git remoteのURLに埋め込まれたPATを抽出する(新規env var不要)。"""
    result = subprocess.run(
        ["git", "-C", REPO_ROOT, "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    match = re.search(r"https://([^@]+)@github\.com", result.stdout)
    return match.group(1) if match else None


def _run_git(*args) -> None:
    subprocess.run(["git", "-C", REPO_ROOT] + list(args), check=True, capture_output=True, text=True)


def create_kind_pr(proposal: KindProposal, test_output: str) -> Optional[str]:
    branch = f"auto-kind/{proposal.kind_name}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    plugin_path = os.path.join(KINDS_DIR, f"{proposal.kind_name}.py")

    try:
        _run_git("checkout", "-b", branch)

        with open(plugin_path, "w", encoding="utf-8") as f:
            f.write(f'"""kind_generator.py が自動生成したプラグイン: {proposal.kind_name}"""\n\n')
            f.write("import requests\n\n")
            f.write(proposal.plugin_code)
            f.write("\n")

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config["seed_niches"].append(proposal.niche_seed)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

        _run_git("add", f"src/kinds/{proposal.kind_name}.py", "config.yaml")
        _run_git("commit", "-m", f"新kind自動提案: {proposal.kind_name}")
        _run_git("push", "-u", "origin", branch)
    finally:
        _run_git("checkout", "main")

    token = _github_token()
    if not token:
        print("[kind_generator] GitHubトークンが取得できずPR作成をスキップしました")
        return None

    body = (
        f"## AIが自動提案した新kind: `{proposal.kind_name}`\n\n"
        f"**追加ニッチ**: {proposal.niche_seed}\n"
        f"**キーワード**: {', '.join(proposal.keywords)}\n"
        f"**使用API**: {proposal.api_notes}\n\n"
        f"### テスト実行結果\n```\n{test_output}\n```\n\n"
        "静的検証(AST)・実データでの動作テストを通過しています。"
        "内容を確認の上、問題なければマージしてください。"
    )
    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": f"新kind自動提案: {proposal.kind_name}", "head": branch, "base": "main", "body": body},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


def create_paid_api_issue(proposal: KindProposal) -> Optional[str]:
    token = _github_token()
    if not token:
        print("[kind_generator] GitHubトークンが取得できずIssue作成をスキップしました")
        return None

    body = (
        f"AIが提案した新kind `{proposal.kind_name}` は、支払い/アカウント登録が"
        f"必要なAPIを使う必要があります。\n\n**詳細**: {proposal.api_notes}\n\n"
        "対応する場合は該当APIのアカウント作成・キー取得を行い、"
        f".envに設定した上で改めて実装を進めてください。"
    )
    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": f"要対応: {proposal.kind_name}には有料/要登録APIが必要", "body": body},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


def main() -> None:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config.get("kind_generator", {}).get("enabled", False):
        print("[kind_generator] kind_generator.enabled=false のため何もしません")
        return

    proposal = propose_new_kind()
    if proposal is None:
        return

    if not is_valid_kind_name(proposal.kind_name):
        print(f"[kind_generator] kind_nameが不正なため却下: {proposal.kind_name!r}")
        return

    # 実際にAnthropic APIを呼び出せた時点でコストが発生している
    survival = config["survival"]
    st = state_mod.load_state(survival["starting_balance_usd"])
    state_mod.log_event(
        st, "cost", "新kind生成コスト", -ESTIMATED_COST_PER_KIND_GENERATION_USD
    )
    state_mod.save_state(st)

    if proposal.requires_paid_api:
        url = create_paid_api_issue(proposal)
        print(f"[kind_generator] 要対応Issueを作成しました: {url}")
        return

    ok, reason = validate_plugin_code(proposal.plugin_code)
    if not ok:
        print(f"[kind_generator] 静的検証で却下: {reason}")
        return

    ok, output = test_plugin(proposal)
    if not ok:
        print(f"[kind_generator] 動作テストで却下: {output}")
        return

    url = create_kind_pr(proposal, output)
    print(f"[kind_generator] PRを作成しました: {url}")


if __name__ == "__main__":
    main()
