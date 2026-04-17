# -*- coding: utf-8 -*-
"""SPL块生成器

包含所有SPL块类型的生成器实现。
"""

from typing import List, Optional
import logging

from .base import BlockGenerator
from .prompt_builder import get_block_prompt
from ..models import SPLBlockType, TypedVariable, SymbolTable, ComplexTypeDef, ComplexTypeCategory

logger = logging.getLogger(__name__)


class TypesGenerator:
    """TYPES块生成器

    根据复杂类型定义生成SPL TYPES块。
    必须在Phase 4其他块生成之前执行。
    
    注意：此类不继承BlockGenerator，因为它接收ComplexTypeDef列表而非Annotation。
    """

    def __init__(self, llm_client, config: Optional[dict] = None):
        """初始化生成器

        Args:
            llm_client: LLM客户端
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}

    async def generate(self, complex_types: List[ComplexTypeDef]) -> str:
        """生成TYPES块

        Args:
            complex_types: 复杂类型定义列表

        Returns:
            SPL TYPES块代码
        """
        if not complex_types:
            logger.info("No complex types to generate, returning empty TYPES block")
            return ""

        logger.info(f"Generating TYPES block for {len(complex_types)} complex types")

        # 加载提示词
        system_prompt = self._get_system_prompt()

        # 构建用户提示词
        user_prompt = self._build_user_prompt(complex_types)

        # 调用LLM
        response = await self.llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # 提取代码
        code = self._extract_code(response)

        # 后处理
        code = self._post_process(code)

        logger.info(f"Generated TYPES block: {len(code)} chars")

        return code

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return get_block_prompt(SPLBlockType.TYPES)

    def _build_user_prompt(self, complex_types: List[ComplexTypeDef]) -> str:
        """构建用户提示词"""
        types_info = []

        for ct in complex_types:
            type_desc = f"""类型名称: {ct.name}
类型类别: {ct.category.value}
定义: {ct.definition}
描述: {ct.description}
被引用变量: {', '.join(ct.referenced_by)}
"""
            types_info.append(type_desc)

        return f"""请根据以下复杂类型定义生成SPL TYPES块代码：

[类型定义列表]
{'---'.join(types_info)}
[/类型定义列表]

要求：
1. 生成标准的SPL TYPES块
2. 每个类型前添加描述注释
3. 确保语法正确
4. 只输出生成的TYPES块代码，不要包含其他说明
"""

    def _extract_code(self, response) -> str:
        """从响应中提取代码"""
        import re

        # 处理不同格式的响应
        if isinstance(response, dict):
            content = response.get("content", "")
        elif isinstance(response, str):
            content = response
        else:
            content = str(response)

        # 尝试提取代码块
        code_pattern = r'```(?:spl)?\n?(.*?)```'
        match = re.search(code_pattern, content, re.DOTALL)

        if match:
            return match.group(1).strip()

        # 如果没有代码块，返回整个内容
        return content.strip()

    def _post_process(self, code: str) -> str:
        """后处理代码"""
        # 去除多余空行
        lines = [line for line in code.split('\n') if line.strip()]
        return '\n'.join(lines)


class PersonaGenerator(BlockGenerator):
    """PERSONA块生成器"""

    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.PERSONA

    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.PERSONA)


class AudienceGenerator(BlockGenerator):
    """AUDIENCE块生成器"""

    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.AUDIENCE

    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.AUDIENCE)


class ConceptsGenerator(BlockGenerator):
    """CONCEPTS块生成器"""

    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.CONCEPTS

    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.CONCEPTS)


class ConstraintsGenerator(BlockGenerator):
    """CONSTRAINTS块生成器"""

    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.CONSTRAINTS

    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.CONSTRAINTS)


class VariablesGenerator(BlockGenerator):
    """VARIABLES块生成器

    支持从推断的类型生成VARIABLES块。
    可以引用TYPES中定义的复杂类型。
    """

    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.VARIABLES

    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.VARIABLES)

    async def generate_with_types(self, typed_vars: List[TypedVariable],
                                 types_block: str = "") -> str:
        """使用推断的类型生成VARIABLES块

        Args:
            typed_vars: 带类型的变量列表
            types_block: TYPES块代码（用于上下文）

        Returns:
            SPL VARIABLES块代码
        """
        import logging
        logger = logging.getLogger(__name__)

        if not typed_vars:
            logger.info("No variables to generate, returning empty VARIABLES block")
            return ""

        logger.info(f"Generating VARIABLES block for {len(typed_vars)} variables")

        # 加载提示词
        system_prompt = self._get_system_prompt()

        # 构建用户提示词
        user_prompt = self._build_user_prompt_with_types(typed_vars, types_block)

        # 调用LLM
        response = await self.llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # 提取代码
        code = self._extract_code(response)

        # 后处理
        code = self._post_process(code)

        logger.info(f"Generated VARIABLES block: {len(code)} chars")

        return code

    def _build_user_prompt_with_types(self, typed_vars: List[TypedVariable],
                                     types_block: str) -> str:
        """构建带类型的用户提示词"""

        vars_info = []
        for tv in typed_vars:
            type_ref = tv.type_name
            if tv.needs_type_definition and types_block:
                # 确保引用的是TYPES中定义的类型
                type_ref = f"{tv.type_name} (defined in TYPES)"

            var_info = f"""变量名: {tv.name}
类型: {type_ref}
描述: {tv.original_info.context}
"""
            vars_info.append(var_info)

        types_info = f"\n[已定义的TYPES块]\n{types_block}\n[/已定义的TYPES块]\n" if types_block else ""

        return f"""请根据以下变量信息生成SPL VARIABLES块代码：

[变量列表]
{'---'.join(vars_info)}
[/变量列表]
{types_info}
要求：
1. 为简单基础类型（text/image/audio/number/boolean）直接使用类型名
2. 为复杂类型引用TYPES中定义的类型名
3. 为每个变量添加描述注释
4. 确保语法正确，标签闭合
5. 只输出生成的VARIABLES块代码
"""


class WorkerGenerator(BlockGenerator):
    """WORKER块生成器

    支持SymbolTable，处理变量引用和临时变量声明。
    """

    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.WORKER_MAIN_FLOW

    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.WORKER_MAIN_FLOW)

    async def generate_with_symbol_table(self, annotation,
                                        symbol_table: SymbolTable) -> str:
        """使用符号表生成WORKER块

        Args:
            annotation: Worker标注结果
            symbol_table: 符号表（包含变量和类型定义）

        Returns:
            SPL WORKER块代码
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Generating WORKER block with symbol table")

        # 加载提示词
        system_prompt = self._get_system_prompt()

        # 构建带符号表的用户提示词
        user_prompt = self._build_user_prompt_with_symbol_table(annotation, symbol_table)

        # 调用LLM
        response = await self.llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # 提取代码
        code = self._extract_code(response)

        # 后处理
        code = self._post_process(code)

        # 更新符号表：提取临时变量
        self._update_symbol_table_from_code(code, symbol_table)

        logger.info(f"Generated WORKER block: {len(code)} chars")

        return code

    def _build_user_prompt_with_symbol_table(self, annotation,
                                             symbol_table: SymbolTable) -> str:
        """构建带符号表的用户提示词"""

        # 构建可用变量列表
        available_vars = []
        for name, tv in symbol_table.global_vars.items():
            available_vars.append(f"  - {name}: {tv.type_name}")

        for name, type_name in symbol_table.temp_vars.items():
            available_vars.append(f"  - {name}: {type_name} (temporary)")

        vars_section = "\n".join(available_vars) if available_vars else "  (none)"

        # 构建可用类型列表
        available_types = []
        for type_name, type_def in symbol_table.type_defs.items():
            available_types.append(f"  - {type_name}: {type_def.definition}")

        types_section = "\n".join(available_types) if available_types else "  (none)"

        return f"""请根据以下内容生成SPL WORKER块代码：

[内容开始]
{annotation.extracted_content}
[内容结束]

[可用变量]
{vars_section}
[/可用变量]

[可用类型]
{types_section}
[/可用类型]

生成规则：
1. INPUTS/OUTPUTS中引用变量使用: <REF>var_name</REF>
2. GENERAL_COMMAND中可引用变量: <REF>var_name</REF>
3. RESULT中声明临时变量: var_name: TypeName
4. 确保引用的变量在[可用变量]中已定义
5. 声明临时变量时确保类型有效
6. 只输出生成的WORKER块代码
"""

    def _update_symbol_table_from_code(self, code: str, symbol_table: SymbolTable):
        """从生成的代码中提取临时变量并更新符号表"""
        import re

        # 匹配 RESULT var: type 模式
        result_pattern = r'RESULT\s+(\w+)\s*:\s*(\w+)'
        matches = re.findall(result_pattern, code, re.IGNORECASE)

        for var_name, type_name in matches:
            if not symbol_table.is_defined(var_name):
                symbol_table.add_temp_var(var_name, type_name)
