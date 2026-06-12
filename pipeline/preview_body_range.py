from __future__ import annotations

import argparse
import html
from pathlib import Path
import webbrowser

from .epub_extract import EpubChapter, extract_epub_to_chapters


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _preview_start(text: str, limit: int) -> str:
    return text[:max(0, limit)].strip()


def _preview_end(text: str, limit: int) -> str:
    limit = max(0, limit)
    if limit == 0:
        return ""
    return text[-limit:].strip()


def render_unit_card(unit: EpubChapter, preview_chars: int, tail_chars: int) -> str:
    return f"""
<article class="unit-card">
  <h3>[{unit.index}] chars={len(unit.text)}</h3>
  <dl>
    <dt>title</dt>
    <dd>{_escape(unit.title)}</dd>
    <dt>href</dt>
    <dd>{_escape(unit.href)}</dd>
    <dt>id/chapter_id</dt>
    <dd>{_escape(unit.chapter_id)}</dd>
  </dl>
  <h4>START preview</h4>
  <pre>{_escape(_preview_start(unit.text, preview_chars))}</pre>
  <h4>END preview</h4>
  <pre>{_escape(_preview_end(unit.text, tail_chars))}</pre>
</article>
""".strip()


def render_side(
    label: str,
    epub_path: str,
    units: list[EpubChapter],
    preview_chars: int,
    tail_chars: int,
) -> str:
    cards = "\n".join(
        render_unit_card(unit, preview_chars=preview_chars, tail_chars=tail_chars)
        for unit in units
    )
    return f"""
<section class="side">
  <header class="side-header">
    <h2>{_escape(label)}</h2>
    <p>{_escape(epub_path)}</p>
    <p>{len(units)} units</p>
  </header>
  {cards}
</section>
""".strip()


def render_html(
    en_path: str | None,
    zh_path: str | None,
    en_units: list[EpubChapter] | None,
    zh_units: list[EpubChapter] | None,
    preview_chars: int,
    tail_chars: int,
) -> str:
    sides = []
    if en_path is not None and en_units is not None:
        sides.append(
            render_side(
                "English",
                en_path,
                en_units,
                preview_chars=preview_chars,
                tail_chars=tail_chars,
            )
        )
    if zh_path is not None and zh_units is not None:
        sides.append(
            render_side(
                "Chinese",
                zh_path,
                zh_units,
                preview_chars=preview_chars,
                tail_chars=tail_chars,
            )
        )

    column_class = "two-column" if len(sides) == 2 else "one-column"
    body = "\n".join(sides)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>BookAlign Body Range Preview</title>
  <style>
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    .page {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px;
    }}
    .instructions {{
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 18px 20px;
      margin-bottom: 20px;
    }}
    .instructions h1 {{
      margin: 0 0 8px;
      font-size: 22px;
    }}
    .instructions p {{
      margin: 6px 0;
    }}
    code {{
      background: #eef2f7;
      border-radius: 4px;
      padding: 1px 5px;
    }}
    .columns {{
      display: grid;
      gap: 18px;
      align-items: start;
    }}
    .columns.two-column {{
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }}
    .columns.one-column {{
      grid-template-columns: minmax(0, 1fr);
    }}
    .side-header, .unit-card {{
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 14px;
    }}
    .side-header h2 {{
      margin: 0 0 6px;
      font-size: 20px;
    }}
    .side-header p {{
      margin: 4px 0;
      color: #4b5563;
      overflow-wrap: anywhere;
    }}
    .unit-card h3 {{
      margin: 0 0 10px;
      font-size: 17px;
    }}
    .unit-card h4 {{
      margin: 14px 0 6px;
      font-size: 14px;
      color: #374151;
    }}
    dl {{
      display: grid;
      grid-template-columns: 86px minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
    }}
    dt {{
      color: #6b7280;
      font-weight: 600;
    }}
    dd {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    pre {{
      margin: 0;
      padding: 10px;
      background: #f8fafc;
      border: 1px solid #e5eaf1;
      border-radius: 6px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }}
    @media (max-width: 900px) {{
      .columns.two-column {{
        grid-template-columns: minmax(0, 1fr);
      }}
      .page {{
        padding: 14px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="instructions">
      <h1>BookAlign Body Range Preview</h1>
      <p>Range syntax is inclusive <code>START:END</code>.</p>
      <p>Example: EN range <code>4:38</code> includes units 4 through 38.</p>
      <p>After choosing ranges, run <code>pipeline.run_align</code> with <code>--mode body-range</code>.</p>
    </section>
    <div class="columns {column_class}">
      {body}
    </div>
  </main>
</body>
</html>
"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an HTML preview for choosing body-range EPUB units."
    )
    parser.add_argument("--en", help="English EPUB path")
    parser.add_argument("--zh", help="Chinese EPUB path")
    parser.add_argument("--out", default="body_preview.html", help="Output HTML path")
    parser.add_argument("--preview-chars", type=int, default=500)
    parser.add_argument("--tail-chars", type=int, default=500)
    parser.add_argument("--min-chars", type=int, default=20)
    parser.add_argument("--open", action="store_true", help="Open generated HTML in the default browser")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if not args.en and not args.zh:
        raise SystemExit("Please provide --en and/or --zh")

    en_units = extract_epub_to_chapters(args.en, min_chars=args.min_chars) if args.en else None
    zh_units = extract_epub_to_chapters(args.zh, min_chars=args.min_chars) if args.zh else None

    html_text = render_html(
        en_path=args.en,
        zh_path=args.zh,
        en_units=en_units,
        zh_units=zh_units,
        preview_chars=args.preview_chars,
        tail_chars=args.tail_chars,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"Saved body range preview to: {out_path}")

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
