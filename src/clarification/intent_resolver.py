"""意图解析器

使用LLM批量处理"其他"选项的用户描述，理解用户意图并映射到SPL块类型。

流程:
1. 收集所有标准选项的直接回答
2. 收集"其他"选项的用户描述
3. 批量异步调用LLM理解描述意图
4. 返回最终的标签映射结果
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, cast
from dataclasses import dataclass

from ..models import SPLBlockType, ClarificationQuestion

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """解析结果"""
    question_index: int
    selected_label: Optional[SPLBlockType]  # 最终映射的标签
    user_response: str  # 用户的原始回答
    is_other: bool  # 是否来自"其他"选项
    llm_reasoning: Optional[str] = None  # LLM的推理过程（如果是"其他"选项）


class IntentResolver:
    """意图解析器
    
    批量处理用户澄清回答，对"其他"选项使用LLM理解意图。
    """
    
    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM客户端，用于理解用户意图
        """
        self.llm_client = llm_client
    
    async def resolve_batch(
        self,
        questions: List[ClarificationQuestion],
        user_responses: Dict[int, str]
    ) -> List[ResolutionResult]:
        """批量解析用户回答
        
        Args:
            questions: 澄清问题列表
            user_responses: 用户回答字典 {question_index: response}
        
        Returns:
            ResolutionResult列表
        """
        results = []
        other_responses = []  # 需要LLM处理的"其他"选项
        
        # 第一阶段：分离标准选项和"其他"选项
        for i, question in enumerate(questions):
            if i not in user_responses:
                # 用户没有回答此问题
                results.append(ResolutionResult(
                    question_index=i,
                    selected_label=None,
                    user_response="",
                    is_other=False
                ))
                continue
            
            response = user_responses[i]
            
            if response.startswith("OTHER:"):
                # "其他"选项，需要LLM处理
                custom_desc = response[6:].strip()
                other_responses.append((i, question, custom_desc))
                results.append(ResolutionResult(
                    question_index=i,
                    selected_label=None,  # 待LLM处理
                    user_response=response,
                    is_other=True,
                    llm_reasoning=None
                ))
            else:
                # 标准选项，直接解析
                selected_label = self._parse_standard_response(response, question.options)
                results.append(ResolutionResult(
                    question_index=i,
                    selected_label=selected_label,
                    user_response=response,
                    is_other=False
                ))
        
        # 第二阶段：批量LLM处理"其他"选项（异步，并行）
        if other_responses:
            logger.info(f"Processing {len(other_responses)} 'other' responses with LLM")
            await self._resolve_other_responses(other_responses, results)
        
        return results
    
    def _parse_standard_response(
        self,
        response: str,
        options: List[Dict]
    ) -> Optional[SPLBlockType]:
        """解析标准选项回答"""
        try:
            option_id = int(response.strip())
            for option in options:
                if option["id"] == option_id:
                    return option.get("block_type")
        except ValueError:
            pass
        return None
    
    async def _resolve_other_responses(
        self,
        other_responses: List[Tuple[int, ClarificationQuestion, str]],
        results: List[ResolutionResult]
    ):
        """批量处理"其他"选项（异步并行）"""
        # 创建并行任务
        tasks = []
        for idx, question, description in other_responses:
            task = self._resolve_single_other(idx, question, description)
            tasks.append(task)
        
        # 并行执行所有LLM调用
        llm_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 更新结果
        for (idx, question, _), llm_result in zip(other_responses, llm_results):
            if isinstance(llm_result, Exception):
                logger.error(f"LLM failed for question {idx}: {llm_result}")
                continue

            # llm_result 是 Dict，安全访问
            result_dict = cast(Dict, llm_result)

            # 找到对应的结果项并更新
            for r in results:
                if r.question_index == idx:
                    r.selected_label = result_dict.get("label")
                    r.llm_reasoning = result_dict.get("reasoning")
                    break
    
    async def _resolve_single_other(
        self,
        question_index: int,
        question: ClarificationQuestion,
        user_description: str
    ) -> Dict:
        """使用LLM理解单个"其他"选项的描述"""
        
        # 构建候选标签说明
        candidate_labels = []
        for opt in question.options:
            if opt.get("block_type") is not None:
                candidate_labels.append({
                    "id": opt["id"],
                    "description": opt["text"],
                    "block_type": opt["block_type"].value
                })
        
        # 构建提示词
        system_prompt = """你是一名专业的自然语言理解专家。

任务：根据用户的描述，理解其意图，将内容分类到最合适的SPL块类型。

候选类型说明：
"""
        
        for label in candidate_labels:
            system_prompt += f"\n{label['id']}. {label['description']} (类型: {label['block_type']})"
        
        system_prompt += """

用户提供的描述可能包含关键词、短语或完整句子。
请分析描述的核心意图，选择最匹配的类型。

返回格式（JSON）：
{
    "selected_id": 选项ID数字,
    "reasoning": "简要说明为什么这个类型最匹配"
}
"""
        
        user_prompt = f"""冲突内容："{question.conflict.segments[0].content if question.conflict.segments else 'N/A'}"

用户描述这段内容属于："{user_description}"

请分析并返回最合适的类型ID和理由。"""
        
        try:
            response = await self.llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json"
            )
            
            if isinstance(response, dict):
                selected_id = response.get("selected_id")
                reasoning = response.get("reasoning", "")
                
                # 找到对应的block_type
                for opt in question.options:
                    if opt["id"] == selected_id:
                        return {
                            "label": opt.get("block_type"),
                            "reasoning": reasoning
                        }
            
            logger.warning(f"Could not parse LLM response for question {question_index}")
            return {"label": None, "reasoning": "解析失败"}
            
        except Exception as e:
            logger.error(f"LLM call failed for question {question_index}: {e}")
            raise
