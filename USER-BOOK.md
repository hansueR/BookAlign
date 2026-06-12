mkdir -p output/educated

python -m pipeline.inspect_chapters \
  --en book/Educated.en.epub \
  --zh book/Educated.zh.epub \
  --out output/educated/chapter_preview.txt \
  --preview-chars 1000


python -m pipeline.inspect_chapters \
  --en book/The_Alchemist.en.epub \
  --zh book/The_Alchemist.zh.epub \
  --out output/The_Alchemist/chapter_preview.txt \
  --preview-chars 1000
  
  
查看 epub 文件结构

```bash
python -m pipeline.debug_epub_structure \
  --epub book/The_Alchemist.zh.epub \
  --out output/The_Alchemist/debug_zh_structure.txt
```


自动生成章节映射文件

```yaml
chapters:
  - id: ch001
    en_index: 5
    zh_index: 4
```

`pipeline/gen_chapter_map.py`：


如果你想从头生成一个完整 map，比如英文正文从 `5` 到 `44`，中文正文从 `4` 到 `43`：

```bash
python -m pipeline.gen_chapter_map \
  --en-start 5 \
  --en-end 44 \
  --zh-start 4 \
  --zh-end 43 \
  --id-start 1 \
  --out book/educated.chapter_map.yml
```

它会生成：

```yaml
chapters:
  - id: ch001
    en_index: 5
    zh_index: 4
  - id: ch002
    en_index: 6
    zh_index: 5
  - id: ch003
    en_index: 7
    zh_index: 6
```

如果你已经手写了开头，比如：

```yaml
chapters:
  - id: prologue
    en_index: 4
    zh_index: 3
```

然后想从 `ch001` 开始追加剩下的章节，就用 `--append`：

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

它会保留你已有的 `prologue`，然后把 `ch001` 到后面的章节追加进去。

注意四个数字都是闭区间，也就是包括起点和终点。脚本会检查英文数量和中文数量是否一致；如果不一致，会直接报错，避免生成错位 map。
