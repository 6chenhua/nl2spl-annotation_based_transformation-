"""问题生成器

为冲突生成自然语言问题，用户无需了解SPL术语。
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..models import Conflict, ClarificationQuestion, TextSegment
from .label_mapper import LabelMapper

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """问题生成器
    
    生成用户友好的澄清问题，避免使用SPL技术术语。
    """
    
    def __init__(self, label_mapper: Optional[LabelMapper] = None):
        """初始化问题生成器"""
        self.label_mapper = label_mapper or LabelMapper()
    
    def generate_question(self, 
                         conflict: Conflict,
                         original_prompt: str) -> ClarificationQuestion:
        """为冲突生成澄清问题
        
        Args:
            conflict: 冲突信息
            original_prompt: 原始prompt（用于提供上下文）
            
        Returns:
            澄清问题对象
        """
        # 提取冲突内容
        conflict_text = self._extract_conflict_text(conflict)
        
        # 创建选项
        options = self.label_mapper.create_options(
            conflict.candidate_labels,
            include_other=True
        )
        
        # 生成问题文本
        question_text = self._generate_question_text(
            conflict_text,
            options
        )
        
        # 提取上下文
        context = self._extract_context(conflict, original_prompt)
        
        return ClarificationQuestion(
            conflict=conflict,
            question_text=question_text,
            options=options,
            context=context
        )
    
    def _extract_conflict_text(self, conflict: Conflict) -> str:
        """提取冲突文本（合并所有片段）"""
        texts = []
        seen = set()
        
        for segment in conflict.segments:
            if segment.content not in seen:
                texts.append(segment.content)
                seen.add(segment.content)
        
        return "\n\n".join(texts)
    
    def _generate_question_text(self, 
                                conflict_text: str,
                                options: List[Dict]) -> str:
        """生成问题文本"""
        # 简化冲突文本用于显示
        display_text = conflict_text[:200] + "..." if len(conflict_text) > 200 else conflict_text
        
        # 构建问题
        question_parts = [
            "我需要确认一下这段内容的归属。",
            "",
            f"原文：\"{display_text}\"",
            "",
            "这段内容主要是：",
        ]
        
        # 添加选项
        for option in options:
            question_parts.append(f"{option['id']}. {option['text']}")
            if option.get('hint'):
                question_parts.append(f"   （{option['hint']}）")
        
        question_parts.extend([
            "",
            "请选择一个最符合的选项（输入数字）："
        ])
        
        return "\n".join(question_parts)
    
    def _extract_context(self, 
                        conflict: Conflict,
                        original_prompt: str) -> str:
        """提取冲突周围的上下文"""
        if not conflict.segments:
            return original_prompt
        
        # 获取冲突片段的位置范围
        min_start = min(seg.start_pos for seg in conflict.segments)
        max_end = max(seg.end_pos for seg in conflict.segments)
        
        # 扩展上下文范围
        context_start = max(0, min_start - 100)
        context_end = min(len(original_prompt), max_end + 100)
        
        return original_prompt[context_start:context_end]
    
    def generate_questions_batch(self,
                                conflicts: List[Conflict],
                                original_prompt: str) -> List[ClarificationQuestion]:
        """为多个冲突批量生成问题"""
        questions = []
        
        for i, conflict in enumerate(conflicts):
            logger.info(f"Generating question {i+1}/{len(conflicts)}")
            question = self.generate_question(conflict, original_prompt)
            questions.append(question)
        
        return questions