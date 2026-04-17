"""变量提取器

从Worker标注中提取变量信息。
扫描INPUTS、OUTPUTS和RESULT部分识别变量。
"""

import re
import logging
from typing import List, Optional

from ..models import Annotation, TextSegment, VariableInfo, SPLBlockType

logger = logging.getLogger(__name__)


class VariableExtractor:
    """变量提取器

    从Worker标注的extracted_content中提取变量定义和引用。
    """

    def __init__(self, llm_client=None, config: Optional[dict] = None):
        """初始化提取器

        Args:
            llm_client: LLM客户端（可选，用于复杂提取）
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}

    async def extract(self, annotation: Annotation) -> List[VariableInfo]:
        """从Worker标注中提取变量

        Args:
            annotation: Worker标注结果

        Returns:
            变量信息列表
        """
        if annotation.block_type != SPLBlockType.WORKER_MAIN_FLOW:
            logger.warning(f"Expected WORKER annotation, got {annotation.block_type}")
            return []

        content = annotation.extracted_content
        if not content:
            logger.warning("Empty annotation content")
            return []

        variables = []

        # 1. 从INPUTS提取变量
        input_vars = self._extract_from_section(content, "INPUTS", "CONTROLLED_INPUTS")
        for var in input_vars:
            var.source = "INPUTS"
        variables.extend(input_vars)

        # 2. 从OUTPUTS提取变量
        output_vars = self._extract_from_section(content, "OUTPUTS", "CONTROLLED_OUTPUTS")
        for var in output_vars:
            var.source = "OUTPUTS"
        variables.extend(output_vars)

        # 3. 从RESULT提取变量声明
        result_vars = self._extract_from_results(content)
        variables.extend(result_vars)

        # 4. 从GENERAL_COMMAND提取变量引用
        ref_vars = self._extract_references(content)
        # 过滤掉已在INPUTS/OUTPUTS/RESULT中的变量
        existing_names = {v.name for v in variables}
        for var in ref_vars:
            if var.name not in existing_names:
                variables.append(var)

        # 5. 使用LLM辅助提取（如果配置了）
        if self.llm_client:
            llm_vars = await self._extract_with_llm(content)
            # 合并LLM提取结果
            for var in llm_vars:
                if var.name not in existing_names:
                    variables.append(var)
                    existing_names.add(var.name)

        logger.info(f"Extracted {len(variables)} variables from Worker annotation")
        return variables

    def _extract_from_section(self, content: str, *section_names) -> List[VariableInfo]:
        """从指定section提取变量引用

        Args:
            content: Worker内容
            section_names: section名称列表（如"INPUTS", "CONTROLLED_INPUTS"）

        Returns:
            变量信息列表
        """
        variables = []

        for section_name in section_names:
            # 匹配 [SECTION_NAME] ... [/SECTION_NAME] 或 [END_SECTION_NAME]
            pattern = rf'\[{section_name}\](.*?)\[(?:END_{section_name}|/{section_name})\]'
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

            for match in matches:
                section_content = match.strip()
                # 提取 <REF>var</REF> 引用
                ref_pattern = r'<REF>\*?(\w+)</REF>'
                refs = re.findall(ref_pattern, section_content)

                for ref in refs:
                    variables.append(VariableInfo(
                        name=ref,
                        context=f"Referenced in {section_name}",
                        source=section_name,
                        confidence=0.9
                    ))

        return variables

    def _extract_from_results(self, content: str) -> List[VariableInfo]:
        """从RESULT部分提取变量声明

        Args:
            content: Worker内容

        Returns:
            变量信息列表
        """
        variables = []

        # 匹配 RESULT var: type 或 RESULT var:type
        # 支持: RESULT var:number, RESULT var:List [text], RESULT var:MyType
        # pattern: RESULT\s+(\w+)\s*:\s*([\w\[\]{}\s,]+)
        result_pattern = r'RESULT\s+(\w+)\s*:\s*([\w\[\]\{\}\s,]+)'
        matches = re.findall(result_pattern, content, re.IGNORECASE)

        for var_name, var_type in matches:
            # 清理类型名（去除多余空格）
            clean_type = var_type.strip()
            variables.append(VariableInfo(
                name=var_name,
                context=f"Declared in RESULT with type {clean_type}",
                source="RESULT",
                confidence=0.95
            ))

        return variables

    def _extract_references(self, content: str) -> List[VariableInfo]:
        """从整个内容中提取变量引用

        Args:
            content: Worker内容

        Returns:
            变量信息列表
        """
        variables = []

        # 提取所有 <REF>var</REF>
        ref_pattern = r'<REF>\*?(\w+)</REF>'
        refs = re.findall(ref_pattern, content)

        seen = set()
        for ref in refs:
            if ref not in seen:
                seen.add(ref)
                variables.append(VariableInfo(
                    name=ref,
                    context="Referenced in Worker flow",
                    source="REFERENCE",
                    confidence=0.8
                ))

        return variables

    async def _extract_with_llm(self, content: str) -> List[VariableInfo]:
        """使用LLM辅助提取变量

        Args:
            content: Worker内容

        Returns:
            变量信息列表
        """
        if not self.llm_client:
            return []

        system_prompt = '''You are an expert in SPL (Structured Prompt Language) variable extraction.

## Task
Analyze the provided SPL Worker content and extract all variable names that are:
1. Referenced in INPUTS/OUTPUTS sections
2. Declared in RESULT statements
3. Referenced via <REF> tags throughout the flow

## Output Format
Return a JSON array of variable objects:
```json
{
    "variables": [
        {
            "name": "variable_name",
            "context": "description of how this variable is used",
            "source": "INPUTS|OUTPUTS|RESULT|REFERENCE"
        }
    ]
}
```

## Rules
- Include all variables mentioned in the content
- Provide context for each variable
- Use appropriate source category
'''

        user_prompt = f"""Extract all variables from the following SPL Worker content:

{content}

Return only the JSON array of variables."""

        try:
            response = await self.llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json"
            )

            if isinstance(response, dict) and "variables" in response:
                variables = []
                for var_data in response["variables"]:
                    variables.append(VariableInfo(
                        name=var_data.get("name", ""),
                        context=var_data.get("context", ""),
                        source=var_data.get("source", "LLM"),
                        confidence=0.85
                    ))
                return variables

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")

        return []
