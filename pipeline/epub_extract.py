from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from bs4 import BeautifulSoup, NavigableString
from ebooklib import epub, ITEM_DOCUMENT


BLOCK_TAGS = {
    "p", "div", "section", "article", "chapter",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "ul", "ol", "blockquote", "pre",
    "table", "tr"
}

REMOVE_TAGS = {"script", "style", "noscript"}


@dataclass
class EpubChapter:
    index: int
    chapter_id: str
    href: str
    title: str
    text: str


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\u00ad", "")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def soup_to_text(soup: BeautifulSoup) -> str:
    root = soup.body if soup.body is not None else soup

    for tag in root.find_all(REMOVE_TAGS):
        tag.decompose()

    for br in root.find_all("br"):
        br.replace_with("\n")

    for tag in root.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = root.get_text(separator=" ", strip=False)
    return clean_text(text)


def html_to_text(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup_to_text(soup)


def first_nonempty_line(text: str, fallback: str = "") -> str:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return fallback


def guess_lang_from_text(text: str) -> str | None:
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_chars = len(re.findall(r"[A-Za-z]", text))
    if zh_chars > latin_chars:
        return "zh"
    if latin_chars > zh_chars:
        return "en"
    return None


def safe_id(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", s)
    return s[:80] or "chapter"


def normalize_title(title: str) -> str:
    title = clean_text(title)
    title = re.sub(r"\s*\[\d+\]\s*$", "", title)
    return title.strip()


def is_part_title(title: str) -> bool:
    title = title.strip()
    return bool(re.match(r"^第[一二三四五六七八九十百千万零〇两\d]+部分$", title))


def split_html_by_heading_markers(
    html: bytes,
    heading_tag: str,
    min_chars: int,
) -> list[tuple[str, str]]:
    """
    Split one XHTML document by repeated heading tags.

    For this Chinese EPUB:
      h1 = 第一部分 / 第二部分 / 第三部分
      h2 = actual chapter titles, e.g. 择善 / 助产士 / 奶油色鞋子
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body if soup.body is not None else soup

    headings = root.find_all(heading_tag)
    if len(headings) < 2:
        return []

    titles: list[str] = []
    for i, h in enumerate(headings):
        title = normalize_title(h.get_text(" ", strip=True))
        titles.append(title)
        marker = f"@@ALIGNER_CHAPTER_SPLIT_{i:04d}@@"
        h.insert_before(NavigableString(f"\n\n{marker}\n\n"))

    text = soup_to_text(soup)
    parts = re.split(r"@@ALIGNER_CHAPTER_SPLIT_(\d{4})@@", text)

    chunks: list[tuple[str, str]] = []

    # parts[0] is text before the first heading marker.
    # In this Chinese book it is usually just "第一部分", so we discard it
    # unless it contains meaningful long text.
    prefix = clean_text(parts[0]) if parts else ""
    if prefix and len(prefix) >= min_chars and not is_part_title(prefix):
        chunks.append((first_nonempty_line(prefix), prefix))

    i = 1
    while i + 1 < len(parts):
        idx = int(parts[i])
        chunk = clean_text(parts[i + 1])
        i += 2

        if not chunk or len(chunk) < min_chars:
            continue

        title = titles[idx] if 0 <= idx < len(titles) else first_nonempty_line(chunk)
        chunks.append((title, chunk))

    return chunks


def split_html_into_semantic_chapters(
    html: bytes,
    lang: str | None,
    min_chars: int,
) -> list[tuple[str, str]]:
    """
    Return list of (title, text).

    Chinese policy:
      - If multiple h2 exist, split by h2.
      - h1 like 第一部分 is a part title, not a chapter.
      - If no h2 splitting is possible, keep the spine item as one unit.

    English policy:
      - Usually EPUB spine is already chapter-level.
      - Keep one spine item as one unit for first version.
    """
    plain_text = html_to_text(html)
    if not plain_text or len(plain_text) < min_chars:
        return []

    detected_lang = lang or guess_lang_from_text(plain_text)

    if detected_lang == "zh":
        h2_chunks = split_html_by_heading_markers(
            html,
            heading_tag="h2",
            min_chars=max(40, min_chars),
        )
        if h2_chunks:
            return h2_chunks

    return [(first_nonempty_line(plain_text), plain_text)]


def extract_epub_to_chapters(
    epub_path: str,
    min_chars: int = 20,
    lang: str | None = None,
) -> list[EpubChapter]:
    """
    Extract EPUB chapters in spine order.

    Important:
    - EPUB spine items are not always real chapters.
    - For Chinese books where one spine item contains a whole part,
      split inside the XHTML by h2 headings.
    """
    book = epub.read_epub(epub_path)

    id_to_item = {item.get_id(): item for item in book.get_items()}
    seen_ids = set()
    chapters: list[EpubChapter] = []

    for spine_pos, spine_item in enumerate(book.spine):
        item_id = spine_item[0] if isinstance(spine_item, tuple) else spine_item

        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        item = id_to_item.get(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue

        href = getattr(item, "file_name", None) or item.get_name() or item_id

        try:
            html = item.get_content()
            subchapters = split_html_into_semantic_chapters(
                html,
                lang=lang,
                min_chars=min_chars,
            )
        except Exception as e:
            print(f"Skip item {item_id}: {e}")
            continue

        for sub_idx, (title, text) in enumerate(subchapters):
            if not text or len(text) < min_chars:
                continue

            if len(subchapters) == 1:
                chapter_id = item_id
                chapter_href = href
            else:
                chapter_id = f"{item_id}__{sub_idx:03d}__{safe_id(title)}"
                chapter_href = f"{href}#{sub_idx:03d}"

            chapters.append(
                EpubChapter(
                    index=len(chapters),
                    chapter_id=chapter_id,
                    href=chapter_href,
                    title=title,
                    text=text,
                )
            )

    return chapters


def extract_epub_to_txt(epub_path: str, out_txt_path: str) -> None:
    chapters = extract_epub_to_chapters(epub_path)
    full_text = "\n\n".join(ch.text for ch in chapters).strip()

    out_path = Path(out_txt_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full_text, encoding="utf-8")

    print(f"Saved UTF-8 txt to: {out_path}")


if __name__ == "__main__":
    extract_epub_to_txt(
        "book/Educated.en.epub",
        "book/Educated_en.txt",
    )

    extract_epub_to_txt(
        "book/Educated.zh.epub",
        "book/Educated_zh.txt",
    )


def chapter_table(chapters: list[EpubChapter]) -> str:
    """
    Compatibility helper used by run_align.py / debug output.
    Return a readable table of extracted chapters.
    """
    lines = []
    lines.append("index\tchapter_id\thref\ttitle\tchars")
    for ch in chapters:
        title = " ".join((ch.title or "").split())
        href = ch.href or ""
        chapter_id = ch.chapter_id or ""
        lines.append(
            f"{ch.index}\t{chapter_id}\t{href}\t{title}\t{len(ch.text)}"
        )
    return "\n".join(lines)
