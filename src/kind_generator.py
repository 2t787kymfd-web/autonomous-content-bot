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
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urljoin, urlparse

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
ALLOWED_IMPORT_MODULES = {"json", "datetime", "typing", "requests"}

# --- 検証は「許可リスト」方式(禁止リストではなく) ---
# 生成コード中で「参照(Load)」してよい自由識別子(ローカルで束縛された変数名は
# 別途自動的に許可される)。eval/exec/getattr/globals/__builtins__ 等はここに
# 含めない限り一切参照できない。
SAFE_GLOBAL_NAMES = {
    "requests", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "len", "range", "enumerate", "zip", "sorted", "reversed", "sum", "min", "max",
    "round", "abs", "isinstance", "print",
    "None", "True", "False",
    "Exception", "ValueError", "KeyError", "TypeError", "IndexError",
    "AttributeError", "StopIteration", "RuntimeError",
}
# dunder属性(__で始まる属性)経由でのPythonサンドボックス脱出
# (例: ().__class__.__bases__[0].__subclasses__() ...)を防ぐため、
# 既知の危険な属性名を名指しで塞ぐのではなく「__で始まる属性への
# アクセスは理由を問わず一律拒否」にする(未知の迂回経路を潰し漏らさないため)。
# プラグインコードが正当にdunder属性を必要とする場面は無い想定。
# ツールプラグインに正当な用途が無い構文(Pythonバージョン間で変わりやすい
# 「許可する構文一覧」ではなく、安定した「禁止する構文一覧」として持つ)
FORBIDDEN_NODE_TYPES = (
    ast.ClassDef, ast.Global, ast.Nonlocal,
    ast.Yield, ast.YieldFrom, ast.Await, ast.AsyncFunctionDef,
    ast.AsyncFor, ast.AsyncWith, ast.With, ast.Delete,
)
# Lambdaは意図的に許可している: 中身の自由識別子(getattr等)やdunder属性は
# 通常の関数と同じくast.walk()で個別に検査されるため、Lambdaというノード種別
# 自体を禁止しても追加のセキュリティ効果は無く、sorted(x, key=lambda ...)等の
# 正当な用途を不必要に妨げるだけだった。

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
    """tool_builder.pyの契約: ページ本文(<h1>から出典表記まで)のHTML断片を返す。
    サイト共通のヘッダー/フッター/CSS/広告タグはtool_builder.py側が自動で
    付与するため、<!doctype html>/<html>/<head>/<body>タグや、独自の<style>は
    一切書かないこと。既存の他ページと見た目・機能を統一するため。"""
    return (
        f'<h1>🔍 {niche}</h1>'
        '<p>データの概要説明。</p>'
        '<table><tr><th>項目</th><th>値</th></tr>...</table>'
        '<div class="source">データ出典: ...</div>'
    )
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
- 【最重要・違反すると自動的に却下されます】build_html()の戻り値に
  <!doctype、<html、<head、<body、<style のいずれの文字列も含めないこと。
  例に示した通り、返すのは<h1>から始まる本文断片のみです。
  誤った例(絶対にやらないこと): return "<!doctype html><html>...<style>...</style>...</html>"
  正しい例: return f"<h1>{{niche}}</h1><table>...</table><div class=\"source\">...</div>"
  サイト共通のヘッダー/フッター/CSS/広告タグはtool_builder.py側が自動で
  付与するので、あなたがこれらを書くと二重になりテストで却下されます。
- 生成コードで使ってよいのは requests, json, datetime, typing のみ
- HTTPリクエストは requests.get() のみ使用すること(POST等の送信系メソッドは不可)
- eval/exec/compile/__import__/open は絶対に使わないこと
- os/sys/subprocess/socket/shutil には一切アクセスしないこと
- __で始まる属性(__class__, __globals__ 等)には一切アクセスしないこと
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


def _strip_markdown_fence(text: str) -> str:
    """「JSON形式のみで出力」と指示しても```json ... ```で囲んで返してくることが
    あるため、コードフェンスがあれば取り除く。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def propose_new_kind(st: dict) -> Optional[KindProposal]:
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        print("[kind_generator] ANTHROPIC_API_KEY未設定のためスキップ")
        return None

    existing = _existing_kind_names()
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
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
    # 実際にAPI呼び出しが成功した時点でコストは発生している(この後の
    # JSONパースが失敗しても課金自体は起きているため、パース結果を待たずに
    # ここで記録する)
    state_mod.log_event(
        st, "cost", "新kind生成コスト", -ESTIMATED_COST_PER_KIND_GENERATION_USD
    )
    state_mod.save_state(st)

    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    try:
        data = json.loads(_strip_markdown_fence(text))
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


def _names_bound_by_target(target) -> set:
    """代入・for・comprehension等の「束縛」対象からローカル変数名を集める。"""
    names = set()
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.update(_names_bound_by_target(elt))
    elif isinstance(target, ast.Starred):
        names.update(_names_bound_by_target(target.value))
    return names


def _collect_bound_names(tree) -> set:
    """コード全体でどこかしら「束縛」される識別子を集める(関数定義・引数・
    代入・for・内包表記・except as・import)。スコープ単位の厳密な解決はせず
    ファイル全体で緩く集約するが、安全側としては十分:
    「どこにも束縛されていない裸の名前」だけを次のチェックで疑う。"""
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                bound.add(node.name)
            args = node.args
            for arg in list(args.args) + list(args.kwonlyargs) + list(getattr(args, "posonlyargs", [])):
                bound.add(arg.arg)
            if args.vararg:
                bound.add(args.vararg.arg)
            if args.kwarg:
                bound.add(args.kwarg.arg)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                bound.update(_names_bound_by_target(target))
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            bound.update(_names_bound_by_target(node.target))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            bound.update(_names_bound_by_target(node.target))
        elif isinstance(node, (ast.comprehension,)):
            bound.update(_names_bound_by_target(node.target))
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
    return bound


def validate_plugin_code(code: str) -> tuple:
    """生成コードをASTで静的検証する。許可リスト方式:
    - importは許可された標準モジュールのみ
    - 参照してよい「自由識別子」(ローカルで束縛されていないもの)は
      SAFE_GLOBAL_NAMES のみに限定する(getattr/globals/__builtins__/eval/exec等は
      ここに含まれないため、リテラル名を使わない難読化を試みても素通りしない)
    - dunder属性(__class__ 等)経由のサンドボックス脱出は属性名そのものを拒否
    危険な要素が無いことを確認するまでこのコードは一切実行・使用してはならない。"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"構文エラー: {e}"

    bound_names = _collect_bound_names(tree)
    allowed_free_names = SAFE_GLOBAL_NAMES | bound_names

    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODE_TYPES):
            return False, f"許可されていない構文です: {type(node).__name__}"

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = (
                [alias.name.split(".")[0] for alias in node.names]
                if isinstance(node, ast.Import)
                else [(node.module or "").split(".")[0]]
            )
            for mod in module_names:
                if mod not in ALLOWED_IMPORT_MODULES:
                    return False, f"許可されていないimportです: {mod}"

        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False, f"dunder属性へのアクセスは一律禁止です: {node.attr}"

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in allowed_free_names:
                return False, f"許可されていない識別子の参照です: {node.id}"

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


MAX_TEST_RESPONSE_BYTES = 2_000_000
MAX_TEST_TIMEOUT_SECONDS = 10
MAX_TEST_REDIRECTS = 3
BLOCKED_HOSTNAMES = {"169.254.169.254", "metadata.google.internal", "metadata", "100.100.100.200"}

# ipaddressモジュールのis_private/is_link_local等では捕捉できない範囲を
# 明示的に追加で拒否する。
# - 100.64.0.0/10 (RFC 6598 共有アドレス空間/CGN用): Pythonのipaddressは
#   これを「プライベート」と判定しないが、Alibaba Cloudのメタデータ
#   エンドポイント(100.100.100.200)はこの範囲に属する。169.254.169.254
#   (AWS/GCP/Azure/DigitalOcean等)はis_link_localで既にカバー済み。
_ADDITIONAL_BLOCKED_NETWORKS = [
    ipaddress.ip_network("100.64.0.0/10"),
]


def _resolve_safe_ip(hostname: str) -> str:
    """ホスト名を解決し、プライベート/ループバック/リンクローカル/クラウド
    メタデータIPでないことを確認した上で、実際に使うIPを1つ確定して返す。
    ここで確定したIPを接続時にもそのまま使う(DNS rebinding対策。
    「検証した時点のIP」と「実際に接続する時点のIP」がズレないようにする)。"""
    if not hostname or hostname.lower() in BLOCKED_HOSTNAMES:
        raise ValueError(f"アクセスが許可されていないホストです: {hostname}")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"名前解決に失敗したホストです: {hostname}")
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            continue
        if any(ip in net for net in _ADDITIONAL_BLOCKED_NETWORKS):
            continue
        return str(ip)
    raise ValueError(f"アクセスが許可されていないホストです(プライベートIP等): {hostname}")


class _PinnedDNSGuard:
    """socket.getaddrinfoを一時的に差し替え、指定ホスト名の名前解決を
    _resolve_safe_ip()で確定させたIPに固定する。with文の範囲内でのみ有効。"""

    def __init__(self, hostname: str, pinned_ip: str):
        self.hostname = hostname
        self.pinned_ip = pinned_ip
        self._original = socket.getaddrinfo

    def __enter__(self):
        original = self._original
        hostname, pinned_ip = self.hostname, self.pinned_ip

        def patched(host, *args, **kwargs):
            if host == hostname:
                host = pinned_ip
            return original(host, *args, **kwargs)

        socket.getaddrinfo = patched
        return self

    def __exit__(self, *exc):
        socket.getaddrinfo = self._original


class _SafeRequestsModule:
    """test_plugin() 実行時のみ、生成コードから見える `requests` をこれに
    差し替える。生成コードが未レビューの状態で実際に外部へHTTPリクエストを
    送るため、以下を強制する:
    - GETのみ許可(POST等でのデータ送信・外部への書き込みを一切許さない)
    - HTTPSのみ、プライベート/リンクローカル/クラウドメタデータIP拒否
    - DNS解決結果をピン留めして接続する(DNS rebinding対策)
    - 3xxリダイレクトは自動追従させず、リダイレクト先ごとに同じ検証をやり直す
      (でなければこれまでの検証が全て無意味になる)
    - タイムアウト強制(最大10秒)・レスポンスサイズ上限(2MB)
    """

    def get(self, url, **kwargs):
        return self._safe_get(url, **kwargs)

    def post(self, url, **kwargs):
        raise ValueError("test_plugin実行時はPOST等の送信系メソッドを許可していません(GETのみ)")

    def _safe_get(self, url: str, redirects_left: int = MAX_TEST_REDIRECTS, **kwargs):
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"httpsのみ許可されています: {url}")

        pinned_ip = _resolve_safe_ip(parsed.hostname or "")
        timeout = min(kwargs.pop("timeout", None) or MAX_TEST_TIMEOUT_SECONDS, MAX_TEST_TIMEOUT_SECONDS)

        with _PinnedDNSGuard(parsed.hostname, pinned_ip):
            resp = requests.get(
                url, timeout=timeout, stream=True, allow_redirects=False, **kwargs
            )
            is_redirect = resp.is_redirect or resp.is_permanent_redirect
            location = resp.headers.get("Location") if is_redirect else None
            if not is_redirect:
                content = resp.raw.read(MAX_TEST_RESPONSE_BYTES + 1, decode_content=True)
            resp.close()

        # with文(=DNSピン留め)を抜けてから再帰する: リダイレクト先は別ホストの
        # 可能性があるため、ピン留めがネストしない形で改めて安全性を検証し直す
        if is_redirect:
            if redirects_left <= 0:
                raise ValueError("リダイレクト回数が上限を超えました")
            if not location:
                raise ValueError("リダイレクト先が不明です")
            next_url = urljoin(url, location)
            return self._safe_get(next_url, redirects_left=redirects_left - 1, **kwargs)

        if len(content) > MAX_TEST_RESPONSE_BYTES:
            raise ValueError("レスポンスサイズが上限を超えました")
        resp._content = content
        return resp


def test_plugin(proposal: KindProposal) -> tuple:
    """検証を通ったコードを実際にモジュールとして読み込み、外部APIへの
    fetch()呼び出しとbuild_html()呼び出しを試す。ここで失敗したら
    (LLMがAPIを幻覚した等)PRは作成しない。

    この時点のコードはまだ人間のレビュー前なので、requestsは本物ではなく
    _SafeRequestsModule に差し替えて実行する(SSRF・タイムアウト・
    レスポンスサイズの安全装置を強制するため)。生成コードが`import requests`を
    自分で書いた場合でも安全ラッパーが使われるよう、sys.modules レベルで
    差し替える(module.requests への直接注入だけでは、生成コード自身の
    `import requests`によって本物のrequestsに上書きされてしまうため)。"""
    tmp_path = os.path.join(KINDS_DIR, f"_test_{proposal.kind_name}.py")
    original_requests_module = sys.modules.get("requests")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(proposal.plugin_code)

        safe_requests = _SafeRequestsModule()
        sys.modules["requests"] = safe_requests

        spec = importlib.util.spec_from_file_location(f"_test_{proposal.kind_name}", tmp_path)
        module = importlib.util.module_from_spec(spec)
        module.requests = safe_requests
        spec.loader.exec_module(module)

        summary, sources, raw = module.fetch(proposal.niche_seed)
        if not summary:
            return False, "fetch()がdata_summaryを返しませんでした"
        html = module.build_html(proposal.niche_seed, raw, sources)
        if not html or "<" not in html:
            return False, "build_html()が空、またはHTMLらしき内容を返しませんでした"
        lowered = html.lower()
        forbidden_tags = ("<!doctype", "<html", "<head", "<body", "<style")
        if any(tag in lowered for tag in forbidden_tags):
            return False, (
                "build_html()が本文の断片ではなく完全なHTML文書/独自<style>を"
                "返しています(サイト共通のヘッダー/フッター/CSSと二重になるため契約違反)"
            )
        return True, f"fetch()結果: {summary[:200]}\nbuild_html()文字数: {len(html)}"
    except Exception as e:
        return False, f"実行時エラー: {e}"
    finally:
        if original_requests_module is not None:
            sys.modules["requests"] = original_requests_module
        else:
            sys.modules.pop("requests", None)
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


def _append_seed_niche(niche_seed: str) -> None:
    """config.yamlをyaml.safe_load/safe_dumpで往復させるとコメントや書式が
    全て失われるため、seed_niches: セクションの末尾にテキストとして1行だけ
    追記する(ファイルの他の部分には一切触れない)。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start = None
    for i, line in enumerate(lines):
        if line.startswith("seed_niches:"):
            start = i
            break
    if start is None:
        raise ValueError("config.yamlにseed_niches:セクションが見つかりません")

    end = start + 1
    while end < len(lines) and lines[end].startswith("  - "):
        end += 1

    escaped = niche_seed.replace('"', '\\"')
    lines.insert(end, f'  - "{escaped}"\n')

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def create_kind_pr(proposal: KindProposal, test_output: str) -> Optional[str]:
    branch = f"auto-kind/{proposal.kind_name}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    plugin_path = os.path.join(KINDS_DIR, f"{proposal.kind_name}.py")

    try:
        # -b(既存だと失敗)ではなく-B(既存でも作り直す)を使う。
        # 同名kindが過去に提案・却下されて古いローカルブランチが残っている
        # ケースがあり得るため(実際に発生した)、常に現在のmainから作り直す。
        _run_git("checkout", "-B", branch, "main")

        with open(plugin_path, "w", encoding="utf-8") as f:
            f.write(f'"""kind_generator.py が自動生成したプラグイン: {proposal.kind_name}"""\n\n')
            # 生成コードが自分でimport requestsを書いていることがあるため、
            # 重複して書かないようにする
            if "import requests" not in proposal.plugin_code:
                f.write("import requests\n\n")
            f.write(proposal.plugin_code)
            f.write("\n")

        _append_seed_niche(proposal.niche_seed)

        _run_git("add", f"src/kinds/{proposal.kind_name}.py", "config.yaml")
        _run_git("commit", "-m", f"新kind自動提案: {proposal.kind_name}")
        # 同名ブランチがリモートに残っている(前回失敗時等)可能性があるため
        # force pushする。auto-kind/* ブランチは使い捨て前提で共有編集されない。
        _run_git("push", "-f", "-u", "origin", branch)
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


# 週1回のcron運用を想定。「明らかな二重起動・cron設定ミス(想定より高頻度に
# 発火する等)」だけを防ぐための短い間隔。手動での動作確認・再テストの
# 妨げにならない程度に短くしてある(週1回の間隔そのものを強制するものではない)
MIN_INTERVAL_HOURS = 6


def _too_soon_since_last_attempt(st: dict) -> bool:
    last = st.get("last_kind_generator_attempt_at")
    if last is None:
        return False
    elapsed_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() / 3600
    return elapsed_hours < MIN_INTERVAL_HOURS


def main() -> None:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config.get("kind_generator", {}).get("enabled", False):
        print("[kind_generator] kind_generator.enabled=false のため何もしません")
        return

    survival = config["survival"]
    st = state_mod.load_state(survival["starting_balance_usd"])

    if _too_soon_since_last_attempt(st):
        print(
            f"[kind_generator] 前回の試行から{MIN_INTERVAL_HOURS}時間経っていないためスキップします"
        )
        return

    proposal = propose_new_kind(st)
    # 試行したこと自体を結果に関わらず記録する(コストが発生しなかった
    # 場合=APIキー未設定等でも、意図しない連続実行の抑止として記録しておく)
    st["last_kind_generator_attempt_at"] = datetime.now(timezone.utc).isoformat()
    state_mod.save_state(st)

    if proposal is None:
        return

    if not is_valid_kind_name(proposal.kind_name):
        print(f"[kind_generator] kind_nameが不正なため却下: {proposal.kind_name!r}")
        return

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
