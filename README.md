# PaperWiki

将 PDF 学术论文自动转换为 Obsidian 结构化阅读笔记。

放入 PDF → 自动生成 Markdown 报告 → 在 Obsidian 中查看知识图谱。

## 功能

- **文件夹监控** — 监听论文目录，新增 PDF 自动触发处理
- **多角度并行分析** — 5 个视角（元数据提取、核心贡献、方法分析、实验分析、批判分析）并行执行
- **结构化报告** — TL;DR、研究背景、核心方法、关键发现、关键概念、参考文献
- **知识图谱** — 实体自动提取并以 `[[wiki-link]]` 格式输出，在 Obsidian 中形成关联网络
- **Pydantic 校验 + 重试** — LLM 输出自动验证格式，不符合时反馈修复
- **SHA256 去重** — 已处理的论文不会重复生成
- **多后端支持** — Ollama / OpenAI / DeepSeek / MiniMax / 通义千问 / 自定义接口

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制 `config.yaml.example` 为 `config.yaml`，编辑以下内容：

```yaml
paths:
  raw_papers: ~/Documents/raw_papers         # 论文 PDF 存放目录
  obsidian_vault: ~/Documents/Obsidian Vault  # Obsidian Vault 路径
  wiki_subdir: wiki                           # 报告子目录

ai:
  backend: minimax                            # ollama | openai | deepseek | minimax | qwen | custom
  minimax:
    base_url: https://api.minimax.chat/v1
    api_key: ${MINIMAX_API_KEY}               # 支持环境变量
    model: MiniMax-M2.7-highspeed

report:
  multi_angle: True                           # 多角度分析（推荐开启）
```

### 3. 启动

```bash
python3 paperwiki/main.py
```

程序开始监控 `raw_papers` 目录，放入 PDF 即可自动生成报告到 Obsidian。

## 使用方式

### 命令行

```
python3 paperwiki/main.py
```

放入论文到 `raw_papers` 目录，报告自动生成到 Obsidian vault 的 `wiki/` 子目录。

### 打包为独立程序

```bash
pip install pyinstaller
python3 -m PyInstaller paperwiki.spec
```

构建完成后，`dist/` 目录包含可直接分发的 `paperwiki` 可执行文件。用户只需编辑同目录下的 `config.yaml`，双击 `launcher.command`（macOS）或 `launcher.bat`（Windows）即可使用，无需安装 Python。

## 多角度分析

启用 `multi_angle: True` 后，5 个分析视角并行执行：

| 视角 | 内容 |
|------|------|
| 元数据提取 | 标题、作者、摘要、关键词、参考文献 |
| 核心贡献 | 研究问题、创新点、学术价值 |
| 方法分析 | 技术路线、关键组件、创新、流程 |
| 实验分析 | 数据集、基准方法、主要结果、消融实验 |
| 批判分析 | 优势、局限性、假设、改进方向 |

所有视角结果由综述 Agent 综合成最终报告。

## 报告示例

生成的 Markdown 报告包含以下章节，可直接在 Obsidian 中查看：

- **TL;DR** — 论文概述
- **研究背景** — 问题动机
- **核心方法** — 技术方案说明
- **关键发现** — 实验结论
- **关键概念** — 实体及 Wiki 链接
- **论文信息** — 作者、关键词、摘要
- **参考文献**

## 项目结构

```
PaperWiki/
├── paperwiki/
│   ├── main.py              # 入口：watchdog 文件监控
│   ├── config.py            # 配置加载与校验
│   ├── pdf_extractor.py     # PDF 文本提取（PyMuPDF）
│   ├── ai_client.py         # AI 客户端（多后端、同步/异步）
│   ├── report_generator.py  # 报告生成（单次 + 多角度分析）
│   └── obsidian_writer.py   # Obsidian 文件输出与去重
├── tests/                   # 测试（31 个）
├── config.yaml.example      # 配置模板
├── paperwiki.spec           # PyInstaller 打包配置
├── launcher.command         # macOS 启动脚本
├── launcher.bat             # Windows 启动脚本
└── requirements.txt
```

## License

MIT
