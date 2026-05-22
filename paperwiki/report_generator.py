import json
import logging
from datetime import datetime
from jinja2 import Template
from paperwiki.config import Config

logger = logging.getLogger("paperwiki.report_generator")

SYSTEM_PROMPT = """你是一个学术论文分析助手。根据提供的论文文本，生成一份JSON格式的分析报告。
JSON必须包含以下字段：
- title: 论文标题
- summary: 300字以内的中文摘要
- entities: 数组，每项含 name(名称) 和 type(类型，取值为: 人物/术语/概念/方法)
- references: 数组，重要参考文献列表

只返回JSON，不要包含其他文字。"""

REPORT_TEMPLATE = """# {{ title }}

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
*自动生成于 {{ generated_at }} | 来源: {{ source_file }}*"""


class ReportGenerator:
    def __init__(self, config: Config, ai_client):
        self.ai_client = ai_client
        self.template = Template(REPORT_TEMPLATE)

    def _call_ai(self, paper_text: str) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": paper_text},
        ]
        response = self.ai_client.chat(messages)
        try:
            return json.loads(self._extract_json(response))
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse AI response as JSON. Raw response:\n%s",
                response,
            )
            raise

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def generate_report(self, paper_text: str, metadata: dict, source_file: str) -> str:
        ai_result = self._call_ai(paper_text)

        title = ai_result.get("title", metadata.get("title", "Untitled"))
        summary = ai_result.get("summary", "")
        entities = ai_result.get("entities", [])
        references = ai_result.get("references", [])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        markdown = self.template.render(
            title=title,
            summary=summary,
            entities=entities,
            references=references,
            generated_at=now,
            source_file=source_file,
        )
        return markdown
