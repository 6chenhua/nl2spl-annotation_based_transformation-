"""类型推断器

基于变量名和上下文推断变量类型。
支持5大类型类别：简单基础类型、枚举、数组、结构化、声明命名类型。
"""

import re
import logging
from typing import List, Optional

from ..models import VariableInfo, TypedVariable, SimpleType, ComplexTypeCategory

logger = logging.getLogger(__name__)


class TypeInferencer:
    """类型推断器

    基于启发式规则和LLM辅助推断变量类型。
    """

    # 类型关键词映射
    TYPE_KEYWORDS = {
        SimpleType.TEXT: ['text', 'string', 'str', 'content', 'message', 'description', 'name', 'title'],
        SimpleType.NUMBER: ['number', 'count', 'score', 'value', 'amount', 'price', 'quantity', 'int', 'float'],
        SimpleType.BOOLEAN: ['boolean', 'bool', 'flag', 'is_', 'has_', 'can_', 'should_', 'enable'],
        SimpleType.IMAGE: ['image', 'img', 'picture', 'photo', 'graphic', 'visual'],
        SimpleType.AUDIO: ['audio', 'sound', 'voice', 'recording', 'music'],
    }

    # 数组指示词
    ARRAY_INDICATORS = ['list', 'array', 'items', 'elements', 'collection', 'multiple', 'many', 'batch']

    # 结构化类型指示
    STRUCTURED_INDICATORS = ['result', 'object', 'struct', 'record', 'data', 'info', 'details']

    # 枚举指示
    ENUM_INDICATORS = ['status', 'state', 'type', 'category', 'mode', 'option', 'choice']

    def __init__(self, llm_client=None, config: Optional[dict] = None):
        """初始化推断器

        Args:
            llm_client: LLM客户端（可选，用于复杂推断）
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)

    async def infer(self, variables: List[VariableInfo]) -> List[TypedVariable]:
        """推断变量类型

        Args:
            variables: 变量信息列表

        Returns:
            带类型的变量列表
        """
        typed_variables = []

        for var in variables:
            typed_var = self._infer_single(var)
            typed_variables.append(typed_var)

        # 使用LLM辅助处理低置信度推断
        if self.llm_client:
            low_confidence_vars = [v for v in typed_variables if v.confidence < self.confidence_threshold]
            if low_confidence_vars:
                await self._refine_with_llm(low_confidence_vars)

        logger.info(f"Inferred types for {len(typed_variables)} variables")
        return typed_variables

    def _infer_single(self, var: VariableInfo) -> TypedVariable:
        """推断单个变量类型

        Args:
            var: 变量信息

        Returns:
            带类型的变量
        """
        name_lower = var.name.lower()
        context_lower = var.context.lower()

        # 1. 检查是否为数组类型
        is_array, element_type = self._infer_array_type(name_lower, context_lower)
        if is_array:
            # SPL语法: List [element_type] (注意空格)
            # 对于简单类型元素，需要类型定义
            needs_def = True  # 数组类型总是需要在TYPES中定义
            return TypedVariable(
                name=var.name,
                type_name=f"List [{element_type}]",
                is_simple_type=False,
                needs_type_definition=needs_def,
                original_info=var,
                confidence=0.85
            )

        # 2. 检查是否为枚举类型
        is_enum, enum_values = self._infer_enum_type(name_lower, context_lower)
        if is_enum:
            return TypedVariable(
                name=var.name,
                type_name=f"Enum_{var.name}",
                is_simple_type=False,
                needs_type_definition=True,
                original_info=var,
                confidence=0.75
            )

        # 3. 检查是否为结构化类型
        is_structured = self._infer_structured_type(name_lower, context_lower)
        if is_structured:
            return TypedVariable(
                name=var.name,
                type_name=f"Struct_{var.name}",
                is_simple_type=False,
                needs_type_definition=True,
                original_info=var,
                confidence=0.70
            )

        # 4. 推断简单基础类型
        simple_type = self._infer_simple_type(name_lower, context_lower)
        if simple_type:
            return TypedVariable(
                name=var.name,
                type_name=simple_type.value,
                is_simple_type=True,
                needs_type_definition=False,
                original_info=var,
                confidence=0.80
            )

        # 5. 默认类型
        return TypedVariable(
            name=var.name,
            type_name="text",
            is_simple_type=True,
            needs_type_definition=False,
            original_info=var,
            confidence=0.60
        )

    def _infer_simple_type(self, name: str, context: str) -> Optional[SimpleType]:
        """推断简单基础类型

        Args:
            name: 变量名（小写）
            context: 上下文（小写）

        Returns:
            简单类型或None
        """
        combined = f"{name} {context}"

        scores = {}
        for simple_type, keywords in self.TYPE_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in combined:
                    score += 1
            scores[simple_type] = score

        # 返回得分最高的类型
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])[0]
            if scores[best_type] > 0:
                return best_type

        return None

    def _infer_array_type(self, name: str, context: str) -> tuple[bool, str]:
        """推断是否为数组类型

        Args:
            name: 变量名（小写）
            context: 上下文（小写）

        Returns:
            (是否为数组, 元素类型)
        """
        # 1. 检查数组指示词 - 只在变量名中检查，避免上下文中的描述词误触发
        is_array = any(indicator in name for indicator in self.ARRAY_INDICATORS)

        if is_array:
            # 推断元素类型
            element_type = self._infer_element_type(name, context)
            return True, element_type

        # 2. 检查明确的数组描述模式（短语匹配）
        array_patterns = ['list of', 'array of', 'collection of', 'set of', 'items of']
        if any(pattern in context for pattern in array_patterns):
            element_type = self._infer_element_type(name, context)
            return True, element_type

        # 3. 检查复数形式（简单启发式）
        if name.endswith('s') and len(name) > 1:
            # 可能是复数，尝试推断单数形式
            singular = name[:-1]
            element_type = self._infer_simple_type(singular, context)
            if element_type:
                return True, element_type.value

            # 默认text
            return True, "text"

        return False, ""

    def _infer_element_type(self, name: str, context: str) -> str:
        """推断数组元素类型

        Args:
            name: 变量名（小写）
            context: 上下文（小写）

        Returns:
            元素类型名
        """
        # 尝试从名称中提取元素类型
        # 如 "text_list" -> "text"
        for simple_type in SimpleType:
            if simple_type.value in name:
                return simple_type.value

        # 默认text
        return "text"

    def _infer_enum_type(self, name: str, context: str) -> tuple[bool, List[str]]:
        """推断是否为枚举类型

        Args:
            name: 变量名（小写）
            context: 上下文（小写）

        Returns:
            (是否为枚举, 枚举值列表)
        """
        # 检查枚举指示词
        is_enum_candidate = any(indicator in name
                               for indicator in self.ENUM_INDICATORS)

        if is_enum_candidate:
            # 尝试从上下文提取枚举值
            enum_values = self._extract_enum_values(context)
            if enum_values:
                return True, enum_values

        return False, []

    def _extract_enum_values(self, context: str) -> List[str]:
        """从上下文提取枚举值

        Args:
            context: 上下文文本

        Returns:
            枚举值列表
        """
        # 查找 [value1, value2] 格式
        enum_pattern = r'\[(\w+(?:\s*,\s*\w+)*)\]'
        match = re.search(enum_pattern, context)
        if match:
            values = [v.strip() for v in match.group(1).split(',')]
            return values

        # 查找如 "can be A, B, or C" 格式
        or_pattern = r'(?:can be|options?|values?):?\s*(.+?)(?:\.|$)'
        match = re.search(or_pattern, context, re.IGNORECASE)
        if match:
            values_text = match.group(1)
            # 分割逗号或"or"
            values = re.split(r',|\s+or\s+', values_text)
            return [v.strip() for v in values if v.strip()]

        return []

    def _infer_structured_type(self, name: str, context: str) -> bool:
        """推断是否为结构化类型

        Args:
            name: 变量名（小写）
            context: 上下文（小写）

        Returns:
            是否为结构化类型
        """
        # 检查结构化指示词
        return any(indicator in name or indicator in context
                  for indicator in self.STRUCTURED_INDICATORS)

    def _is_simple_type(self, type_name: str) -> bool:
        """检查是否为简单类型

        Args:
            type_name: 类型名称

        Returns:
            是否为简单类型
        """
        simple_types = [t.value for t in SimpleType]
        return type_name in simple_types

    async def _refine_with_llm(self, typed_vars: List[TypedVariable]):
        """使用LLM细化低置信度推断

        Args:
            typed_vars: 低置信度变量列表
        """
        if not self.llm_client:
            return

        system_prompt = '''You are an expert in data type inference.

## Task
Review the following variable definitions and improve their type inference.
Consider:
1. Variable naming conventions
2. Context description
3. Common patterns in data types

## Output Format
Return a JSON object with refined type information:
```json
{
    "refined_types": [
        {
            "name": "variable_name",
            "type_name": "refined_type",
            "is_simple_type": true/false,
            "needs_type_definition": true/false,
            "confidence": 0.9
        }
    ]
}
```

## Type Guidelines
- Simple types: text, number, boolean, image, audio
- Complex types: structured {field: type}, enum [value1, value2], arrays List[type]
'''

        # 构建变量描述
        vars_desc = []
        for tv in typed_vars:
            desc = f"Name: {tv.name}, Context: {tv.original_info.context}, Current Type: {tv.type_name}"
            vars_desc.append(desc)

        user_prompt = f"""Please refine the type inference for these variables:

{'\n'.join(vars_desc)}

Return the refined types in JSON format."""

        try:
            response = await self.llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json"
            )

            if isinstance(response, dict) and "refined_types" in response:
                refined_map = {rt["name"]: rt for rt in response["refined_types"]}

                for tv in typed_vars:
                    if tv.name in refined_map:
                        rt = refined_map[tv.name]
                        tv.type_name = rt.get("type_name", tv.type_name)
                        tv.is_simple_type = rt.get("is_simple_type", tv.is_simple_type)
                        tv.needs_type_definition = rt.get("needs_type_definition", tv.needs_type_definition)
                        tv.confidence = rt.get("confidence", 0.8)

        except Exception as e:
            logger.warning(f"LLM refinement failed: {e}")
