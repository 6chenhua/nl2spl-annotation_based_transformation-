"""VARIABLES块标注器"""

from typing import List
import logging

from .base import BlockAnnotator
from ..models import TextSegment, SPLBlockType

logger = logging.getLogger(__name__)


class VariablesAnnotator(BlockAnnotator):
    """VARIABLES块标注器
    
    负责识别和提取变量定义、数据类型的内容。
    """
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.VARIABLES
    
    def _get_system_prompt(self) -> str:
        return '''你是一名专业的SPL内容标注专家。

## 任务
从用户的自然语言描述中，识别并提取属于VARIABLES（变量定义）的内容。

## VARIABLES定义
VARIABLES定义AI Agent处理的数据、输入、输出和中间变量。
这是定义"AI处理什么数据"的部分。

## 包含的内容类型
- 输入参数描述
- 输出结果描述
- 数据类型说明（文本、数字、列表等）
- 文件或数据源引用
- 中间变量的定义
- 变量约束（取值范围、必填/可选）

## 不包含的内容
- AI的角色定义（属于PERSONA）
- 目标用户描述（属于AUDIENCE）
- 领域术语定义（属于CONCEPTS）
- 一般性限制条件（属于CONSTRAINTS）
- 具体步骤流程（属于WORKER）

## 输出格式
以JSON格式返回提取的段落列表：
```json
{
    "segments": [
        {
            "content": "提取的原文内容",
            "relevance": "high",
            "reason": "这段描述了输入变量"
        }
    ]
}
```

## 注意
- 只提取确定属于VARIABLES的内容
- 如果没有相关内容，返回空数组
- 保持文本原样，不要改写
- relevance可选: high(高度相关), medium(中等相关), low(低度相关)
'''
    
    def _parse_response(self, response: dict, original_prompt: str) -> List[TextSegment]:
        """解析LLM响应"""
        segments = []
        
        if "segments" not in response:
            logger.warning(f"No 'segments' key in response for VARIABLES annotator")
            return segments
        
        for seg_data in response["segments"]:
            content = seg_data.get("content", "").strip()
            if not content:
                continue
            
            start_pos, end_pos = self._find_position(content, original_prompt)
            
            if start_pos >= 0:
                segments.append(TextSegment(
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    source="variables_annotator"
                ))
            else:
                logger.warning(f"Could not find position for content: {content[:50]}...")
        
        return segments