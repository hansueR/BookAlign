from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .align_dp import AlignmentRow, align_chapter_dp
from .config import AlignConfig, DEFAULT_MODEL
from .embedder import Embedder, resolve_device
from .epub_extract import EpubChapter, chapter_table, extract_epub_to_chapters
from .export_review import export_aligned_xlsx
from .segment import make_sentence_records


@dataclass(frozen=True)
class ChapterPair:
    chapter_id: str
    en_ref: Any
    zh_ref: Any


def _load_yaml(path: str | Path) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_chapter_map(path: str | Path) -> list[ChapterPair]:
    data = _load_yaml(path)
    if data is None:
        raise ValueError(f"Empty chapter map: {path}")

    entries = data.get("chapters", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("chapter_map.yml must be a list or contain a top-level 'chapters' list")

    pairs: list[ChapterPair] = []
    for pos, entry in enumerate(entries):
        if isinstance(entry, dict):
            chapter_id = str(entry.get("chapter_id") or entry.get("id") or f"ch{pos:04d}")
            en_ref = (
                entry.get("en")
                if "en" in entry
                else entry.get("en_index")
                if "en_index" in entry
                else entry.get("en_id")
                if "en_id" in entry
                else entry.get("en_href")
            )
            zh_ref = (
                entry.get("zh")
                if "zh" in entry
                else entry.get("zh_index")
                if "zh_index" in entry
                else entry.get("zh_id")
                if "zh_id" in entry
                else entry.get("zh_href")
            )
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            chapter_id = f"ch{pos:04d}"
            en_ref, zh_ref = entry[0], entry[1]
        else:
            raise ValueError(f"Invalid chapter map entry at position {pos}: {entry!r}")

        if en_ref is None or zh_ref is None:
            raise ValueError(f"Missing en/zh reference in chapter map entry: {entry!r}")
        pairs.append(ChapterPair(chapter_id=chapter_id, en_ref=en_ref, zh_ref=zh_ref))

    return pairs


def _resolve_chapter_ref(chapters: list[EpubChapter], ref: Any, lang: str) -> EpubChapter:
    if isinstance(ref, int):
        if 0 <= ref < len(chapters):
            return chapters[ref]
        raise IndexError(f"{lang} chapter index out of range: {ref}; total={len(chapters)}")

    if isinstance(ref, str):
        ref_norm = ref.strip()
        if ref_norm.isdigit():
            idx = int(ref_norm)
            if 0 <= idx < len(chapters):
                return chapters[idx]
            raise IndexError(f"{lang} chapter index out of range: {idx}; total={len(chapters)}")
        for ch in chapters:
            if ref_norm in {ch.chapter_id, ch.href, ch.title}:
                return ch
        # Useful for href fragments or partial title matching.
        for ch in chapters:
            if ref_norm and (ref_norm in ch.href or ref_norm in ch.title):
                return ch

    raise KeyError(
        f"Cannot resolve {lang} chapter reference {ref!r}.\n"
        f"Available chapters:\n{chapter_table(chapters)}"
    )


def align_book(
    book_id: str,
    en_epub: str | Path,
    zh_epub: str | Path,
    chapter_map: str | Path,
    model_name: str = DEFAULT_MODEL,
    device: str = "auto",
    out_path: str | Path = "aligned.xlsx",
    cache_dir: str | Path = ".align_cache",
    batch_size: int = 32,
    max_chars_per_segment: int = 1200,
) -> Path:
    cfg = AlignConfig(
        book_id=book_id,
        model_name=model_name,
        device=device,
        cache_dir=Path(cache_dir),
        batch_size=batch_size,
        max_chars_per_segment=max_chars_per_segment,
    )

    resolved_device = resolve_device(cfg.device)
    print(f"[1/6] Extracting EPUB chapters")
    en_chapters = extract_epub_to_chapters(en_epub)
    zh_chapters = extract_epub_to_chapters(zh_epub)
    print(f"  EN chapters: {len(en_chapters)}")
    print(f"  ZH chapters: {len(zh_chapters)}")

    print(f"[2/6] Loading chapter map: {chapter_map}")
    pairs = load_chapter_map(chapter_map)
    print(f"  Chapter pairs: {len(pairs)}")

    print(f"[3/6] Loading embedder: {model_name} | device={resolved_device}")
    embedder = Embedder(
        model_name=cfg.model_name,
        device=resolved_device,
        cache_dir=cfg.cache_dir,
        batch_size=cfg.batch_size,
    )

    all_rows: list[AlignmentRow] = []
    for pair_idx, pair in enumerate(pairs, start=1):
        en_ch = _resolve_chapter_ref(en_chapters, pair.en_ref, lang="en")
        zh_ch = _resolve_chapter_ref(zh_chapters, pair.zh_ref, lang="zh")
        print(
            f"[4/6] Aligning {pair_idx}/{len(pairs)} {pair.chapter_id}: "
            f"EN[{en_ch.index}:{en_ch.chapter_id}] ↔ ZH[{zh_ch.index}:{zh_ch.chapter_id}]"
        )

        en_sents = make_sentence_records(
            en_ch.text,
            lang="en",
            chapter_id=pair.chapter_id,
            max_chars=cfg.max_chars_per_segment,
        )
        zh_sents = make_sentence_records(
            zh_ch.text,
            lang="zh",
            chapter_id=pair.chapter_id,
            max_chars=cfg.max_chars_per_segment,
        )
        print(f"  sentences: en={len(en_sents)} zh={len(zh_sents)}")

        en_emb = embedder.encode(
            [s.text for s in en_sents],
            namespace=f"{book_id}:{pair.chapter_id}:en",
        )
        zh_emb = embedder.encode(
            [s.text for s in zh_sents],
            namespace=f"{book_id}:{pair.chapter_id}:zh",
        )

        rows = align_chapter_dp(
            en_sents,
            zh_sents,
            en_emb,
            zh_emb,
            chapter_id=pair.chapter_id,
            skip_penalty=cfg.skip_penalty,
            size_penalty_12_or_21=cfg.size_penalty_12_or_21,
            size_penalty_22=cfg.size_penalty_22,
        )
        all_rows.extend(rows)

    print(f"[5/6] Exporting Excel: {out_path}")
    result = export_aligned_xlsx(all_rows, out_path)
    print(f"[6/6] Done: {result}")
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight Chinese-English EPUB embedding aligner")
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--en", required=True, help="English EPUB path")
    parser.add_argument("--zh", required=True, help="Chinese EPUB path")
    parser.add_argument("--chapter-map", required=True, help="chapter_map.yml path")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache-dir", default=".align_cache")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-chars-per-segment", type=int, default=1200)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    align_book(
        book_id=args.book_id,
        en_epub=args.en,
        zh_epub=args.zh,
        chapter_map=args.chapter_map,
        model_name=args.model,
        device=args.device,
        out_path=args.out,
        cache_dir=args.cache_dir,
        batch_size=args.batch_size,
        max_chars_per_segment=args.max_chars_per_segment,
    )


if __name__ == "__main__":
    main()
