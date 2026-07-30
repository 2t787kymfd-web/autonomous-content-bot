"""
safe_http.py
------------
src/kinds/*.py(AIが自動生成したプラグイン)からのHTTPリクエストを、
コードレビューの有無に関わらず常に安全な経路に強制するためのモジュール。

kind_generator.py の test_plugin()(マージ前の動作確認)と、
researcher.py の research_niche()(マージ後・本番実行)の**両方**で
使う。SSRF・DNS rebinding・プライベート/クラウドメタデータIPへの
アクセスは「コードが人間にレビューされたかどうか」とは無関係な
ネットワーク層のリスクであり、レビュー済みコードであっても実行時に
渡される値(niche文字列等、外部の影響を受けうる)次第では危険な宛先に
アクセスしうるため、レビュー後の本番実行でも同じ制約を外さない。
"""

import ipaddress
import socket
import sys
from contextlib import contextmanager
from urllib.parse import urljoin, urlparse

import requests

MAX_RESPONSE_BYTES = 2_000_000
MAX_TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 3
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


class SafeRequestsModule:
    """src/kinds/*.py プラグインから見える `requests` をこれに差し替える。
    マージ前のテストか本番実行かに関わらず常に以下を強制する:
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
        raise ValueError("POST等の送信系メソッドは許可していません(GETのみ)")

    def _safe_get(self, url: str, redirects_left: int = MAX_REDIRECTS, **kwargs):
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"httpsのみ許可されています: {url}")

        pinned_ip = _resolve_safe_ip(parsed.hostname or "")
        timeout = min(kwargs.pop("timeout", None) or MAX_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS)

        with _PinnedDNSGuard(parsed.hostname, pinned_ip):
            resp = requests.get(
                url, timeout=timeout, stream=True, allow_redirects=False, **kwargs
            )
            is_redirect = resp.is_redirect or resp.is_permanent_redirect
            location = resp.headers.get("Location") if is_redirect else None
            if not is_redirect:
                content = resp.raw.read(MAX_RESPONSE_BYTES + 1, decode_content=True)
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

        if len(content) > MAX_RESPONSE_BYTES:
            raise ValueError("レスポンスサイズが上限を超えました")
        resp._content = content
        return resp


@contextmanager
def patched_requests():
    """このwithブロック内では、`import requests`(sys.modules経由)も
    直接の`requests`参照も、両方SafeRequestsModuleに差し替わる。
    ブロックを抜けると必ず元のrequestsモジュールに復元される。"""
    original = sys.modules.get("requests")
    safe = SafeRequestsModule()
    sys.modules["requests"] = safe
    try:
        yield safe
    finally:
        if original is not None:
            sys.modules["requests"] = original
        else:
            sys.modules.pop("requests", None)
