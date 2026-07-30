"""
quality_gate.py
----------------
「価格が間違ってる機会を探す」の逆で、ここでは
"公開して問題ないか"を機械的に判定するゲート。

Google の scaled content abuse / YouTube の inauthentic content
ポリシーが問題にしているのは「薄い」「テンプレの繰り返し」
「既存コンテンツの焼き直し」なので、その3点を最低限チェックする。

これはあくまで簡易ヒューリスティックであり、
「これを通せばポリシー的に安全」を保証するものではない。
最終的な公開可否の責任は運用者にある。
"""

import difflib
from typing import List


def word_count(text: str) -> int:
    return len(text)  # 日本語は文字数ベースで簡易カウント


def similarity_to_existing(text: str, existing_texts: List[str]) -> float:
    if not existing_texts:
        return 0.0
    return max(
        difflib.SequenceMatcher(None, text, existing).ratio()
        for existing in existing_texts
    )


def passes_quality_gate(
    text: str,
    existing_texts: List[str],
    min_word_count: int,
    max_similarity_ratio: float,
) -> tuple[bool, str]:
    wc = word_count(text)
    if wc < min_word_count:
        return False, f"文字数不足 ({wc} < {min_word_count})"

    sim = similarity_to_existing(text, existing_texts)
    if sim > max_similarity_ratio:
        return False, f"既存コンテンツとの類似度が高すぎる ({sim:.2f})"

    return True, "OK"
