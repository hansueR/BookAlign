from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Sentence:
    sent_id: str
    text: str
    lang: str
    chapter_id: str
    index: int


_ABBREVIATIONS = {
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "St.",
    "vs.", "etc.", "e.g.", "i.e.", "Fig.", "No.", "U.S.", "U.K.",
}


def normalize_segment_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _protect_abbreviations(text: str) -> str:
    for abbr in sorted(_ABBREVIATIONS, key=len, reverse=True):
        text = text.replace(abbr, abbr.replace(".", "<DOT>"))
    text = re.sub(r"\b([A-Z])\.([A-Z])\.", lambda m: m.group(0).replace(".", "<DOT>"), text)
    return text


def _unprotect(text: str) -> str:
    return text.replace("<DOT>", ".")


def split_en_sentences(text: str, max_chars: int = 1200) -> list[str]:
    text = normalize_segment_text(text)
    if not text:
        return []

    protected = _protect_abbreviations(text)
    # Split after sentence punctuation followed by whitespace/newline and a plausible next sentence.
    parts = re.split(
        r"(?:(?<=[.!?])|(?<=[.!?][\"')\]]))\s+(?=[\"'“‘(\[]?[A-Z0-9])",
        protected,
    )
    sentences: list[str] = []
    for part in parts:
        part = _unprotect(part).strip()
        if not part:
            continue
        sentences.extend(_split_overlong(part, max_chars=max_chars, lang="en"))
    return sentences


def split_zh_sentences(text: str, max_chars: int = 1200) -> list[str]:
    text = normalize_segment_text(text)
    if not text:
        return []

    # Keep punctuation with the preceding segment.
    raw_parts = re.split(r"(?<=[。！？!?；;])\s*", text)
    sentences: list[str] = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        sentences.extend(_split_overlong(part, max_chars=max_chars, lang="zh"))
    return sentences


def _split_overlong(text: str, max_chars: int, lang: str) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    if lang == "zh":
        pieces = re.split(r"(?<=[，,、：:])\s*", text)
    else:
        pieces = re.split(r"(?<=[,;:])\s+", text)

    out: list[str] = []
    buf = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        candidate = piece if not buf else f"{buf} {piece}" if lang == "en" else f"{buf}{piece}"
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                out.append(buf)
            if len(piece) > max_chars:
                out.extend(piece[i:i + max_chars] for i in range(0, len(piece), max_chars))
                buf = ""
            else:
                buf = piece
    if buf:
        out.append(buf)
    return out


def split_sentences(text: str, lang: str, max_chars: int = 1200) -> list[str]:
    lang = lang.lower()
    if lang.startswith("zh") or lang in {"cn", "chinese"}:
        return split_zh_sentences(text, max_chars=max_chars)
    if lang.startswith("en") or lang == "english":
        return split_en_sentences(text, max_chars=max_chars)
    raise ValueError(f"Unsupported language: {lang}")


def make_sentence_records(text: str, lang: str, chapter_id: str, max_chars: int = 1200) -> list[Sentence]:
    parts = split_sentences(text, lang=lang, max_chars=max_chars)
    return [
        Sentence(
            sent_id=f"{chapter_id}:{lang}:{idx:05d}",
            text=part,
            lang=lang,
            chapter_id=chapter_id,
            index=idx,
        )
        for idx, part in enumerate(parts)
    ]
