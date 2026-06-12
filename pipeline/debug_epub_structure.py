from __future__ import annotations

import argparse
import re
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT


CHAPTER_PATTERNS = [
    re.compile(r"第[一二三四五六七八九十百千万零〇两\d]+章"),
    re.compile(r"第[一二三四五六七八九十百千万零〇两\d]+部分"),
    re.compile(r"Chapter\s+\d+", re.I),
    re.compile(r"Prologue", re.I),
    re.compile(r"Epilogue", re.I),
]


def compact(s: str, limit: int = 300) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= limit else s[:limit] + "..."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epub", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--preview-chars", type=int, default=1200)
    args = parser.parse_args()

    book = epub.read_epub(args.epub)
    id_to_item = {item.get_id(): item for item in book.get_items()}

    lines = []
    lines.append(f"EPUB: {args.epub}")
    lines.append(f"spine items: {len(book.spine)}")
    lines.append("=" * 120)
    lines.append("")

    seen = set()

    for spine_i, spine_item in enumerate(book.spine):
        item_id = spine_item[0] if isinstance(spine_item, tuple) else spine_item
        if item_id in seen:
            continue
        seen.add(item_id)

        item = id_to_item.get(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue

        href = getattr(item, "file_name", None) or item.get_name() or item_id
        html = item.get_content()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)

        lines.append("-" * 120)
        lines.append(f"SPINE_INDEX: {spine_i}")
        lines.append(f"ITEM_ID    : {item_id}")
        lines.append(f"HREF       : {href}")
        lines.append(f"TEXT_CHARS : {len(text)}")
        lines.append("")

        lines.append("[HTML headings h1-h6]")
        heading_found = False
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            t = compact(tag.get_text(" ", strip=True), 300)
            if t:
                heading_found = True
                lines.append(f"  <{tag.name}> {t}")
        if not heading_found:
            lines.append("  <none>")
        lines.append("")

        lines.append("[Lines containing 章 / 部分 / Chapter / Prologue / Epilogue]")
        candidate_found = False
        raw_lines = [x.strip() for x in text.splitlines() if x.strip()]
        for j, line in enumerate(raw_lines):
            if any(p.search(line) for p in CHAPTER_PATTERNS):
                candidate_found = True
                before = compact(raw_lines[j - 1], 180) if j - 1 >= 0 else ""
                current = compact(line, 300)
                after = compact(raw_lines[j + 1], 180) if j + 1 < len(raw_lines) else ""
                lines.append(f"  line {j}: {current}")
                if before:
                    lines.append(f"      prev: {before}")
                if after:
                    lines.append(f"      next: {after}")
        if not candidate_found:
            lines.append("  <none>")
        lines.append("")

        lines.append("[Text preview]")
        lines.append(compact(text, args.preview_chars))
        lines.append("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved debug report to: {out}")


if __name__ == "__main__":
    main()
