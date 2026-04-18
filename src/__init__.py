"""Annotated NL2SPL Pipeline

基于标注的自然语言到SPL转换管道。
"""

from .pipeline import Pipeline
from .models import PipelineResult, Annotation, Conflict
from .output_manager import OutputManager

__version__ = "0.1.0"
__all__ = ["Pipeline", "PipelineResult", "Annotation", "Conflict", "OutputManager"]