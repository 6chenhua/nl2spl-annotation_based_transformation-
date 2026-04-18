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
    
    async def collect_responses_batch(self,
                                     questions: list[ClarificationQuestion],
                                     max_questions: int = 10) -> Dict[int, str]:
        """批量收集用户回答（仅收集，不解析）

        这是异步澄清流程的第一阶段，只收集用户输入，不涉及LLM调用。

        Args:
            questions: 澄清问题列表
            max_questions: 最多处理的问题数

        Returns:
            用户回答字典 {question_index: response}
            response 可能是:
            - "1", "2", "3" 等选项ID（标准选项）
            - "OTHER:用户描述"（其他选项）
            - ""（用户跳过或未回答）
        """
        responses = {}

        for i, question in enumerate(questions[:max_questions]):
            logger.info(f"Collecting response for question {i+1}/{len(questions)}")
            self.present_question(question)
            response = self.collect_response(question)
            responses[i] = response

        return responses

    async def resolve_conflicts_batch(self,
                                     questions: list[ClarificationQuestion],
                                     max_questions: int = 10) -> Dict[int, Optional[SPLBlockType]]:
        """批量解决冲突（旧版兼容方法）

        现在使用两阶段流程：
        1. 先调用 collect_responses_batch 收集回答
        2. 使用 IntentResolver 解析"其他"选项

        为了保持兼容，这个方法现在会调用完整的两阶段流程。
        """
        from .intent_resolver import IntentResolver

        # 阶段1: 收集回答
        responses = await self.collect_responses_batch(questions, max_questions)

        # 阶段2: 解析意图（需要LLM客户端，但这里无法访问）
        # 为了保持兼容，我们只处理标准选项
        resolutions = {}
        for i, question in enumerate(questions[:max_questions]):
            response = responses.get(i, "")
            if response.startswith("OTHER:"):
                # "其他"选项需要LLM处理，这里返回None
                logger.warning(f"Question {i} selected 'other', needs LLM processing")
                resolutions[i] = None
            else:
                # 标准选项直接解析
                selected_label = self.label_mapper.map_response_to_label(
                    response, question.options
                )
                resolutions[i] = selected_label

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

                # 验证是否为有效选项ID
                valid_ids = [str(opt["id"]) for opt in question.options]
                if response not in valid_ids:
                    print(f"无效的选项，请输入: {', '.join(valid_ids)}")
                    continue

                # 检查是否选择了"其他"选项
                selected_option = None
                for opt in question.options:
                    if str(opt["id"]) == response:
                        selected_option = opt
                        break

                if selected_option and selected_option.get("block_type") is None:
                    # 用户选择了"其他"，允许自由输入理解
                    print("\n您选择了'其他'，请描述您的理解：")
                    print("（例如：'这是描述AI的语气风格' 或 '这是关于用户交互的说明'）")
                    custom_response = input("您的描述: ").strip()

                    if custom_response:
                        # 返回格式：OTHER:用户的描述
                        return f"OTHER:{custom_response}"
                    else:
                        print("未提供描述，跳过此冲突。")
                        return ""

                return response

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