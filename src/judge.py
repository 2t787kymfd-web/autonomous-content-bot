"""
judge.py
--------
Polymarket版の「価格が間違ってる機会かどうかを判断する」に相当する、
コンテンツ版の判断ステップ。

researcher.py が独自データを取得できたニッチについて、実際に
記事/ツールを生成する価値があるかをAIに評価させる。ANTHROPIC_API_KEY
未設定時は、既存の暗黙の挙動(独自データがあれば常に生成する)と
互換性のあるフォールバックで判定する。
"""

import json
import os
from dataclasses import dataclass

from .researcher import ResearchResult

try:
    import anthropic
except ImportError:
    anthropic = None


SYSTEM_PROMPT = """あなたはコンテンツ企画の判断者です。
与えられたニッチと一次データをもとに、実際に記事/ツールを作って公開する
価値があるかを判断してください。

- データが薄すぎる、または一般的すぎて独自の価値を提供できない場合はNG
- 読者が実際に役立てられる具体性がある場合はOK
- 判断結果は必ず次のJSON形式のみで出力すること(他のテキストを含めない):
  {"worth_pursuing": true または false, "reason": "一文の理由"}
"""


@dataclass
class JudgeResult:
    worth_pursuing: bool
    reason: str


def judge_niche(niche: str, research: ResearchResult) -> JudgeResult:
    if not research.has_unique_data:
        return JudgeResult(False, "独自データが無いため判断以前にスキップ")

    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        # サンドボックス/APIキー未設定時: 独自データがあれば通す(既存の暗黙挙動と互換)
        return JudgeResult(True, "ANTHROPIC_API_KEY未設定のため簡易判定(データありで許可)")

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"ニッチ: {niche}\n"
                    f"一次データ: {research.data_summary}\n"
                    f"出典: {research.sources}\n\n"
                    "上記のニッチ・データについて判断してください。"
                ),
            }
        ],
    )
    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    try:
        parsed = json.loads(text)
        return JudgeResult(bool(parsed["worth_pursuing"]), str(parsed["reason"]))
    except (json.JSONDecodeError, KeyError, TypeError):
        # パース失敗時は安全側(生成を許可)にフォールバック
        return JudgeResult(True, f"AI出力のパースに失敗したため安全側で許可: {text[:200]!r}")
