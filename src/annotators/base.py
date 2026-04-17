"""块标注器基类"""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from ..models import Annotation, TextSegment, SPLBlockType


logger = logging.getLogger(__name__)


class BlockAnnotator(ABC):
    """SPL块标注器基类
    
    每个块类型都有一个对应的标注器，负责从原始prompt中提取
    属于该块的内容并返回标注结果。
    """
    
    def __init__(self, llm_client, config: Optional[dict] = None):
        """初始化标注器
        
        Args:
            llm_client: LLM客户端，用于调用模型
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.block_type = self._block_type
        
    @property
    @abstractmethod
    def _block_type(self) -> SPLBlockType:
        """返回该标注器对应的SPL块类型"""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """获取系统提示词
        
        该提示词解释该SPL块的语义，并指导LLM如何标注。
        """
        pass
    
    async def annotate(self, prompt: str) -> Annotation:
        """执行标注
        
        Args:
            prompt: 原始用户prompt
            
        Returns:
            Annotation: 标注结果
        """
        logger.info(f"Starting annotation for {self.block_type.value}")
        
        # 加载提示词
        system_prompt = self._get_system_prompt()
        
        # 调用LLM进行标注
        response = await self.llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=prompt,
            response_format="json"
        )
        
        # 解析响应
        segments = self._parse_response(response, prompt)
        
        # 构建Annotation
        annotation = Annotation(
            block_type=self.block_type,
            segments=segments,
            confidence=self._calculate_confidence(segments),
            extracted_content=self._merge_segments(segments),
            metadata={"annotator": self.__class__.__name__}
        )
        
        logger.info(f"Completed annotation for {self.block_type.value}: "
                   f"found {len(segments)} segments")
        
        return annotation
    
    @abstractmethod
    def _parse_response(self, response: dict, original_prompt: str) -> List[TextSegment]:
        """解析LLM响应，提取TextSegment列表
        
        Args:
            response: LLM的JSON响应
            original_prompt: 原始prompt（用于计算位置）
            
        Returns:
            List[TextSegment]: 提取的文本片段列表
        """
        pass
    
    def _calculate_confidence(self, segments: List[TextSegment]) -> float:
        """计算置信度
        
        基于片段数量和长度计算
        """
        if not segments:
            return 0.0
        
        # 简单的启发式：片段越多、越长，置信度越高
        total_length = sum(len(s.content) for s in segments)
        base_confidence = min(0.5 + len(segments) * 0.1, 0.9)
        length_factor = min(total_length / 100, 0.1)
        
        return base_confidence + length_factor
    
    def _merge_segments(self, segments: List[TextSegment]) -> str:
        """合并所有片段内容"""
        return "\n\n".join(s.content for s in segments)
    
    def _find_position(self, content: str, original: str) -> tuple:
        """在原始文本中查找内容位置

        Returns:
            (start_pos, end_pos) 或 (-1, -1) 如果未找到
        """
        # 清理内容以便匹配
        content_clean = content.strip()

        # 尝试精确匹配
        pos = original.find(content_clean)
        if pos >= 0:
            return (pos, pos + len(content_clean))

        # 尝试模糊匹配（忽略多余空格）
        import re
        content_pattern = re.escape(content_clean)
        content_pattern = content_pattern.replace(r'\ ', r'\s+')
        matches = list(re.finditer(content_pattern, original, re.IGNORECASE))

        if matches:
            match = matches[0]
            return (match.start(), match.end())

        # 尝试基于关键词的匹配（取前50个字符的子串）
        if len(content_clean) > 50:
            substrings = [content_clean[:50], content_clean[:30]]
        else:
            substrings = [content_clean[:30]] if len(content_clean) > 30 else [content_clean]

        for substring in substrings:
            if len(substring) < 10:
                continue
            pos = original.find(substring)
            if pos >= 0:
                # 找到起始位置，估计结束位置
                estimated_end = pos + len(content_clean)
                return (pos, min(estimated_end, len(original)))

        return (-1, -1)
