"""核心数据模型"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
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
