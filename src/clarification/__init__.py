"""人机交互澄清模块

负责生成自然语言问题，收集用户反馈，解决标注冲突。
"""

from .question_generator import QuestionGenerator
from .clarification_ui import ClarificationUI, ConsoleUI
from .label_mapper import LabelMapper

__all__ = ["QuestionGenerator", "ClarificationUI", "ConsoleUI", "LabelMapper"]