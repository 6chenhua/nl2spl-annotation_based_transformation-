"""变量提取与类型推断模块

Phase 2核心组件：
- VariableExtractor: 从Worker标注提取变量
- TypeInferencer: 推断变量类型
- TypeCollector: 收集复杂类型定义
"""

from .variable_extractor import VariableExtractor
from .type_inferencer import TypeInferencer
from .type_collector import TypeCollector

__all__ = [
    "VariableExtractor",
    "TypeInferencer",
    "TypeCollector",
]
