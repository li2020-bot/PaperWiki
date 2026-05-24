import os
import json
import logging
import re
import time
import asyncio
from datetime import datetime
from typing import Literal

from jinja2 import Template
from pydantic import BaseModel, ValidationError

from paperwiki.config import Config

logger = logging.getLogger("paperwiki.report_generator")

# ---------------------------------------------------------------------------
# Pydantic output schemas
# ---------------------------------------------------------------------------


class Entity(BaseModel):
    name: str
    type: Literal["人物", "术语", "概念", "方法"]
    brief: str


class MetadataOutput(BaseModel):
    title: str
    authors: list[str] = []
    abstract: str = ""
    keywords: list[str] = []
    references: list[str] = []


class ContributionOutput(BaseModel):
    problem: str
    contributions: list[str]
    novelty: str
    significance: str


class MethodOutput(BaseModel):
    approach: str
    key_techniques: list[str]
    innovations: str
    pipeline: str
    entities: list[Entity] = []


class ExperimentOutput(BaseModel):
    datasets: str
    baselines: str
    main_results: list[str]
    ablation: str
    key_findings: list[str]


class CriticalOutput(BaseModel):
    strengths: list[str]
    limitations: list[str]
    assumptions: str
    future_work: str


class ReportOutput(BaseModel):
    title: str
    authors: list[str] = []
    abstract: str = ""
    keywords: list[str] = []
    tldr: str
    background: str
    method: str
    key_findings: list[str]
    entities: list[Entity] = []
    references: list[str] = []


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个学术论文分析助手。根据论文的原始文本，提取以下内容，帮助读者快速理解这篇论文的核心贡献和方法。

论文的标题、作者名、摘要通常在第一页的前几行，关键词通常在摘要附近。请从文本中准确识别这些信息。

返回JSON，包含以下字段：
- title: 论文标题（原文语言）
- authors: 数组，作者姓名列表，从论文第一页作者信息中提取。只包含人名本身，不包含机构、邮箱、编号、星号上标等
- abstract: 论文摘要原文（如果文本中包含）
- keywords: 数组，5-8个核心关键词
- tldr: 完整概述论文的核心贡献和意义，包含：论文要解决的问题、提出的方法、关键发现和学术影响（中文，150-200字）
- background: 详细说明研究背景、问题动机、以及为什么该问题值得研究（中文，250-350字）
- method: 详细说明核心方法，清楚解释设计思路、关键组件及其作用，用通俗语言但保留必要的技术细节（中文，350-500字）
- key_findings: 数组，4-6条最重要的实验发现或结论，每条写清楚发现了什么、有什么数据支撑、意味着什么（中文，每条80-120字）
- entities: 数组，每项含 name(名称)、type(类型，取值为: 人物/术语/概念/方法) 和 brief(用一句话解释该实体是什么，20字以内)
- references: 数组，论文中引用的主要参考文献

注意：
- 不要将图表编号（Figure X、Table X、图X、表X）作为实体提取。
- 作者名中不要包含机构名称（如Google、MIT等）、邮箱地址、数字编号、∗†等符号。
只返回JSON，不要包含其他文字。"""

REPORT_TEMPLATE = """## TL;DR
{{ tldr }}

## 研究背景
{{ background }}

## 核心方法
{{ method }}

## 关键发现
{% for f in key_findings %}
- {{ f }}
{% endfor %}

## 关键概念
{% for entity in entities %}
- **[[{{ entity.name }}]]**（{{ entity.type }}）— {{ entity.brief }}
{% endfor %}

## 论文信息
- **作者**：{% for author in authors %}[[{{ author }}]]{% if not loop.last %}、{% endif %}{% endfor %}
- **关键词**：{% for kw in keywords %}[[{{ kw }}]]{% if not loop.last %}、{% endif %}{% endfor %}
- **摘要**：{{ abstract }}

## 参考文献
{% for ref in references %}
- {{ ref }}
{% endfor %}

---
*自动生成于 {{ generated_at }} | 来源: {{ source_file }}*"""

# ---------------------------------------------------------------------------
# Multi-angle analysis: angle definitions
# ---------------------------------------------------------------------------

ANGLE_METADATA = {
    "name": "metadata",
    "label": "元数据提取",
    "response_model": MetadataOutput,
    "system_prompt": """你是一个学术论文文献整理专家。从论文文本中准确提取以下元数据信息。

论文的标题、作者名、摘要通常在第一页的前几行，关键词通常在摘要附近。

返回JSON：
- title: 论文标题（原文语言）
- authors: 数组，作者姓名列表。只包含人名本身，不包含机构名称（如Google、MIT等）、邮箱地址、数字编号、∗†等符号
- abstract: 论文摘要原文（如果文本中包含）
- keywords: 数组，5-8个核心关键词
- references: 数组，论文中引用的主要参考文献列表

只返回JSON，不要包含其他文字。""",
}

ANGLE_CONTRIBUTION = {
    "name": "core_contribution",
    "label": "核心贡献",
    "response_model": ContributionOutput,
    "system_prompt": """你是一个学术论文评审专家，专注于识别论文的核心贡献和创新点。

请仔细阅读论文，分析以下方面：
1. 论文解决了什么问题？该问题的背景和动机是什么？
2. 核心创新点是什么？与已有方法的关键区别在哪里？
3. 该研究的学术价值和应用前景如何？

返回JSON：
- problem: 论文要解决的问题，详细说明背景、动机以及该问题为什么重要（中文，300字以内）
- contributions: 数组，3-5条核心贡献，每条写清楚做了什么、怎么做的、为什么有意义（中文，每条120字以内）
- novelty: 与已有工作相比的创新之处，具体说明技术差异和突破点（中文，200字以内）
- significance: 学术价值和应用前景的详细评估（中文，150字以内）

只返回JSON，不要包含其他文字。""",
}

ANGLE_METHOD = {
    "name": "method_analysis",
    "label": "方法分析",
    "response_model": MethodOutput,
    "system_prompt": """你是一个技术专家，擅长理解学术论文中的技术方法。请深入分析论文的技术方案。

关注以下方面：
1. 整体技术路线和框架设计
2. 关键算法、模型结构或技术组件
3. 方法上的创新点，与已有技术的区别
4. 实现流程或pipeline

用通俗易懂的语言解释，避免过于技术化的细节。

返回JSON：
- approach: 技术路线整体概述，详细说明设计思路和原理（中文，300字以内）
- key_techniques: 数组，3-5个关键技术点或组件，每个写清楚是什么、起什么作用（中文，每条100字以内）
- innovations: 方法层面的创新之处，说明与已有技术的具体差异（中文，200字以内）
- pipeline: 方法流程详述，从输入到输出的完整步骤（中文，200字以内）
- entities: 数组，论文中出现的核心方法/概念实体。每项含 name(名称)、type(类型，取值为: 术语/概念/方法)、brief(一句话解释，20字以内)。不要包含图表编号（Figure X、Table X等）

只返回JSON，不要包含其他文字。""",
}

ANGLE_EXPERIMENT = {
    "name": "experiment_analysis",
    "label": "实验分析",
    "response_model": ExperimentOutput,
    "system_prompt": """你是一个实验评估专家。分析论文的实验设计和结果。

关注以下方面：
1. 使用了哪些数据集？规模和特点如何？
2. 对比了哪些基准方法（baselines）？
3. 主要实验结果是什么？是否有统计显著性？
4. 是否有消融实验（ablation study）？结论是什么？

返回JSON：
- datasets: 数据集详细信息，包括规模、领域、特点（中文，200字以内）
- baselines: 对比的基准方法，说明每种方法的特点和对比目的（中文，200字以内）
- main_results: 数组，3-5条主要实验结果，每条包含具体数据和对比说明（中文，每条120字以内）
- ablation: 消融实验的关键发现，具体说明每项消融的结论（中文，150字以内，如论文无消融实验则写"无"）
- key_findings: 数组，3-5条最重要的实验发现或结论，每条写清楚发现内容和支撑证据（中文，每条120字以内）

只返回JSON，不要包含其他文字。""",
}

ANGLE_CRITICAL = {
    "name": "critical_review",
    "label": "批判分析",
    "response_model": CriticalOutput,
    "system_prompt": """你是一个严格的学术论文审稿人。对论文进行批判性分析。

从以下角度进行评估：
1. 论文的主要优势和亮点
2. 方法或实验的局限性和不足
3. 关键假设条件是否合理
4. 未来可能的改进方向

请保持客观、平衡的态度，既指出优点也点明不足。

返回JSON：
- strengths: 数组，2-3条主要优势，每条详细说明优势是什么、为什么是优势（中文，每条100字以内）
- limitations: 数组，2-3条局限性或不足，每条详细说明限制是什么、对结果的影响（中文，每条100字以内）
- assumptions: 关键假设条件，逐一列出并评估其合理性（中文，150字以内）
- future_work: 可能的改进方向或后续研究建议，具体说明改进思路（中文，150字以内）

只返回JSON，不要包含其他文字。""",
}

ANGLES = [ANGLE_METADATA, ANGLE_CONTRIBUTION, ANGLE_METHOD, ANGLE_EXPERIMENT, ANGLE_CRITICAL]

# ---------------------------------------------------------------------------
# Synthesizer prompt
# ---------------------------------------------------------------------------

SYNTHESIZER_PROMPT = """你是一个学术论文综述撰写专家。你的任务是根据多个角度的分析结果，生成一份完整、统一、高质量的论文阅读报告。

你会收到：
1. 论文原文的前2000字（供参考）
2. 五个角度的分析结果（JSON格式）：
   - metadata: 标题、作者、摘要、关键词、参考文献
   - core_contribution: 问题、贡献、创新点、价值
   - method_analysis: 技术路线、关键技术、方法创新、流程、实体
   - experiment_analysis: 数据集、baseline、结果、消融实验、关键发现
   - critical_review: 优势、局限性、假设、未来方向

你需要综合所有角度的信息，生成一份全面、平衡的报告。规则：
- title、authors、abstract、keywords、references 以 metadata 的结果为准
- tldr 综合所有角度的核心信息，写一段150-200字的完整概述，包含：论文要解决的问题、提出的方法、关键实验发现和学术意义。要具体，不要泛泛而谈
- background 基于 core_contribution 的 problem，详细阐述研究背景、问题动机、以及该问题为什么值得研究（中文，250-350字）
- method 综合 method_analysis 的 approach、key_techniques、innovations 和 pipeline，写一份详细的方法说明。要清楚地解释技术方案的设计思路、关键组件及其作用、方法的创新之处。用通俗语言，但保留必要的技术细节（中文，350-500字）
- key_findings 综合 experiment_analysis 的关键发现和 core_contribution 的贡献，列出4-6条最重要的发现。每条写清楚发现了什么、有什么数据支撑、意味着什么（中文，每条80-120字）
- entities 综合所有角度的实体，去重并统一命名。同一概念的不同写法（如 Self-Attention / Self Attention / self-attention）统一为一个标准名称，优先使用论文原文中的英文术语
- 如果某个角度的分析缺失，用其他角度的信息补充

返回JSON：
- title: 论文标题
- authors: 数组
- abstract: 摘要
- keywords: 数组
- tldr: 完整概述，150-200字（中文）
- background: 详细研究背景，250-350字（中文）
- method: 详细方法说明，350-500字（中文）
- key_findings: 数组，4-6条关键发现，每条80-120字（中文）
- entities: 数组，{name, type(人物/术语/概念/方法), brief(20字以内)}
- references: 数组

只返回JSON，不要包含其他文字。"""

# ---------------------------------------------------------------------------
# Name extraction utilities
# ---------------------------------------------------------------------------

_NON_NAME = re.compile(
    r"University|Institute|Department|Laboratory|College|School|"
    r"Research|Center|Centre|Corporation|Inc\.?|Ltd\.?|"
    r"©|@|http|www\.|email|"
    r"Google|Microsoft|Facebook|Amazon|Apple|IBM|Intel|NVIDIA|Baidu|Tencent|Alibaba|"
    r"^\d+$|^[∗†‡§¶#*]+$",
    re.IGNORECASE,
)

_EMAIL = re.compile(r"\S+@\S+")


def _looks_like_person_name(part: str) -> bool:
    part = part.strip().rstrip("0123456789∗†‡,*")
    if not part or len(part) < 2 or len(part) > 80:
        return False
    if _NON_NAME.search(part):
        return False
    if any(c.isupper() for c in part):
        return True
    if re.search(r"[一-鿿]", part):
        return len(part) <= 6
    return False


def _try_extract_name(text: str) -> str | None:
    text = re.sub(r"[∗†‡]", "", text).strip()
    if not text or len(text) < 2 or len(text) > 80:
        return None
    if _looks_like_person_name(text):
        return text
    name_tokens: list[str] = []
    for w in text.split():
        w_clean = w.strip().rstrip("0123456789,*")
        if _looks_like_person_name(w_clean):
            name_tokens.append(w_clean)
        else:
            break
    if name_tokens:
        name = " ".join(name_tokens)
        if len(name) >= 2:
            return name
    return None


def _split_authors(author_strings: list[str]) -> list[str]:
    names: list[str] = []
    for s in author_strings:
        s = _EMAIL.sub("", s)
        for part in re.split(r",\s*|\s+(?:and|&)\s+|\s{2,}", s):
            part = re.sub(r"\s+et\s+al\.?\s*$", "", part, flags=re.IGNORECASE).strip()
            name = _try_extract_name(part)
            if name:
                names.append(name)
    seen = set()
    unique = []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            unique.append(n)
    return unique


_FIG_TABLE_PATTERN = re.compile(r"^(?:Figure|Fig\.?|Table|图|表)\s*\d", re.IGNORECASE)


def _filter_entities(entities: list[dict]) -> list[dict]:
    return [e for e in entities if not _FIG_TABLE_PATTERN.match(e.get("name", ""))]


def _normalize_entity_name(name: str) -> str:
    """Collapse casing, whitespace, dashes, and Unicode variants so similar names match."""
    import unicodedata
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[\s\-_—–―]+", " ", name)
    return name.strip().lower()


def _dedupe_entities(entities: list[dict]) -> list[dict]:
    from difflib import SequenceMatcher

    unique: list[dict] = []
    for e in entities:
        norm = _normalize_entity_name(e.get("name", ""))
        if any(
            _normalize_entity_name(u["name"]) == norm
            or SequenceMatcher(None, _normalize_entity_name(u["name"]), norm).ratio() >= 0.85
            for u in unique
        ):
            continue
        unique.append(e)
    return unique


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:
    def __init__(self, config: Config, ai_client):
        self.config = config
        self.ai_client = ai_client
        self.template = Template(REPORT_TEMPLATE)

    # ---- JSON extraction & repair -----------------------------------------

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        if not text:
            return "{}"

        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        if not text:
            return "{}"

        if text.startswith("{"):
            depth = 0
            for i, ch in enumerate(text):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[:i + 1]
            return text

        start = text.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]

        return text

    @staticmethod
    def _repair_json(text: str) -> str:
        """Fix common LLM JSON formatting errors: trailing commas, unquoted keys, single quotes."""
        text = re.sub(r",\s*([}\]])", r"\1", text)
        text = re.sub(
            r'([{,])\s*([a-zA-Z_一-鿿][a-zA-Z0-9_一-鿿]*)\s*:',
            r'\1"\2":',
            text,
        )
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        return text

    @classmethod
    def _format_pydantic_errors(cls, e: ValidationError) -> str:
        lines = []
        for err in e.errors()[:12]:
            loc = ".".join(str(x) for x in err["loc"])
            lines.append(f"  - {loc}: {err['msg']}")
        return "\n".join(lines)

    @classmethod
    def _validate_with_model(cls, model: type[BaseModel], json_str: str) -> tuple[dict | None, str]:
        """Try Pydantic validation on extracted JSON string.

        Returns (dict, "") on success, or (None, error_message) on failure.
        """
        # Attempt 1: direct parse
        try:
            return model.model_validate_json(json_str).model_dump(), ""
        except ValidationError as e:
            return None, cls._format_pydantic_errors(e)
        except (json.JSONDecodeError, ValueError):
            pass

        # Attempt 2: repair then parse
        repaired = cls._repair_json(json_str)
        try:
            return model.model_validate_json(repaired).model_dump(), ""
        except ValidationError as e:
            return None, cls._format_pydantic_errors(e)
        except (json.JSONDecodeError, ValueError) as e:
            return None, f"JSON语法错误（修复后仍无法解析）: {e}"

    # ---- AI call with schema validation + retry ---------------------------

    def _call_ai(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_model: type[BaseModel] | None = None,
        stage: str = "",
        max_format_retries: int = 5,
    ) -> dict:
        sp = system_prompt if system_prompt is not None else SYSTEM_PROMPT
        current_prompt = prompt

        for attempt in range(max_format_retries + 1):
            if len(current_prompt) > 12000:
                current_prompt = current_prompt[:12000] + "\n\n[... 文本过长，已截断 ...]"

            messages = [
                {"role": "system", "content": sp},
                {"role": "user", "content": current_prompt},
            ]
            response = self.ai_client.chat(messages)

            if response_model is None:
                # No schema — best-effort JSON parse
                return json.loads(self._extract_json(response))

            extracted = self._extract_json(response)
            result, error_msg = self._validate_with_model(response_model, extracted)

            if result is not None:
                return result

            last_error = error_msg
            if attempt < max_format_retries:
                tag = f" [{stage}]" if stage else ""
                logger.warning(
                    "Format validation failed%s (attempt %d/%d), retrying...\n%s",
                    tag, attempt + 1, max_format_retries, error_msg[:300],
                )
                current_prompt = (
                    f"{prompt}\n\n"
                    f"[你的上一次输出格式不符合要求，请严格按照JSON格式修正后重新输出。\n"
                    f"具体错误：\n{error_msg}\n\n"
                    f"请返回完整且符合格式的JSON，不要包含其他文字。]"
                )

        raise ValueError(
            f"Stage '{stage}': format validation failed after "
            f"{max_format_retries} retries.\n{last_error}"
        )

    async def _call_ai_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_model: type[BaseModel] | None = None,
        stage: str = "",
        max_format_retries: int = 5,
    ) -> dict:
        sp = system_prompt if system_prompt is not None else SYSTEM_PROMPT
        current_prompt = prompt

        for attempt in range(max_format_retries + 1):
            if len(current_prompt) > 12000:
                current_prompt = current_prompt[:12000] + "\n\n[... 文本过长，已截断 ...]"

            messages = [
                {"role": "system", "content": sp},
                {"role": "user", "content": current_prompt},
            ]
            response = await self.ai_client.chat_async(messages)

            if response_model is None:
                return json.loads(self._extract_json(response))

            extracted = self._extract_json(response)
            result, error_msg = self._validate_with_model(response_model, extracted)

            if result is not None:
                return result

            last_error = error_msg
            if attempt < max_format_retries:
                tag = f" [{stage}]" if stage else ""
                logger.warning(
                    "Format validation failed%s (attempt %d/%d), retrying...\n%s",
                    tag, attempt + 1, max_format_retries, error_msg[:300],
                )
                current_prompt = (
                    f"{prompt}\n\n"
                    f"[你的上一次输出格式不符合要求，请严格按照JSON格式修正后重新输出。\n"
                    f"具体错误：\n{error_msg}\n\n"
                    f"请返回完整且符合格式的JSON，不要包含其他文字。]"
                )

        raise ValueError(
            f"Stage '{stage}': format validation failed after "
            f"{max_format_retries} retries.\n{last_error}"
        )

    # ---- Multi-angle analysis ---------------------------------------------

    @staticmethod
    def _summarize_angle(name: str, result: dict | None) -> str:
        """One-line summary of an angle's key findings for terminal display."""
        if result is None:
            return ""
        try:
            if name == "metadata":
                title = result.get("title", "?")
                n_auth = len(result.get("authors", []))
                n_kw = len(result.get("keywords", []))
                return f"标题: {title[:35]}, {n_auth}位作者, {n_kw}个关键词"
            elif name == "core_contribution":
                n_contrib = len(result.get("contributions", []))
                novelty = result.get("novelty", "")
                return f"{n_contrib}条贡献, 创新: {novelty[:40]}"
            elif name == "method_analysis":
                n_tech = len(result.get("key_techniques", []))
                n_ent = len(result.get("entities", []))
                return f"{n_tech}个技术点, {n_ent}个实体"
            elif name == "experiment_analysis":
                datasets = result.get("datasets", "")
                n_results = len(result.get("main_results", []))
                return f"数据: {datasets[:35]}, {n_results}条结果"
            elif name == "critical_review":
                n_strengths = len(result.get("strengths", []))
                n_limits = len(result.get("limitations", []))
                return f"{n_strengths}个优势, {n_limits}个局限"
        except Exception:
            pass
        return ""

    async def _run_angle_async(self, angle_def: dict, raw_text: str) -> tuple[dict, dict | None]:
        """Run one analysis angle via async. Returns (angle_def, result_or_None)."""
        try:
            result = await self._call_ai_async(
                raw_text,
                system_prompt=angle_def["system_prompt"],
                response_model=angle_def.get("response_model"),
                stage=angle_def["label"],
            )
            return angle_def, result
        except Exception:
            logger.exception("Angle '%s' failed.", angle_def["label"])
            return angle_def, None

    async def _run_parallel_analyses_async(self, raw_text: str) -> dict[str, dict | None]:
        """Run all analysis angles in parallel via asyncio with structured terminal output."""
        results: dict[str, dict | None] = {}
        label_width = max(len(a["label"]) for a in ANGLES)

        print(f"\n{'─'*72}")
        print(f"  PaperWiki 多角度分析 — 调度 {len(ANGLES)} 个分析视角")
        print(f"{'─'*72}")
        for a in ANGLES:
            print(f"  [dispatch]  {a['label']:<{label_width}}  {a['name']}")
        print(f"{'─'*72}")

        t0 = time.monotonic()

        tasks = [asyncio.create_task(self._run_angle_async(a, raw_text)) for a in ANGLES]

        for completed in asyncio.as_completed(tasks):
            angle_def, result = await completed
            results[angle_def["name"]] = result

            elapsed = time.monotonic() - t0
            ok = result is not None
            mark = "✓" if ok else "✗"
            summary = self._summarize_angle(angle_def["name"], result)
            print(f"  [{mark}]  {angle_def['label']:<{label_width}}  {elapsed:>5.1f}s  {summary}")

        total = time.monotonic() - t0
        success = sum(1 for v in results.values() if v is not None)
        all_ok = success == len(ANGLES)
        print(f"  [{'✓' if all_ok else '⚠'}]  结果: {success}/{len(ANGLES)} 个视角成功 "
              f"(总耗时 {total:.1f}s)")
        print(f"{'─'*72}")

        return results

    def _synthesize(self, angle_results: dict[str, dict | None], raw_text: str) -> dict:
        """Combine all angle results into a final unified JSON via a synthesizer call."""
        summary = {}
        for name, result in angle_results.items():
            if result is not None:
                summary[name] = result
            else:
                summary[name] = {"error": "此角度分析失败"}

        synthesis_input = json.dumps(summary, ensure_ascii=False, indent=2)
        prompt = (
            f"以下是从不同角度对一篇学术论文的分析结果。请综合这些信息，生成一份完整的论文阅读报告。\n\n"
            f"=== 论文原文前2000字（供参考） ===\n{raw_text[:2000]}\n\n"
            f"=== 多角度分析结果 ===\n{synthesis_input}"
        )
        return self._call_ai(
            prompt,
            system_prompt=SYNTHESIZER_PROMPT,
            response_model=ReportOutput,
            stage="synthesizer",
        )

    # ---- Report generation -------------------------------------------------

    def _resolve_title(self, title: str, source_file: str) -> str:
        _GENERIC_TITLES = frozenset({"untitled", "title", "untitled document", "无标题", ""})
        if title.lower() in _GENERIC_TITLES:
            stem = os.path.splitext(os.path.basename(source_file))[0]
            return stem if stem.lower() not in _GENERIC_TITLES else f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return title

    def _render_report(self, ai_result: dict, source_file: str) -> dict:
        """Shared post-processing: filter entities, add author entities, render markdown."""
        title = self._resolve_title(ai_result.get("title", "").strip(), source_file)
        abstract = ai_result.get("abstract", "")
        keywords = ai_result.get("keywords", [])
        tldr = ai_result.get("tldr", "")
        background = ai_result.get("background", "")
        method = ai_result.get("method", "")
        key_findings = ai_result.get("key_findings", [])

        ai_authors = ai_result.get("authors", [])
        authors = _split_authors(ai_authors)

        ai_entities = ai_result.get("entities", [])
        entities = _filter_entities(ai_entities)

        for name in authors:
            entities.insert(0, {"name": name, "type": "人物", "brief": "论文作者"})
        entities = _dedupe_entities(entities)

        refs = ai_result.get("references", [])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        markdown = self.template.render(
            tldr=tldr,
            background=background,
            method=method,
            key_findings=key_findings,
            abstract=abstract,
            authors=authors,
            keywords=keywords,
            entities=entities,
            references=refs,
            generated_at=now,
            source_file=source_file,
        )
        return {
            "markdown": markdown,
            "title": title,
            "authors": authors,
            "keywords": keywords,
            "abstract": abstract,
            "tldr": tldr,
            "background": background,
            "method": method,
            "key_findings": key_findings,
            "entities": entities,
            "references": refs,
        }

    def generate_report(self, raw_text: str, source_file: str = "", multi_angle: bool = False) -> dict:
        """Generate a learning report from raw PDF text.

        Args:
            raw_text: Extracted PDF text.
            source_file: Path to the source PDF.
            multi_angle: If True, use parallel multi-angle analysis + synthesis.

        Returns a dict with keys:
            markdown, title, authors, keywords, abstract
        """
        if multi_angle:
            return self._generate_multi_angle(raw_text, source_file)
        else:
            return self._generate_single(raw_text, source_file)

    def _generate_single(self, raw_text: str, source_file: str) -> dict:
        """Original single-call pipeline (backward compatible)."""
        ai_result = self._call_ai(raw_text, response_model=ReportOutput, stage="single")
        return self._render_report(ai_result, source_file)

    def _generate_multi_angle(self, raw_text: str, source_file: str) -> dict:
        """Multi-angle parallel analysis pipeline via asyncio coroutines."""

        async def _run():
            try:
                return await self._run_parallel_analyses_async(raw_text)
            finally:
                await self.ai_client.aclose()

        angle_results = asyncio.run(_run())

        success_count = sum(1 for v in angle_results.values() if v is not None)
        print(f"  [synthesizing] 综合 {success_count}/{len(ANGLES)} 个视角结果 → 生成报告...")
        t0 = time.monotonic()
        ai_result = self._synthesize(angle_results, raw_text)
        elapsed = time.monotonic() - t0
        print(f"  [✓]  报告生成完成 ({elapsed:.1f}s)")
        print(f"{'─'*72}\n")

        return self._render_report(ai_result, source_file)
