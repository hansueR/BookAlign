from __future__ import annotations

from .epub_extract import clean_text, html_to_text, extract_epub_to_chapters, extract_epub_to_txt


if __name__ == "__main__":
    extract_epub_to_txt(
        "book/Educated (Tara Westover).epub",
        "book/Educated_en.txt",
    )

    extract_epub_to_txt(
        "book/你当像鸟飞往你的山.epub",
        "book/Educated_zh.txt",
    )
