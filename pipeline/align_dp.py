from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

from .config import STATES, AUTO_GOOD_THRESHOLD, NEEDS_REVIEW_THRESHOLD
from .segment import Sentence


@dataclass(frozen=True)
class AlignmentRow:
    en_text: str
    zh_text: str
    score: float | None
    status: str
    chapter_id: str
    align_id: str
    en_ids: str
    zh_ids: str
    align_type: str
    note: str = ""


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        return vec
    return vec / norm


def _group_embedding(emb: np.ndarray, start: int, size: int) -> np.ndarray:
    if size <= 0:
        raise ValueError("size must be positive")
    return _normalize(emb[start:start + size].mean(axis=0))


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def classify_status(score: float | None, align_type: str) -> str:
    if align_type == "1-0":
        return "skip_en"
    if align_type == "0-1":
        return "skip_zh"
    if score is None or math.isnan(score):
        return "bad_suspect"
    if score >= AUTO_GOOD_THRESHOLD:
        return "auto_good"
    if score >= NEEDS_REVIEW_THRESHOLD:
        return "needs_review"
    return "bad_suspect"


def _state_penalty(a: int, b: int, penalty_12_or_21: float, penalty_22: float) -> float:
    if (a, b) == (1, 1):
        return 0.0
    if (a, b) in {(1, 2), (2, 1)}:
        return penalty_12_or_21
    if (a, b) == (2, 2):
        return penalty_22
    return 0.0


def align_chapter_dp(
    en_sentences: Sequence[Sentence],
    zh_sentences: Sequence[Sentence],
    en_embeddings: np.ndarray,
    zh_embeddings: np.ndarray,
    chapter_id: str,
    skip_penalty: float = -0.30,
    size_penalty_12_or_21: float = 0.03,
    size_penalty_22: float = 0.06,
) -> list[AlignmentRow]:
    """Monotonic DP alignment over small local states.

    The DP maximizes accumulated semantic similarity with mild penalties for grouped
    matches and skips. It is intentionally simple for v1: no reranker, no global
    chapter repair, no interactive correction layer.
    """
    n = len(en_sentences)
    m = len(zh_sentences)
    if en_embeddings.shape[0] != n or zh_embeddings.shape[0] != m:
        raise ValueError(
            f"Embedding row mismatch: en {en_embeddings.shape[0]} vs {n}, "
            f"zh {zh_embeddings.shape[0]} vs {m}"
        )

    dp = np.full((n + 1, m + 1), -np.inf, dtype=np.float32)
    back: dict[tuple[int, int], tuple[int, int, tuple[int, int], float | None]] = {}
    dp[0, 0] = 0.0

    for i in range(n + 1):
        for j in range(m + 1):
            if not np.isfinite(dp[i, j]):
                continue
            for a, b in STATES:
                ni, nj = i + a, j + b
                if ni > n or nj > m:
                    continue

                if a == 0 and b == 0:
                    continue
                if a == 0 or b == 0:
                    raw_score = None
                    transition = skip_penalty
                else:
                    en_vec = _group_embedding(en_embeddings, i, a)
                    zh_vec = _group_embedding(zh_embeddings, j, b)
                    raw_score = _cosine(en_vec, zh_vec)
                    transition = raw_score - _state_penalty(
                        a,
                        b,
                        penalty_12_or_21=size_penalty_12_or_21,
                        penalty_22=size_penalty_22,
                    )

                candidate = float(dp[i, j]) + float(transition)
                if candidate > float(dp[ni, nj]):
                    dp[ni, nj] = candidate
                    back[(ni, nj)] = (i, j, (a, b), raw_score)

    if (n, m) not in back and (n, m) != (0, 0):
        raise RuntimeError("DP failed to produce a complete path")

    steps: list[tuple[int, int, tuple[int, int], float | None]] = []
    cur = (n, m)
    while cur != (0, 0):
        prev_i, prev_j, state, score = back[cur]
        steps.append((prev_i, prev_j, state, score))
        cur = (prev_i, prev_j)
    steps.reverse()

    rows: list[AlignmentRow] = []
    for idx, (i, j, (a, b), score) in enumerate(steps):
        en_group = list(en_sentences[i:i + a]) if a else []
        zh_group = list(zh_sentences[j:j + b]) if b else []
        align_type = f"{a}-{b}"
        status = classify_status(score, align_type=align_type)
        rows.append(
            AlignmentRow(
                en_text=" ".join(s.text for s in en_group),
                zh_text="".join(s.text for s in zh_group),
                score=None if score is None else round(float(score), 4),
                status=status,
                chapter_id=chapter_id,
                align_id=f"{chapter_id}:{idx:05d}",
                en_ids=",".join(s.sent_id for s in en_group),
                zh_ids=",".join(s.sent_id for s in zh_group),
                align_type=align_type,
            )
        )

    return rows
