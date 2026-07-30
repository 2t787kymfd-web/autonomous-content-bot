"""
generator.py
-------------
「いくら賭けるか、どっち側にするかを決める」に相当する部分の
コンテンツ版 = 実際に公開する記事/ツールページを生成する。

重要: テンプレ的な量産(scaled content abuse / inauthentic
content 判定のリスク)を避けるため、
  1. researcher.py で取得した「独自データ」を必ず本文に組み込む
  2. 構成・切り口をニッチごとに変えるようプロンプトで明示指示する
  3. データが無い場合は生成そのものをスキップする
という設計にしている。
"""

import os
from .researcher import ResearchResult

try:
    import anthropic
except ImportError:
    anthropic = None


SYSTEM_PROMPT = """あなたはWebコンテンツの編集者です。
与えられたニッチと一次データをもとに、次の条件を満たす記事を書いてください。

- 単なる一般論の要約ではなく、渡されたデータを中心に据えること
- 見出し構成はニッチごとに変え、テンプレートの繰り返しにしないこと
- 読者が実際に判断・行動できる具体的な情報を含めること
- 400語以上、かつ水増しではなく情報密度を保つこと
- データの出典を明記すること
"""


def generate_article(research: ResearchResult) -> str:
    if not research.has_unique_data:
        # ガード: 独自データが無いのに記事を作らせない
        raise ValueError(
            f"'{research.niche}' には独自データがないため生成をスキップします。"
            " researcher.py にデータソースを実装してください。"
        )

    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        # サンドボックス/APIキー未設定時のフォールバック(動作確認用)
        return (
            f"# {research.niche}\n\n"
            f"(ダミー出力: ANTHROPIC_API_KEY未設定のため実生成は行われていません)\n\n"
            f"データ: {research.data_summary}\n"
            f"出典: {', '.join(research.sources)}\n"
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"ニッチ: {research.niche}\n"
                    f"一次データ: {research.data_summary}\n"
                    f"出典: {research.sources}\n\n"
                    "上記のデータを中心に、条件を満たす記事を書いてください。"
                ),
            }
        ],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
