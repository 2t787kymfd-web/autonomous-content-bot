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

import json
import os
import re
from .researcher import ResearchResult

try:
    import anthropic
except ImportError:
    anthropic = None


def _strip_markdown_fence(text: str) -> str:
    """「JSON形式のみで出力」と指示しても```json ... ```で囲んで返してくることが
    あるため、コードフェンスがあれば取り除く(kind_generator.pyと同種の対策)。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


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


DESCRIPTION_SYSTEM_PROMPT = """あなたはデータツールサイトの編集者です。
与えられたニッチと一次データをもとに、そのツールページに掲載する
「説明文」と「FAQ」を作成してください。

説明文の要件:
- 400〜800字程度
- 構成は「導入(このツールが何をするものか)→データの読み方
  (表の見方・用語説明)→今回のデータのポイント(raw_dataに含まれる
  実際の数値に必ず具体的に言及すること)→免責事項/出典」の順
- 一般論の水増しではなく、渡された一次データを中心に据えること

FAQの要件:
- 3〜5問。読者が実際に疑問に思いそうな具体的な質問と、
  簡潔で正確な回答

回答は必ず次のJSON形式のみで出力してください(他のテキストを含めない):
{
  "description": "説明文の本文(HTMLタグは含めない、プレーンテキスト)",
  "faq": [{"q": "質問文", "a": "回答文"}, ...]
}
"""


def generate_tool_description(niche: str, raw_data: dict, sources: list) -> dict:
    """ツールページ用の説明文・FAQを生成する。戻り値:
    {"description": str, "faq": [{"q": str, "a": str}, ...]}
    kind単位で初回のみ呼ばれ、呼び出し元(main_loop.py)がキャッシュして
    使い回す想定(毎サイクル呼ぶものではない)。
    ANTHROPIC_API_KEY未設定時はダミーのフォールバック文言を返す。"""
    fallback = {
        "description": (
            f"{niche}に関するデータツールです。"
            "(ANTHROPIC_API_KEY未設定のため説明文は自動生成されていません)"
        ),
        "faq": [],
    }
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return fallback

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=DESCRIPTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"ニッチ: {niche}\n"
                    f"一次データ: {json.dumps(raw_data, ensure_ascii=False, default=str)}\n"
                    f"出典: {sources}\n\n"
                    "上記のデータについて、説明文とFAQを作成してください。"
                ),
            }
        ],
    )
    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    try:
        data = json.loads(_strip_markdown_fence(text))
        description = str(data["description"])
        faq = [
            {"q": str(item["q"]), "a": str(item["a"])}
            for item in data.get("faq", [])
            if "q" in item and "a" in item
        ]
        return {"description": description, "faq": faq}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[generator] 説明文生成のパースに失敗: {e}\n出力: {text[:300]!r}")
        return fallback
