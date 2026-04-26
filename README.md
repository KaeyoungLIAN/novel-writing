# 📖 Grok 长篇小说自动写作工具

> 基于 Grok API 的自动化长篇中文小说写作工具。
> 将角色设定与故事大纲，自动扩展为 10 章、每章约 8000 字的长篇小说，并导出为 PDF。

## ✨ 功能特性

- **分步生成**：大纲 → 分段要点 → 逐段正文 → 拼接 → PDF，每一步都可审阅和干预
- **固定 Prompt 设计**：精心设计的写作指令模板，保证文章结构自然、不生硬
- **上下文联贯**：每段生成时传入上一段结尾，确保文风与内容连贯
- **自动重试**：API 调用失败时自动重试 3 次
- **中间产物保存**：章节大纲、分段要点、每章全文均可保存为 JSON/TXT，便于调试和断点续写
- **精美 PDF 导出**：自动识别中文字体，含封面、目录、章标题、页码

## 🏗️ 项目结构

```
novel-writing/
├── README.md                 # 项目说明
├── requirements.txt          # Python 依赖
├── config.py                 # API 配置与写作 Prompt 模板
├── grok_client.py            # Grok API 客户端（含重试机制）
├── story_generator.py        # 小说生成管线（核心逻辑）
├── pdf_exporter.py           # PDF 导出模块
├── main.ipynb                # Jupyter Notebook 主入口（一键运行）
├── user_inputs/              # 用户设定目录
│   ├── characters.txt        # 角色设定（示例）
│   ├── plot.txt              # 故事大纲（示例）
│   └── style.txt             # 写作风格（示例）
├── outputs/                  # 生成结果输出目录
│   ├── chapter_outlines.json # 10 章大纲
│   ├── chapter_1_segments.json
│   ├── chapter_1_full.txt
│   ├── novel_full.txt        # 完整小说文本
│   └── novel.pdf             # 最终 PDF
└── samples/
    └── example_inputs/       # 更多示例输入
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 Grok API Key

前往 [xAI Console](https://console.x.ai) 注册并获取 API Key。

### 3. 编辑小说设定

编辑 `user_inputs/` 目录下的三个文件：

| 文件 | 内容 | 说明 |
|------|------|------|
| `characters.txt` | 角色设定 | 每个人物的姓名、性格、背景、关系 |
| `plot.txt` | 故事大纲 | 整体情节走向、核心冲突、关键转折 |
| `style.txt` | 写作风格 | 语言风格、叙事视角、节奏特点 |

也可在 `main.ipynb` 的 Python 字符串中直接编辑。

### 4. 运行 Jupyter Notebook

```bash
jupyter notebook main.ipynb
```

按顺序执行每个单元格即可。

## 📋 工作流程

```
角色设定 + 故事大纲 + 写作风格
        │
        ▼
  [第 2 步] Grok API → 10 章大纲（每章 200–300 字）
        │
        ▼
  [第 3 步] Grok API → 每章拆 10 段（每段 50–80 字要点）
        │
        ▼
  [第 4 步] Grok API → 逐段正文（每段 ~800 字）
        │
        ▼
  [第 5 步] 拼接全文（10 章 × 10 段 ≈ 8 万字）
        │
        ▼
  [第 6 步] 导出 PDF（含封面、目录、页码）
```

## ⚙️ 配置说明

### API 参数（在 Notebook 中设置）

```python
GROK_API_KEY = "xai-..."     # 必填
GROK_MODEL = "grok-3-mini"   # 可选
GROK_TEMPERATURE = 1.0       # 可选
GROK_MAX_TOKENS = 16384      # 可选
```

### Prompt 模板（在 config.py 中调整）

`config.py` 包含所有写作指令模板：

| 常量 | 用途 |
|------|------|
| `SYSTEM_PROMPT_WRITER` | 小说家的系统角色设定 |
| `PROMPT_GENERATE_CHAPTER_OUTLINES` | 生成 10 章大纲 |
| `PROMPT_SPLIT_CHAPTER_INTO_SEGMENTS` | 每章拆 10 段要点 |
| `PROMPT_WRITE_SEGMENT` | 逐段正文写作 |

可以根据需要调整这些 Prompt 来改变写作风格。

### PDF 排版（在 config.py 中调整）

```python
PDF_TITLE_FONT_SIZE = 24     # 封面标题字号
PDF_CHAPTER_FONT_SIZE = 18   # 章标题字号
PDF_BODY_FONT_SIZE = 12      # 正文字号
PDF_LINE_SPACING = 1.5       # 行间距
PDF_MARGIN_MM = 25           # 页边距（mm）
```

## 🔧 技术栈

| 组件 | 技术选型 |
|------|---------|
| 语言 | Python 3.11+ |
| API 接口 | OpenAI 兼容格式（Grok API） |
| HTTP 客户端 | httpx（支持超时与重试） |
| PDF 生成 | reportlab（含中文字体自动检测） |
| 运行环境 | Jupyter Notebook |
| 项目组织 | 模块化 .py + .ipynb 调用 |

## 🔄 断点续写

如果写作过程中因 API 错误中断，Notebook 附录中提供了断点续写功能。
只需指定从第几章继续，即可恢复写作，无需重新生成。

## 📄 许可

MIT License
