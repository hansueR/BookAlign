from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "BAAI/bge-m3"
FAST_CPU_MODEL = "intfloat/multilingual-e5-small"
BALANCED_CPU_MODEL = "intfloat/multilingual-e5-base"

STATES: list[tuple[int, int]] = [
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
    (1, 0),
    (0, 1),
]

AUTO_GOOD_THRESHOLD = 0.72
NEEDS_REVIEW_THRESHOLD = 0.55

EXCEL_COLUMNS = [
    "en_text",
    "zh_text",
    "score",
    "status",
    "chapter_id",
    "align_id",
    "en_ids",
    "zh_ids",
    "align_type",
    "note",
]


@dataclass(frozen=True)
class AlignConfig:
    book_id: str
    model_name: str = DEFAULT_MODEL
    device: str = "auto"
    cache_dir: Path = Path(".align_cache")
    batch_size: int = 32
    max_chars_per_segment: int = 1200
    auto_good_threshold: float = AUTO_GOOD_THRESHOLD
    needs_review_threshold: float = NEEDS_REVIEW_THRESHOLD
    skip_penalty: float = -0.30
    size_penalty_12_or_21: float = 0.03
    size_penalty_22: float = 0.06
