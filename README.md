# Lightweight Chinese-English EPUB Embedding Aligner

This is a first-pass replacement for the old LF Aligner workflow.

Pipeline:

```text
English EPUB + Chinese EPUB
→ extract EPUB spine chapters
→ chapter_map.yml chapter pairing
→ English/Chinese sentence splitting
→ multilingual sentence embeddings
→ monotonic dynamic-programming alignment
→ aligned.xlsx
→ read with pipeline/excel_speaker.py
```

## Install

创建新环境

```bash
cd embedding_aligner_pipeline

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

source .venv/bin/activate
```

Recommended models:

```text
Default quality: BAAI/bge-m3
CPU fast:       intfloat/multilingual-e5-small
CPU balanced:   intfloat/multilingual-e5-base
```

CPU is supported. GPU, CUDA, and Apple MPS are optional.

## Run

```bash
python -m pipeline.run_align \
  --book-id educated \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --chapter-map book/educated.chapter_map.yml \
  --model BAAI/bge-m3 \
  --device auto \
  --out output/educated/aligned.xlsx
```

For a lower-memory CPU test:

```bash
python -m pipeline.run_align \
  --book-id educated \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --chapter-map book/educated.chapter_map.yml \
  --model intfloat/multilingual-e5-small \
  --device cpu \
  --batch-size 16 \
  --out output/educated/aligned.xlsx
```

## chapter_map.yml

The map accepts a top-level `chapters` list. Numeric indexes are 0-based EPUB spine-document indexes.

```yaml
chapters:
  - id: ch001
    en_index: 3
    zh_index: 2
  - id: ch002
    en_index: 4
    zh_index: 3
```

String refs can match `chapter_id`, `href`, title, or a partial href/title.

## Output schema

```text
A: en_text
B: zh_text
C: score
D: status
E: chapter_id
F: align_id
G: en_ids
H: zh_ids
I: align_type
J: note
```

Status values:

```text
auto_good       score >= 0.72
needs_review    0.55 <= score < 0.72
bad_suspect     score < 0.55
skip_en
skip_zh
```

## Notes

`pipeline/excel_speaker.py` 

It can open the generated `aligned.xlsx`; English remains in column A and Chinese in column B.

Embedding cache is stored under `.align_cache/<model>/`. Repeated runs with the same model, book id, chapter id, and sentence text reuse cached `.npy` files.
