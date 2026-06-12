# Lightweight Chinese-English EPUB Embedding Aligner

This is a first-pass replacement for the old LF Aligner workflow.

Pipeline:

```text
English EPUB + Chinese EPUB
→ preview EPUB body units
→ choose inclusive body ranges
→ English/Chinese sentence splitting
→ multilingual sentence embeddings
→ windowed monotonic dynamic-programming alignment
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

### Step 1: Preview EPUB body ranges

```bash
python -m pipeline.preview_body_range \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --out output/educated/body_preview.html \
  --open
```

The HTML shows English and Chinese EPUB units. Choose inclusive ranges from the preview, for example `4:38` and `3:37`; `4:38` includes units 4 through 38.

### Step 2: Run body-range alignment

```bash
python -m pipeline.run_align \
  --book-id educated \
  --mode body-range \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --en-range 4:38 \
  --zh-range 3:37 \
  --model intfloat/multilingual-e5-small \
  --device cpu \
  --batch-size 16 \
  --out output/educated/aligned.xlsx
```

Body-range mode does not require `chapter_map.yml`. Range syntax is inclusive `START:END`. Windowed alignment avoids doing one huge full-book DP, and the Excel schema is unchanged.

### Step 3: Open the Excel reader

```bash
python pipeline/excel_speaker.py
```

## Optional: old chapter-map mode

```bash
python -m pipeline.run_align \
  --book-id educated \
  --mode chapter-map \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --chapter-map book/educated.chapter_map.yml \
  --model intfloat/multilingual-e5-small \
  --device cpu \
  --batch-size 16 \
  --out output/educated/aligned.chapter_map.xlsx
```

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
