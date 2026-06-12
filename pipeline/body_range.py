from __future__ import annotations

from dataclasses import dataclass

from .epub_extract import EpubChapter


@dataclass(frozen=True)
class UnitRange:
    start: int
    end: int


@dataclass(frozen=True)
class SentenceWindow:
    window_id: str
    en_start: int
    en_end: int
    zh_start: int
    zh_end: int


def parse_unit_range(raw: str) -> UnitRange:
    value = raw.strip()
    if not value:
        raise ValueError("Unit range is required in START:END format")
    if value.count(":") != 1:
        raise ValueError(f"Invalid unit range {raw!r}: expected START:END format")

    start_raw, end_raw = value.split(":")
    if not start_raw or not end_raw:
        raise ValueError(f"Invalid unit range {raw!r}: START and END are required")

    try:
        start = int(start_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid unit range {raw!r}: START must be an integer") from exc

    try:
        end = int(end_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid unit range {raw!r}: END must be an integer") from exc

    return UnitRange(start=start, end=end)


def select_units(units: list[EpubChapter], unit_range: UnitRange, lang: str) -> list[EpubChapter]:
    if unit_range.start < 0:
        raise ValueError(f"{lang} unit range start must be >= 0: {unit_range.start}")
    if unit_range.end < unit_range.start:
        raise ValueError(
            f"{lang} unit range end must be >= start: "
            f"{unit_range.start}:{unit_range.end}"
        )
    if unit_range.end >= len(units):
        raise ValueError(
            f"{lang} unit range end out of range: {unit_range.end}; "
            f"available units: {len(units)}"
        )

    return units[unit_range.start:unit_range.end + 1]


def concat_unit_text(units: list[EpubChapter]) -> str:
    return "\n\n".join(unit.text for unit in units).strip()


def build_sentence_windows(
    en_count: int,
    zh_count: int,
    window_sentences: int,
    prefix: str = "body",
) -> list[SentenceWindow]:
    if en_count <= 0:
        raise ValueError(f"English sentence count must be > 0: {en_count}")
    if zh_count <= 0:
        raise ValueError(f"Chinese sentence count must be > 0: {zh_count}")
    if window_sentences <= 0:
        raise ValueError(f"Window sentence count must be > 0: {window_sentences}")

    n_windows = (max(en_count, zh_count) + window_sentences - 1) // window_sentences
    windows: list[SentenceWindow] = []

    for i in range(n_windows):
        en_start = round(i * en_count / n_windows)
        en_end = round((i + 1) * en_count / n_windows) - 1
        zh_start = round(i * zh_count / n_windows)
        zh_end = round((i + 1) * zh_count / n_windows) - 1

        if en_start > en_end or zh_start > zh_end:
            continue

        windows.append(
            SentenceWindow(
                window_id=f"{prefix}_{len(windows):03d}",
                en_start=en_start,
                en_end=en_end,
                zh_start=zh_start,
                zh_end=zh_end,
            )
        )

    return windows


def validate_nonempty_sentences(en_sents: list[object], zh_sents: list[object]) -> None:
    if not en_sents:
        raise ValueError("English sentence list is empty")
    if not zh_sents:
        raise ValueError("Chinese sentence list is empty")
