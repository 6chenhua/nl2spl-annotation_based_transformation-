"""块标注器模块

负责将原始prompt'中的内容标注到不同的SPL块类型。
"""

from .base import BlockAnnotator
from .persona_annotator import PersonaAnnotator
from .audience_annotator import AudienceAnnotator
from .concepts_annotator import ConceptsAnnotator
from .constraints_annotator import ConstraintsAnnotator
from .variables_annotator import VariablesAnnotator
from .worker_annotator import WorkerAnnotator

__all__ = [
    "BlockAnnotator",
    "PersonaAnnotator",
    "AudienceAnnotator",
    "ConceptsAnnotator",
    "ConstraintsAnnotator",
    "VariablesAnnotator",
    "WorkerAnnotator",
]