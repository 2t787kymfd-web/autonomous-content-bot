"""
tool_content.py
----------------
kind別の説明文・FAQ(src/generator.py の generate_tool_description() が
生成する)を data/tool_descriptions.json に永続化する。「初回のみAI生成し
使い回す」ためのキャッシュ層。state.py(残高・履歴等の可変な運用状態)とは
別ファイルに分離している(こちらはコンテンツそのもの、更新頻度も性質も違うため)。
"""

import json
import os
from datetime import datetime, timezone

TOOL_DESCRIPTIONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "tool_descriptions.json"
)


def load() -> dict:
    if os.path.exists(TOOL_DESCRIPTIONS_PATH):
        with open(TOOL_DESCRIPTIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(content: dict) -> None:
    os.makedirs(os.path.dirname(TOOL_DESCRIPTIONS_PATH), exist_ok=True)
    with open(TOOL_DESCRIPTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)


def get_or_generate(content: dict, kind: str, niche: str, raw_data: dict, sources: list) -> dict:
    """content(load()の戻り値)にkindが無ければ生成してcontentに追加し、
    呼び出し元がsave()するのを前提に更新済みcontentを返す実装ではなく、
    ここではkind単位のエントリだけを返す(呼び出し元がcontent自体を管理する)。"""
    if kind in content:
        return content[kind]

    from .generator import generate_tool_description

    generated = generate_tool_description(niche, raw_data, sources)
    entry = {
        "description": generated["description"],
        "faq": generated["faq"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    content[kind] = entry
    return entry
