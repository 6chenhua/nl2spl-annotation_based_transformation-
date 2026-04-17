"""澄清UI接口和实现

提供人机交互界面，支持Console、Web、API等多种模式。
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..models import ClarificationQuestion, Conflict, SPLBlockType
from .label_mapper import LabelMapper

logger = logging.getLogger(__name__)


class ClarificationUI(ABC):
    """澄清UI抽象基类"""
    
    def __init__(self, label_mapper: Optional[LabelMapper] = None):
        self.label_mapper = label_mapper or LabelMapper()
    
    @abstractmethod
    def present_question(self, question: ClarificationQuestion) -> None:
        """向用户展示问题"""
        pass
    
    @abstractmethod
    def collect_response(self, question: ClarificationQuestion) -> str:
        """收集用户回答"""
        pass
    
    async def resolve_conflict(self, 
                              question: ClarificationQuestion) -> Optional[SPLBlockType]:
        """解决冲突
        
        展示问题，收集回答，映射回SPL标签
        
        Args:
            question: 澄清问题
            
        Returns:
            用户选择的SPLBlockType，如果失败则返回None
        """
        self.present_question(question)
        response = self.collect_response(question)
        
        if not response:
            logger.warning("No response collected")
            return None
        
        # 映射回答到标签
        selected_label = self.label_mapper.map_response_to_label(
            response, question.options
        )
        
        if selected_label:
            logger.info(f"Conflict resolved to: {selected_label.value}")
        else:
            logger.warning(f"Could not map response '{response}' to label")
        
        return selected_label
    
    async def resolve_conflicts_batch(self,
                                     questions: list[ClarificationQuestion],
                                     max_questions: int = 10) -> Dict[int, Optional[SPLBlockType]]:
        """批量解决冲突"""
        resolutions = {}
        
        for i, question in enumerate(questions[:max_questions]):
            logger.info(f"Resolving conflict {i+1}/{len(questions)}")
            resolution = await self.resolve_conflict(question)
            resolutions[i] = resolution
        
        return resolutions


class ConsoleUI(ClarificationUI):
    """控制台交互界面"""
    
    def present_question(self, question: ClarificationQuestion) -> None:
        """在控制台展示问题"""
        print("\n" + "=" * 80)
        print("需要澄清")
        print("=" * 80)
        print(question.question_text)
        print("=" * 80 + "\n")
    
    def collect_response(self, question: ClarificationQuestion) -> str:
        """从控制台收集用户回答"""
        while True:
            try:
                response = input("您的选择: ").strip()
                
                if not response:
                    print("请输入有效的选择")
                    continue
                
                # 验证是否为有效选项
                valid_ids = [str(opt["id"]) for opt in question.options]
                if response in valid_ids:
                    return response
                
                print(f"无效的选项，请输入: {', '.join(valid_ids)}")
                
            except (EOFError, KeyboardInterrupt):
                print("\n取消澄清")
                return ""
    
    def confirm(self, message: str) -> bool:
        """确认提示"""
        response = input(f"{message} [y/N]: ").strip().lower()
        return response in ('y', 'yes')


class ProgrammaticUI(ClarificationUI):
    """程序化UI（用于API模式）
    
    不直接交互，而是返回问题供调用者处理
    """
    
    def __init__(self):
        super().__init__()
        self.pending_questions: list[ClarificationQuestion] = []
        self.responses: Dict[int, str] = {}
    
    def present_question(self, question: ClarificationQuestion) -> None:
        """将问题添加到待处理队列"""
        self.pending_questions.append(question)
        logger.info(f"Question queued: {question.question_text[:100]}...")
    
    def collect_response(self, question: ClarificationQuestion) -> str:
        """从预置响应中查找回答"""
        idx = self.pending_questions.index(question) if question in self.pending_questions else -1
        
        if idx >= 0 and idx in self.responses:
            return self.responses[idx]
        
        logger.warning("No pre-set response found for question")
        return ""
    
    def get_pending_questions(self) -> list[ClarificationQuestion]:
        """获取所有待处理的问题"""
        return self.pending_questions.copy()
    
    def submit_response(self, question_index: int, response: str) -> None:
        """提交用户回答"""
        self.responses[question_index] = response
        logger.info(f"Response submitted for question {question_index}: {response}")
    
    def clear(self) -> None:
        """清空状态"""
        self.pending_questions.clear()
        self.responses.clear()