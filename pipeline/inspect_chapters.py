from __future__ import annotations

import argparse
from pathlib import Path

from .epub_extract import extract_epub_to_chapters


def compact(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def write_epub_report(label: str, epub_path: str, preview_chars: int, min_chars: int) -> str:
    chapters = extract_epub_to_chapters(epub_path, min_chars=min_chars)

    lines = []
    lines.append("=" * 100)
    lines.append(f"{label}: {epub_path}")
    lines.append(f"chapters: {len(chapters)}")
    lines.append("=" * 100)
    lines.append("")

    for ch in chapters:
        lines.append("-" * 100)
        lines.append(f"index      : {ch.index}")
        lines.append(f"chapter_id : {ch.chapter_id}")
        lines.append(f"href       : {ch.href}")
        lines.append(f"title      : {ch.title}")
        lines.append(f"chars      : {len(ch.text)}")
        lines.append("")
        lines.append(compact(ch.text, preview_chars))
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect EPUB spine chapters before alignment")
    parser.add_argument("--en", help="English EPUB path")
    parser.add_argument("--zh", help="Chinese EPUB path")
    parser.add_argument("--out", default="chapter_preview.txt")
    parser.add_argument("--preview-chars", type=int, default=800)
    parser.add_argument("--min-chars", type=int, default=20)
    args = parser.parse_args()

    if not args.en and not args.zh:
        raise SystemExit("Please provide --en and/or --zh")

    reports = []
    if args.en:
        reports.append(write_epub_report("EN", args.en, args.preview_chars, args.min_chars))
    if args.zh:
        reports.append(write_epub_report("ZH", args.zh, args.preview_chars, args.min_chars))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(reports), encoding="utf-8")

    print(f"Saved chapter preview to: {out_path}")


if __name__ == "__main__":
    main()
