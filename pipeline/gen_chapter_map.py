from __future__ import annotations

import argparse
from pathlib import Path


def build_chapter_map(
    en_start: int,
    en_end: int,
    zh_start: int,
    zh_end: int,
    id_start: int = 1,
    id_prefix: str = "ch",
    id_width: int = 3,
) -> str:
    en_count = en_end - en_start + 1
    zh_count = zh_end - zh_start + 1

    if en_count <= 0:
        raise ValueError(f"Invalid English range: {en_start}..{en_end}")
    if zh_count <= 0:
        raise ValueError(f"Invalid Chinese range: {zh_start}..{zh_end}")
    if en_count != zh_count:
        raise ValueError(
            f"Range length mismatch: EN has {en_count} chapters, "
            f"ZH has {zh_count} chapters.\n"
            f"EN range: {en_start}..{en_end}\n"
            f"ZH range: {zh_start}..{zh_end}"
        )

    lines = ["chapters:"]

    for offset in range(en_count):
        chapter_num = id_start + offset
        chapter_id = f"{id_prefix}{chapter_num:0{id_width}d}"
        en_index = en_start + offset
        zh_index = zh_start + offset

        lines.append(f"  - id: {chapter_id}")
        lines.append(f"    en_index: {en_index}")
        lines.append(f"    zh_index: {zh_index}")

    return "\n".join(lines) + "\n"


def build_entries_only(
    en_start: int,
    en_end: int,
    zh_start: int,
    zh_end: int,
    id_start: int = 1,
    id_prefix: str = "ch",
    id_width: int = 3,
) -> str:
    full = build_chapter_map(
        en_start=en_start,
        en_end=en_end,
        zh_start=zh_start,
        zh_end=zh_end,
        id_start=id_start,
        id_prefix=id_prefix,
        id_width=id_width,
    )
    return "\n".join(full.splitlines()[1:]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate chapter_map.yml by aligned English/Chinese index ranges."
    )

    parser.add_argument("--en-start", type=int, required=True)
    parser.add_argument("--en-end", type=int, required=True)
    parser.add_argument("--zh-start", type=int, required=True)
    parser.add_argument("--zh-end", type=int, required=True)

    parser.add_argument("--id-start", type=int, default=1)
    parser.add_argument("--id-prefix", default="ch")
    parser.add_argument("--id-width", type=int, default=3)

    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append generated entries to an existing YAML file instead of overwriting it.",
    )

    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.append:
        new_text = build_entries_only(
            en_start=args.en_start,
            en_end=args.en_end,
            zh_start=args.zh_start,
            zh_end=args.zh_end,
            id_start=args.id_start,
            id_prefix=args.id_prefix,
            id_width=args.id_width,
        )

        if out_path.exists():
            old = out_path.read_text(encoding="utf-8").rstrip() + "\n"
            if not old.strip().startswith("chapters:"):
                raise ValueError(
                    f"{out_path} does not look like a chapter_map.yml file. "
                    "It should start with: chapters:"
                )
            out_path.write_text(old + new_text, encoding="utf-8")
        else:
            out_path.write_text("chapters:\n" + new_text, encoding="utf-8")
    else:
        yaml_text = build_chapter_map(
            en_start=args.en_start,
            en_end=args.en_end,
            zh_start=args.zh_start,
            zh_end=args.zh_end,
            id_start=args.id_start,
            id_prefix=args.id_prefix,
            id_width=args.id_width,
        )
        out_path.write_text(yaml_text, encoding="utf-8")

    print(f"Saved chapter map to: {out_path}")


if __name__ == "__main__":
    main()
