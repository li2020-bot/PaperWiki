# PaperWiki 设计文档

## 概述

一个 macOS 本地 AI 代理工具，监控 `raw_papers` 文件夹中的 PDF 论文文件，自动使用 AI 提取摘要、实体信息，生成带 Obsidian 双链（`[[wiki 链接]]`）的 Markdown 学习报告，写入 Obsidian vault 的 wiki 目录。

## 架构方案：模块化流水线

```
config.yaml → pdf_extractor ──→ ai_client ──→ report_generator
                  │                                 ↓
                  │                            obsidian_writer
                  │                                 ↓
                  └──────── raw text ──────→ {wiki_subdir}/raw/
                  ↑                              ↑
                watcher (触发入口)
```

6 个独立模块，通过明确接口协作。PDF 提取后同时走两条路径：AI 生成报告 + 原始文本存档。

## 项目结构

```
PaperWiki/
├── config.yaml              # 用户配置文件
├── requirements.txt         # Python 依赖
├── paperwiki/               # 主包
│   ├── __init__.py
│   ├── main.py              # 入口：启动 watchdog 监控
│   ├── config.py            # 读取解析 config.yaml
│   ├── pdf_extractor.py     # PyMuPDF 提取文本
│   ├── ai_client.py         # AI 调用（多后端）
│   ├── report_generator.py  # 组装 prompt → 调用 AI → 解析结果
│   └── obsidian_writer.py   # 写入 Markdown 到 Obsidian vault
├── tests/                   # 单元测试
│   ├── test_pdf_extractor.py
│   ├── test_ai_client.py
│   ├── test_report_generator.py
│   └── test_obsidian_writer.py
└── processed_files.json     # 已处理文件记录（自动生成）
```

数据流：`PDF 文件 → pdf_extractor → 纯文本 → ai_client → AI 结构化输出 → report_generator → Markdown → obsidian_writer → .md 文件`

## 配置文件 config.yaml

```yaml
paths:
  raw_papers: ~/Documents/raw_papers
  obsidian_vault: ~/Documents/ObsidianVault
  wiki_subdir: wiki
  raw_subdir: raw              # wiki 内的原始文本子目录

ai:
  backend: ollama              # ollama | openai | deepseek | minimax | qwen | custom
  ollama:
    base_url: http://localhost:11434
    model: qwen3
  openai:
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    model: gpt-4o
  deepseek:
    base_url: https://api.deepseek.com
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
  minimax:
    base_url: https://api.minimax.chat/v1
    api_key: ${MINIMAX_API_KEY}
    model: MiniMax-M1
  qwen:
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: ${QWEN_API_KEY}
    model: qwen-plus
  custom:
    base_url: https://your-api-endpoint
    api_key: ${CUSTOM_API_KEY}
    model: your-model-name

report:
  language: zh-CN

processing:
  temp_dir: /tmp/paperwiki
```

- `api_key` 支持 `${ENV_VAR}` 格式引用环境变量
- 切换后端只需改 `backend` 一个字段
- 路径支持 `~` 展开为用户主目录

## 模块设计

### pdf_extractor.py
- 使用 PyMuPDF (fitz) 打开 PDF，逐页提取文本
- 大 PDF（>50页）分段写入 `temp_dir`，分批调用 AI 后合并结果
- 同时提取 PDF 元数据（标题、作者）
- 接口：`extract_text(pdf_path: str) -> tuple[str, dict]` 返回（文本, 元数据）

### ai_client.py
- 统一抽象，根据 `backend` 字段选择具体后端
- 所有云端后端（openai/deepseek/minimax/qwen/custom）共用 OpenAI 兼容协议调用逻辑，仅 `base_url`、`api_key`、`model` 不同
- Ollama 使用 `ollama` Python 库
- 接口：`chat(messages: list[dict]) -> str`
- temperature 设为 0.3 以保证结构化输出一致性

### report_generator.py
- 构建中文 system prompt，要求 AI 返回 JSON：
  - 摘要（summary）
  - 实体列表（entities）：含名称和类型（人物/术语/概念/方法）
  - 参考文献（references）
- 调用 `ai_client.chat()`，解析返回的 JSON
- 实体转为 `[[实体名]]` Obsidian 双链格式
- 渲染 Jinja2 模板生成最终 Markdown
- 接口：`generate_report(paper_text: str, metadata: dict) -> str`，metadata 包含 pdf_extractor 提取的标题、作者等

### obsidian_writer.py
- `save_report()`：将报告 Markdown 写入 `{obsidian_vault}/{wiki_subdir}/{论文标题}.md`
- `save_raw_text()`：将 PDF 原始提取文本写入 `{obsidian_vault}/{wiki_subdir}/{raw_subdir}/{论文标题}.md`
- 文件名特殊字符清洗
- 记录到 `processed_files.json`（文件哈希 → 时间戳），防重复处理

### main.py
- 启动时读取配置，创建必要的文件夹
- 使用 watchdog 监控 `raw_papers`，监听新文件事件
- 仅处理新文件，已处理过的跳过（通过 `processed_files.json`）
- 新 PDF → 触发流水线：提取 → 保存原始文本 → AI 分析 → 生成报告 → 写入
- 处理失败记录到 `error.log`

## AI Prompt 结构

System prompt:
```
你是一个学术论文分析助手。根据提供的论文文本，生成一份JSON格式的分析报告。
JSON必须包含以下字段：
- title: 论文标题
- summary: 300字以内的中文摘要
- entities: 数组，每项含 name(名称) 和 type(类型，取值为: 人物/术语/概念/方法)
- references: 数组，重要参考文献列表
```

## 已处理文件追踪

`processed_files.json` 结构：
```json
{
  "/path/to/paper.pdf": {
    "hash": "sha256_abc123",
    "processed_at": "2026-05-22T10:30:00",
    "output_file": "paper_title.md"
  }
}
```

使用文件哈希（SHA256）确保即使文件重命名也不会重复处理。

## 错误处理

- PDF 提取失败 → 记录 `error.log`，跳过
- AI 调用超时 → 最多重试 3 次，间隔递增
- AI 返回 JSON 解析失败 → 记录原始响应到 `error.log`，跳过
- 文件夹不存在 → 自动创建

## 报告 Markdown 模板

```markdown
# {{ title }}

## 摘要
{{ summary }}

## 关键实体
{% for entity in entities %}
- [[{{ entity.name }}]] ({{ entity.type }})
{% endfor %}

## 参考文献
{% for ref in references %}
- {{ ref }}
{% endfor %}

## 原始文本
- [[raw/{{ title }}|查看原始提取文本]]

---
*自动生成于 {{ generated_at }} | 来源: {{ source_file }}*
```

## 依赖

- watchdog — 文件夹监控
- PyMuPDF (fitz) — PDF 文本提取
- ollama — Ollama API 客户端
- openai — OpenAI 兼容 API 客户端
- PyYAML — 配置解析
- Jinja2 — 模板渲染
- pytest — 测试框架
