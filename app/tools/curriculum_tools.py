from __future__ import annotations

import re
from typing import Dict, Any


def validate_mermaid_syntax(mermaid_code: str) -> Dict[str, Any]:
    """Validates basic syntax correctness for Mermaid.js diagrams.

    Args:
        mermaid_code: The Mermaid diagram definition string (e.g. flowchart TD, sequenceDiagram).

    Returns:
        Dict with 'is_valid' boolean, detected diagram type, and any syntax warning messages.
    """
    cleaned = mermaid_code.strip()
    valid_prefixes = (
        "graph ",
        "flowchart ",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "erDiagram",
        "gantt",
        "pie ",
        "mindmap",
        "timeline",
    )

    is_valid = any(cleaned.startswith(p) for p in valid_prefixes) or "-->" in cleaned or "->>" in cleaned
    detected_type = "unknown"
    for p in valid_prefixes:
        if cleaned.startswith(p):
            detected_type = p.strip()
            break

    warnings = []
    if "(" in cleaned and not ")" in cleaned:
        warnings.append("Unclosed parentheses in node label")
    if "[" in cleaned and not "]" in cleaned:
        warnings.append("Unclosed brackets in node label")

    return {
        "is_valid": is_valid,
        "detected_type": detected_type,
        "warnings": warnings,
        "char_count": len(cleaned),
    }


def estimate_reading_level(text: str) -> Dict[str, Any]:
    """Estimates the reading and complexity level of the generated educational text.

    Args:
        text: The lesson text string to analyze.

    Returns:
        Dict with word count, sentence count, average word length, and estimated grade bracket.
    """
    words = re.findall(r"\b\w+\b", text)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]

    word_count = len(words)
    sentence_count = max(1, len(sentences))
    avg_sentence_len = word_count / sentence_count
    long_words = [w for w in words if len(w) > 6]
    long_word_ratio = len(long_words) / max(1, word_count)

    # Simplified heuristic grade level calculation
    if avg_sentence_len < 10 and long_word_ratio < 0.15:
        grade = "Elementary (Grades 3-5)"
    elif avg_sentence_len < 16 and long_word_ratio < 0.25:
        grade = "Middle School (Grades 6-8)"
    elif avg_sentence_len < 22 and long_word_ratio < 0.35:
        grade = "High School (Grades 9-12)"
    else:
        grade = "Advanced / College"

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sentence_len, 2),
        "long_word_percentage": round(long_word_ratio * 100, 1),
        "estimated_grade_bracket": grade,
    }
