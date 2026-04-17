"""类型收集器

收集需要在TYPES块中定义的复杂类型。
去重、命名和建立变量到类型的映射。
"""

import hashlib
import logging
from typing import List, Dict, Set, Tuple
from dataclasses import field

from ..models import TypedVariable, ComplexTypeDef, ComplexTypeCategory, SimpleType

logger = logging.getLogger(__name__)


class TypeCollector:
    """类型收集器

    从TypedVariable列表中提取需要定义的复杂类型。
    处理结构化类型、枚举类型和自定义类型。
    """

    def __init__(self, config: dict = None):
        """初始化收集器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.type_counter = 0

    def collect(self, typed_variables: List[TypedVariable]) -> List[ComplexTypeDef]:
        """收集复杂类型定义

        Args:
            typed_variables: 带类型的变量列表

        Returns:
            复杂类型定义列表
        """
        complex_types = []
        seen_definitions: Dict[str, str] = {}  # definition_hash -> type_name

        for tv in typed_variables:
            if not tv.needs_type_definition:
                continue

            # 生成类型定义
            type_def = self._create_type_definition(tv)

            if type_def is None:
                # 对于数组类型，如果元素是简单类型，不需要定义类型
                # 更新变量标记，避免验证错误
                if tv.type_name.startswith("List"):
                    tv.needs_type_definition = False
                continue

            if type_def:
                # 检查是否已存在相同定义
                def_hash = self._hash_definition(type_def.definition)

                if def_hash in seen_definitions:
                    # 复用已有类型名
                    existing_name = seen_definitions[def_hash]
                    tv.type_name = existing_name
                    # 更新引用
                    for ct in complex_types:
                        if ct.name == existing_name:
                            ct.referenced_by.append(tv.name)
                else:
                    # 新类型
                    seen_definitions[def_hash] = type_def.name
                    complex_types.append(type_def)

        logger.info(f"Collected {len(complex_types)} unique complex types")
        return complex_types

    def _create_type_definition(self, tv: TypedVariable) -> ComplexTypeDef:
        """为变量创建类型定义

        Args:
            tv: 带类型的变量

        Returns:
            复杂类型定义或None
        """
        # 根据类型推断类别创建定义
        if "Enum_" in tv.type_name:
            return self._create_enum_type(tv)
        elif "Struct_" in tv.type_name:
            return self._create_structured_type(tv)
        elif "List[" in tv.type_name or "List [" in tv.type_name:
            # 数组类型，检查元素类型是否需要定义
            return self._create_array_element_type(tv)
        else:
            # 自定义类型
            return self._create_custom_type(tv)

    def _create_enum_type(self, tv: TypedVariable) -> ComplexTypeDef:
        """创建枚举类型定义

        Args:
            tv: 带类型的变量

        Returns:
            枚举类型定义
        """
        # 从上下文提取可能的枚举值
        enum_values = self._extract_enum_values(tv)

        if not enum_values:
            # 默认枚举值
            enum_values = ["option1", "option2", "option3"]

        # 生成类型名
        type_name = self._generate_type_name(tv.name, "Enum")

        # 生成定义
        values_str = ", ".join(enum_values)
        definition = f"[{values_str}]"

        return ComplexTypeDef(
            name=type_name,
            category=ComplexTypeCategory.ENUM,
            definition=definition,
            description=f"{tv.name} enumeration type",
            referenced_by=[tv.name]
        )

    def _create_structured_type(self, tv: TypedVariable) -> ComplexTypeDef:
        """创建结构化类型定义

        Args:
            tv: 带类型的变量

        Returns:
            结构化类型定义
        """
        # 生成类型名
        type_name = self._generate_type_name(tv.name, "Struct")

        # 从上下文推断字段
        fields = self._infer_struct_fields(tv)

        # 生成定义
        field_strs = [f'"{desc}" {fname}: {ftype}' for fname, ftype, desc in fields]
        definition = "{\n    " + ",\n    ".join(field_strs) + "\n}"

        return ComplexTypeDef(
            name=type_name,
            category=ComplexTypeCategory.STRUCTURED,
            definition=definition,
            description=f"{tv.name} structure type",
            referenced_by=[tv.name]
        )

    def _create_array_element_type(self, tv: TypedVariable) -> ComplexTypeDef:
        """为数组元素创建类型定义

        Args:
            tv: 带类型的变量

        Returns:
            元素类型定义或None
        """
        # 提取元素类型
        match = self._extract_array_element_type(tv.type_name)
        if not match:
            return None

        element_type = match

        # 如果元素类型是简单类型，不需要定义
        if element_type in [t.value for t in SimpleType]:
            return None

        # 如果元素类型已经是自定义类型名
        type_name = self._generate_type_name(element_type, "Item")

        # 推断元素结构
        fields = self._infer_element_fields(tv)
        field_strs = [f'"{desc}" {fname}: {ftype}' for fname, ftype, desc in fields]
        definition = "{\n    " + ",\n    ".join(field_strs) + "\n}"

        return ComplexTypeDef(
            name=type_name,
            category=ComplexTypeCategory.STRUCTURED,
            definition=definition,
            description=f"{tv.name} array element type",
            referenced_by=[tv.name]
        )

    def _create_custom_type(self, tv: TypedVariable) -> ComplexTypeDef:
        """创建自定义类型定义

        Args:
            tv: 带类型的变量

        Returns:
            自定义类型定义
        """
        # 生成新的类型名（基于变量名）
        type_name = self._generate_type_name(tv.name, "")

        # 关键：更新 TypedVariable 的类型名，使其引用新创建的类型
        tv.type_name = type_name

        # 推断结构
        fields = self._infer_struct_fields(tv)
        field_strs = [f'"{desc}" {fname}: {ftype}' for fname, ftype, desc in fields]
        definition = "{\n    " + ",\n    ".join(field_strs) + "\n}"

        return ComplexTypeDef(
            name=type_name,
            category=ComplexTypeCategory.DECLARED,
            definition=definition,
            description=f"{tv.name} custom type",
            referenced_by=[tv.name]
        )

    def _extract_enum_values(self, tv: TypedVariable) -> List[str]:
        """从变量上下文提取枚举值

        Args:
            tv: 带类型的变量

        Returns:
            枚举值列表
        """
        import re

        context = tv.original_info.context

        # 查找 [value1, value2] 格式
        enum_pattern = r'\[(\w+(?:\s*,\s*\w+)*)\]'
        match = re.search(enum_pattern, context)
        if match:
            return [v.strip() for v in match.group(1).split(',')]

        # 查找如 "can be A, B, or C" 格式
        or_pattern = r'(?:can be|options?|values?):?\s*(.+?)(?:\.|$)'
        match = re.search(or_pattern, context, re.IGNORECASE)
        if match:
            values_text = match.group(1)
            values = re.split(r',|\s+or\s+', values_text)
            return [v.strip() for v in values if v.strip()]

        return []

    def _infer_struct_fields(self, tv: TypedVariable) -> List[Tuple[str, str, str]]:
        """推断结构化类型的字段

        Args:
            tv: 带类型的变量

        Returns:
            [(field_name, field_type, description), ...]
        """
        context = tv.original_info.context.lower()
        name = tv.name.lower()

        fields = []

        # 根据变量名和上下文推断字段
        if "result" in name or "output" in name:
            fields = [
                ("content", "text", "内容"),
                ("success", "boolean", "是否成功"),
            ]
        elif "user" in name or "person" in name:
            fields = [
                ("name", "text", "姓名"),
                ("id", "text", "标识"),
            ]
        elif "config" in name or "setting" in name:
            fields = [
                ("key", "text", "键"),
                ("value", "text", "值"),
            ]
        else:
            # 默认字段
            fields = [
                ("data", "text", "数据"),
                ("metadata", "text", "元数据"),
            ]

        return fields

    def _infer_element_fields(self, tv: TypedVariable) -> List[Tuple[str, str, str]]:
        """推断数组元素的字段

        Args:
            tv: 带类型的变量

        Returns:
            [(field_name, field_type, description), ...]
        """
        # 默认元素字段
        return [
            ("id", "text", "标识"),
            ("value", "text", "值"),
        ]

    def _generate_type_name(self, base_name: str, suffix: str = "") -> str:
        """生成唯一的类型名

        Args:
            base_name: 基础名称
            suffix: 后缀

        Returns:
            类型名（PascalCase）
        """
        # 清理基础名称
        clean_name = "".join(word.capitalize() for word in base_name.split("_"))

        if suffix:
            type_name = f"{clean_name}{suffix}"
        else:
            type_name = clean_name

        # 确保首字母大写
        type_name = type_name[0].upper() + type_name[1:] if type_name else "Type"

        self.type_counter += 1
        return type_name

    def _hash_definition(self, definition: str) -> str:
        """计算类型定义的hash

        Args:
            definition: 类型定义字符串

        Returns:
            hash字符串
        """
        return hashlib.md5(definition.encode()).hexdigest()[:12]

    def _extract_array_element_type(self, type_name: str) -> str:
        """从数组类型名中提取元素类型

        Args:
            type_name: 如 "List [text]"

        Returns:
            元素类型名或None
        """
        import re

        # 支持两种格式: "List[text]" 和 "List [text]"
        match = re.match(r'List\s*\[(\w+)\]', type_name)
        if match:
            return match.group(1)
        return None
