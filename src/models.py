"""核心数据模型"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Union
from enum import Enum


class SPLBlockType(Enum):
    """SPL块类型"""
    PERSONA = "persona"
    AUDIENCE = "audience"
    CONCEPTS = "concepts"
    CONSTRAINTS = "constraints"
    VARIABLES = "variables"
    TYPES = "types"
    WORKER_MAIN_FLOW = "worker_main_flow"
    WORKER_EXAMPLE = "worker_example"
    WORKER_FLOW_STEP = "worker_flow_step"


class SimpleType(Enum):
    """5大简单基础类型"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    NUMBER = "number"
    BOOLEAN = "boolean"


class ComplexTypeCategory(Enum):
    """复杂类型类别"""
    ENUM = "enum"
    ARRAY = "array"
    STRUCTURED = "structured"
    DECLARED = "declared"


@dataclass
class TextSegment:
    """文本片段"""
    content: str
    start_pos: int
    end_pos: int
    source: str = ""  # 来源标注器


@dataclass
class Annotation:
    """标注结果"""
    block_type: SPLBlockType
    segments: List[TextSegment]
    confidence: float
    extracted_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conflict:
    """冲突信息"""
    segments: List[TextSegment]  # 冲突的文本片段
    candidate_labels: List[SPLBlockType]  # 候选标签
    confidence_scores: Dict[SPLBlockType, float]
    resolution: Optional[SPLBlockType] = None  # 解决后的标签


@dataclass
class ClarificationQuestion:
    """澄清问题"""
    conflict: Conflict
    question_text: str  # 自然语言问题
    options: List[Dict[str, Any]]  # 选项（包含间接映射）
    context: str  # 原始上下文


@dataclass
class PipelineResult:
    """管道执行结果"""
    original_prompt: str
    annotations: Dict[SPLBlockType, Annotation]
    conflicts: List[Conflict]
    clarification_history: List[Dict[str, Any]]
    spl_code: str
    success: bool
    errors: List[str] = field(default_factory=list)


# ============ Phase 2: 变量提取与类型推断新增模型 ============

@dataclass
class VariableInfo:
    """从Worker标注提取的原始变量信息"""
    name: str
    context: str  # 来源上下文描述
    source: str  # "INPUTS"/"OUTPUTS"/"RESULT"/"EXPLICIT"
    confidence: float = 1.0


@dataclass
class TypedVariable:
    """带类型推断的变量"""
    name: str
    type_name: str  # 类型名称（text/image/number等，或自定义类型名）
    is_simple_type: bool  # 是否为简单基础类型
    needs_type_definition: bool  # 是否需在TYPES中定义
    original_info: VariableInfo
    confidence: float = 1.0


@dataclass
class ComplexTypeDef:
    """复杂类型定义"""
    name: str  # 类型名（如"AnalysisResult"）
    category: ComplexTypeCategory  # 类型类别
    definition: str  # SPL语法定义
    description: str = ""  # 类型描述
    referenced_by: List[str] = field(default_factory=list)  # 引用此类型的变量名列表


@dataclass
class SymbolTable:
    """符号表 - 贯穿Phase 3-5"""
    # 全局变量（来自VARIABLES）
    global_vars: Dict[str, TypedVariable] = field(default_factory=dict)
    # 类型定义（来自TYPES）
    type_defs: Dict[str, ComplexTypeDef] = field(default_factory=dict)
    # Worker临时变量（在Worker生成过程中动态添加）
    temp_vars: Dict[str, str] = field(default_factory=dict)  # name -> type_name

    def add_temp_var(self, name: str, type_name: str):
        """Worker生成时声明临时变量"""
        self.temp_vars[name] = type_name

    def is_defined(self, name: str) -> bool:
        """检查变量是否已定义（全局或临时）"""
        return name in self.global_vars or name in self.temp_vars

    def get_var_type(self, name: str) -> Optional[str]:
        """获取变量类型"""
        if name in self.global_vars:
            return self.global_vars[name].type_name
        if name in self.temp_vars:
            return self.temp_vars[name]
        return None

    def is_type_defined(self, type_name: str) -> bool:
        """检查类型是否已定义"""
        # 简单类型
        if type_name in [t.value for t in SimpleType]:
            return True
        # 数组类型（List[...]）
        if type_name.startswith("List["):
            return True
        # 自定义类型
        return type_name in self.type_defs
