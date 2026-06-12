<p align="right">
  <a href="./README.md">English</a> |
  <a href="./README.zh.md">中文</a>
</p>

# BookAlign 中文使用说明

BookAlign 是一个轻量级的中英文 EPUB 对齐工具，主要用于双语阅读和语言学习。它的目标不是做机器翻译，也不是做复杂的出版级排版，而是把一本英文书和一本中文译本自动对齐成一个 Excel 文件，让读者可以逐行查看英文原文与中文译文，并结合内置的 Excel 阅读器进行英文朗读和阅读练习。

当前推荐使用的是 `body-range` 模式。这个模式的思路是：先让用户用 HTML 预览两个 EPUB 的正文结构，手动选择英文版和中文版的正文范围，然后程序在这个范围内部自动切分句子、生成 multilingual sentence embeddings，并用单调动态规划方法进行对齐，最后输出 `aligned.xlsx`。

## 1. 项目动机

很多双语阅读工具的前提是已经有整理好的平行语料，但真实的 EPUB 书籍通常并不是这样。英文原版和中文译本经常存在这些问题：

英文 EPUB 和中文 EPUB 的章节切分方式不一样；
有些版本包含序言、目录、版权页、广告页、译者说明等非正文内容；
同一章内部，中文译文不一定和英文逐句对应；
传统的 LF Aligner 流程比较重，依赖外部工具，复用成本较高；
如果每本书都手工整理章节映射，使用体验会比较差。

BookAlign 的设计目标是降低这个流程的使用成本。用户不需要手动整理每一个章节，只需要先选择英文和中文各自的正文范围，剩下的句子切分、embedding 计算、窗口化对齐和 Excel 导出都由程序完成。

换句话说，BookAlign 的核心定位是：

把“中英文 EPUB 对齐”变成一个可重复运行、可检查、可修正的轻量 pipeline。

它特别适合以下场景：

你有同一本书的英文 EPUB 和中文 EPUB；
你想把它们整理成中英对照表；
你希望用英文原文阅读，并在旁边参考中文译文；
你希望保留一个 Excel 文件，方便后续筛选、标注、复习和朗读。

## 2. 当前分支的主要功能

当前分支重点实现的是 `body-range` 对齐模式。

完整流程如下：

```text
英文 EPUB + 中文 EPUB
→ 预览 EPUB 正文单元
→ 手动选择英文 / 中文正文范围
→ 英文 / 中文句子切分
→ 多语言 sentence embedding
→ 窗口化单调动态规划对齐
→ 导出 aligned.xlsx
→ 用 pipeline/excel_speaker.py 阅读
```

主要功能包括：

第一，提取 EPUB 文本。程序会按照 EPUB spine 顺序读取正文单元，并尽量清理 HTML 标签、空白字符和无意义内容。

第二，生成正文范围预览。`pipeline.preview_body_range` 会输出一个 HTML 文件，把英文和中文 EPUB 的文本单元并排展示出来。用户可以根据每个单元的 index、标题、href、开头预览和结尾预览，判断正文从哪里开始、到哪里结束。

第三，使用 body-range 模式自动对齐。用户只需要提供英文正文范围和中文正文范围，例如 `--en-range 4:38` 与 `--zh-range 3:37`。范围是闭区间，也就是包括起点和终点。

第四，自动切分句子。英文和中文会分别使用不同规则切分。英文主要根据句末标点和大写开头判断；中文主要根据 `。！？；` 等中文标点切分。

第五，使用多语言 embedding 进行语义匹配。默认模型是 `BAAI/bge-m3`，也可以改用更适合 CPU 的模型，例如 `intfloat/multilingual-e5-small` 或 `intfloat/multilingual-e5-base`。

第六，使用窗口化单调动态规划对齐。程序不会直接对整本书做一个巨大的全局 DP，而是把正文句子分成若干窗口，在每个窗口内做局部对齐。这能降低计算量，也更适合普通电脑运行。

第七，导出 Excel。输出文件通常命名为 `aligned.xlsx`。英文在 A 列，中文在 B 列，后面包含分数、状态、对齐 ID 等辅助信息。

第八，打开阅读器。`pipeline/excel_speaker.py` 可以打开生成的 Excel 文件，用于中英对照阅读。它支持选择英文列、中文列、分页显示、点击英文朗读、书签和阅读位置保存。

## 3. 环境要求

项目使用 Python 编写。普通 Mac、Windows、Linux 都可以运行对齐流程。GPU 不是必需的，CPU 可以运行；如果机器有 CUDA GPU 或 Apple Silicon 的 MPS，也可以作为加速选项。

依赖主要包括：

```text
ebooklib
beautifulsoup4
openpyxl
PyYAML
numpy
sentence-transformers
torch
```

如果只是想在普通电脑上先跑通流程，建议先使用 CPU 和较小模型：

```text
intfloat/multilingual-e5-small
```

如果更重视质量，并且能接受模型下载和运行时间更长，可以使用默认模型：

```text
BAAI/bge-m3
```

## 4. 安装方法

先克隆当前分支：

```bash
git clone -b body-range-aligner https://github.com/hansueR/BookAlign.git
cd BookAlign
```

创建虚拟环境：

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

安装完成后，可以用下面命令检查 Python 是否在虚拟环境中：

```bash
python --version
pip list
```

## 5. 准备书籍文件

建议在项目根目录下新建一个 `book/` 目录，把英文 EPUB 和中文 EPUB 放进去。

例如：

```text
BookAlign/
├── book/
│   ├── Educated.en.epub
│   └── Educated.zh.epub
├── pipeline/
├── requirements.txt
└── README.md
```

文件名可以自定义，但建议保持清楚：

```text
书名.en.epub
书名.zh.epub
```

例如：

```text
Educated.en.epub
Educated.zh.epub
The_Alchemist.en.epub
The_Alchemist.zh.epub
```

## 6. 推荐使用流程：body-range 模式

### 第一步：生成正文范围预览

先运行：

```bash
mkdir -p output/educated

python -m pipeline.preview_body_range \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --out output/educated/body_preview.html \
  --open
```

这里的 `educated` 只是一个例子，可以替换成你自己的书名。

运行后会生成：

```text
output/educated/body_preview.html
```

如果加了 `--open`，程序会自动在浏览器中打开这个 HTML 文件。

这个预览页面会显示英文和中文 EPUB 的文本单元。每个单元都有一个 index，例如：

```text
[0]
[1]
[2]
[3]
...
```

你需要做的是找到真正正文的起点和终点。

例如，英文版可能是：

```text
4:38
```

中文版可能是：

```text
3:37
```

这表示：

英文正文使用第 4 到第 38 个单元；
中文正文使用第 3 到第 37 个单元；
范围是闭区间，所以 `4:38` 包含 4 和 38。

### 第二步：运行正文范围对齐

确定范围后，运行：

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

参数说明：

`--book-id` 是这本书的内部 ID，用于缓存和输出标记。建议使用英文小写，例如 `educated`、`alchemist`。
`--mode body-range` 表示使用正文范围模式。
`--en` 是英文 EPUB 路径。
`--zh` 是中文 EPUB 路径。
`--en-range` 是英文正文范围。
`--zh-range` 是中文正文范围。
`--model` 是使用的 embedding 模型。
`--device cpu` 表示使用 CPU。
`--batch-size` 是 embedding 的批大小。CPU 上建议先用 16 或 32。
`--out` 是输出 Excel 文件路径。

运行成功后，会生成：

```text
output/educated/aligned.xlsx
```

第一次运行时，程序需要下载 embedding 模型，所以会比较慢。后续如果使用同一个模型和同一本书，embedding 会复用缓存，速度会快一些。

### 第三步：查看输出 Excel

输出 Excel 的主要列如下：

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

最重要的是前四列：

`en_text`：英文原文片段。
`zh_text`：中文译文片段。
`score`：语义相似度分数。
`status`：程序对这一行对齐质量的初步判断。

状态值包括：

```text
auto_good       分数较高，通常可以直接使用
needs_review    中等分数，建议人工检查
bad_suspect     分数较低，可能错位
skip_en         英文句子没有匹配到中文
skip_zh         中文句子没有匹配到英文
```

一般阅读时，可以先重点看 `auto_good` 和 `needs_review`。如果你要整理高质量语料，则需要人工检查 `bad_suspect`、`skip_en`、`skip_zh`。

### 第四步：打开 Excel 阅读器

生成 Excel 后，可以运行：

```bash
python pipeline/excel_speaker.py
```

打开后，选择刚才生成的：

```text
output/educated/aligned.xlsx
```

阅读器默认英文列是 A 列，中文列是 B 列。你可以在左侧设置栏中调整英文列、中文列、字体、字号、列宽和每页显示行数。

使用方式：

单击英文单元格：朗读英文。
双击单元格：添加或取消书签。
上下方向键：移动到上一行或下一行。
分页按钮：切换阅读页。
设置栏：调整字体、字号、列宽、朗读速度等。

注意：当前阅读器的朗读功能主要依赖 macOS 的 `say` 命令。如果你在 Windows 或 Linux 上运行，对齐和 Excel 导出仍然可以使用，但朗读功能可能需要后续适配。

## 7. 模型选择建议

当前 README 中推荐了三个模型：

```text
Default quality: BAAI/bge-m3
CPU fast:       intfloat/multilingual-e5-small
CPU balanced:   intfloat/multilingual-e5-base
```

实际使用建议如下：

如果你只是想先跑通流程：

```bash
--model intfloat/multilingual-e5-small
--device cpu
--batch-size 16
```

如果你希望 CPU 上质量和速度平衡：

```bash
--model intfloat/multilingual-e5-base
--device cpu
--batch-size 16
```

如果你更重视对齐质量，且能接受更慢速度：

```bash
--model BAAI/bge-m3
--device cpu
--batch-size 8
```

如果你有 NVIDIA GPU：

```bash
--device cuda
```

如果你是 Apple Silicon Mac，并且 PyTorch 支持 MPS：

```bash
--device mps
```

也可以让程序自动判断：

```bash
--device auto
```

如果运行时内存不够，可以先降低：

```bash
--batch-size 8
```

## 8. body-range 模式的优势

`body-range` 模式的核心优势是减少手工配置。

旧的 chapter-map 模式要求用户准备一个 `chapter_map.yml`，手动指定英文第几章对应中文第几章。例如：

```yaml
chapters:
  - id: ch001
    en_index: 5
    zh_index: 4
```

如果一本书有几十章，手动写映射会比较麻烦。并且不同 EPUB 的章节结构可能不稳定，有些中文 EPUB 会把多个章节放在同一个 spine item 里。

body-range 模式不要求你把所有章节逐个对应起来。你只需要选择英文和中文的正文总范围，程序会在内部自动切分句子，并用窗口方式完成对齐。

因此，当前推荐流程是：

先用 `preview_body_range` 看结构；
然后用 `--en-range` 和 `--zh-range` 选正文；
最后用 `run_align --mode body-range` 生成 Excel。

## 9. 可选功能：chapter-map 模式

如果你已经有比较准确的章节映射文件，也可以使用旧的 chapter-map 模式。

示例命令：

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

对应的 `chapter_map.yml` 可以写成：

```yaml
chapters:
  - id: prologue
    en_index: 4
    zh_index: 3
  - id: ch001
    en_index: 5
    zh_index: 4
  - id: ch002
    en_index: 6
    zh_index: 5
```

如果英文和中文的章节数量完全一致，也可以使用 `pipeline.gen_chapter_map` 自动生成映射文件。

例如：

```bash
python -m pipeline.gen_chapter_map \
  --en-start 5 \
  --en-end 44 \
  --zh-start 4 \
  --zh-end 43 \
  --id-start 1 \
  --out book/educated.chapter_map.yml
```

如果你已经手写了开头几章，想在后面追加自动生成的章节，可以使用：

```bash
python -m pipeline.gen_chapter_map \
  --en-start 5 \
  --en-end 44 \
  --zh-start 4 \
  --zh-end 43 \
  --id-start 1 \
  --append \
  --out book/educated.chapter_map.yml
```

不过，对于普通用户，仍然建议优先使用 body-range 模式。

## 10. 常见问题

### 10.1 为什么需要先预览 body range？

因为 EPUB 的结构不一定等于书的真实章节结构。很多 EPUB 前面会包含封面、目录、版权页、推荐语、序言等内容。如果直接对整本 EPUB 做对齐，这些非正文内容会干扰结果。

预览 body range 的目的就是先排除非正文部分，让程序只处理真正需要对齐的正文。

### 10.2 `4:38` 是什么意思？

这是闭区间范围。`4:38` 表示从 index 4 到 index 38，包含 4 和 38。

### 10.3 英文和中文范围的数字必须一样吗？

不需要。英文可以是 `4:38`，中文可以是 `3:37`。两个版本的 EPUB 结构经常不一样，只要它们覆盖的是同一段正文即可。

### 10.4 对齐结果一定准确吗？

不一定。BookAlign 是自动对齐工具，结果需要根据 `score` 和 `status` 判断。高分结果通常较可靠，低分结果需要人工检查。

建议把这个工具理解为“自动生成初稿”，而不是“完全不需要校对的最终结果”。

### 10.5 为什么第一次运行很慢？

第一次运行时，程序可能需要下载 embedding 模型，并计算整本书的句向量。后续重复运行时，如果模型、文本和 book id 没变，程序会复用 `.align_cache/` 下的缓存。

### 10.6 `.align_cache/` 可以删除吗？

可以。删除后不会影响源文件和输出 Excel，但下次运行需要重新计算 embedding。

### 10.7 输出 Excel 可以手动修改吗？

可以。输出文件是普通 `.xlsx` 文件，可以用 Excel、LibreOffice、WPS 或 Python 的 openpyxl 继续处理。

### 10.8 Windows 可以用吗？

对齐流程本身可以用。需要注意的是，当前 `excel_speaker.py` 的朗读功能主要依赖 macOS 的 `say` 命令。Windows 上可以先使用 Excel 文件本身，或者后续把朗读模块替换为 Windows TTS。

### 10.9 我应该先用哪个模型？

建议先用：

```bash
--model intfloat/multilingual-e5-small
--device cpu
--batch-size 16
```

这个组合比较适合先跑通流程。确认流程正常后，再考虑换成更大的模型。

## 11. 推荐的完整命令模板

假设你的文件是：

```text
book/MyBook.en.epub
book/MyBook.zh.epub
```

推荐完整流程如下。

第一步，预览：

```bash
mkdir -p output/mybook

python -m pipeline.preview_body_range \
  --en book/MyBook.en.epub \
  --zh book/MyBook.zh.epub \
  --out output/mybook/body_preview.html \
  --open
```

第二步，在浏览器中查看 `body_preview.html`，记下英文和中文正文范围。假设得到：

```text
英文：4:38
中文：3:37
```

第三步，运行对齐：

```bash
python -m pipeline.run_align \
  --book-id mybook \
  --mode body-range \
  --en book/MyBook.en.epub \
  --zh book/MyBook.zh.epub \
  --en-range 4:38 \
  --zh-range 3:37 \
  --model intfloat/multilingual-e5-small \
  --device cpu \
  --batch-size 16 \
  --out output/mybook/aligned.xlsx
```

第四步，打开阅读器：

```bash
python pipeline/excel_speaker.py
```

然后选择：

```text
output/mybook/aligned.xlsx
```

## 12. 项目当前定位

BookAlign 当前是一个面向个人阅读和语言学习的轻量工具。它优先解决的是“怎么把同一本书的英文 EPUB 和中文 EPUB 快速对齐成可读的 Excel”。

当前版本的重点是：

让普通电脑可以运行；
减少手工 chapter map；
优先支持 body range 这种更简单的使用流程；
导出便于人工检查和后续阅读的 Excel；
保留旧的 chapter-map 模式作为可选方案。

它暂时不追求复杂的交互式修正、出版级排版、整本书百分百准确对齐，或者完整替代专业双语语料制作流程。更合理的使用方式是：

先自动生成对齐初稿，再根据 `status` 和阅读体验进行人工检查。
