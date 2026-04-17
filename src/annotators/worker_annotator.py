"""WORKER块标注器"""

from typing import List
import logging

from .base import BlockAnnotator
from ..models import TextSegment, SPLBlockType

logger = logging.getLogger(__name__)


class WorkerAnnotator(BlockAnnotator):
    """WORKER块标注器
    
    负责识别和提取工作流步骤、处理逻辑的内容。
    一个WORKER可能包含MAIN_FLOW、EXAMPLES等子部分。
    """
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.WORKER_MAIN_FLOW
    
    def _get_system_prompt(self) -> str:
        return '''你是一名专业的SPL内容标注专家。

## 任务
从用户的自然语言描述中，识别并提取属于WORKER（工作流）的内容。

## WORKER定义
WORKER定义AI Agent的工作流程、处理步骤和逻辑。
这是定义"AI如何工作"的部分。

## 包含的内容类型
1. **主流程 (MAIN_FLOW)**: 核心处理步骤和顺序
2. **示例 (EXAMPLES)**: 输入输出示例、使用案例
3. **流程步骤 (FLOW_STEP)**: 具体的处理动作和决策点

### MAIN_FLOW 包含:
- 处理步骤序列
- 条件判断（if/else）
- 循环处理
- 工具调用
- 输入输出处理

### EXAMPLES 包含:
- 成功的使用示例
- 预期输入输出
- 边界案例
- 失败/错误示例

### FLOW_STEP 包含:
- 具体动作描述
- 决策点
- 状态转换
- 工具使用

## 不包含的内容
- AI的角色定义（属于PERSONA）
- 目标用户描述（属于AUDIENCE）
- 领域术语定义（属于CONCEPTS）
- 限制条件（属于CONSTRAINTS）
- 变量定义（属于VARIABLES）

## 输出格式
以JSON格式返回提取的段落列表，并分类到WORKER的不同子部分：
```json
{
    "segments": [
        {
            "content": "提取的原文内容",
            "worker_subsection": "MAIN_FLOW",
            "relevance": "high",
            "reason": "这段描述了处理步骤"
        },
        {
            "content": "提取的原文内容",
            "worker_subsection": "EXAMPLES",
            "relevance": "high",
            "reason": "这段是输入输出示例"
        }
    ]
}
```

## 注意
- 只提取确定属于WORKER的内容
- 如果没有相关内容，返回空数组
- 保持文本原样，不要改写
- worker_subsection可选: MAIN_FLOW, EXAMPLES, FLOW_STEP
- relevance可选: high(高度相关), medium(中等相关), low(低度相关)
'''
    
    def _parse_response(self, response: dict, original_prompt: str) -> List[TextSegment]:
        """解析LLM响应"""
        segments = []
        
        if "segments" not in response:
            logger.warning(f"No 'segments' key in response for WORKER annotator")
            return segments
        
        for seg_data in response["segments"]:
            content = seg_data.get("content", "").strip()
            if not content:
                continue
            
            # 获取子类型
            subsection = seg_data.get("worker_subsection", "MAIN_FLOW")
            
            start_pos, end_pos = self._find_position(content, original_prompt)

            if start_pos >= 0:
                segments.append(TextSegment(
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    source=f"worker_annotator_{subsection.lower()}"
                ))
            else:
                # 位置查找失败，但仍保留片段用于后续处理
                # 使用内容哈希作为近似位置标记
                logger.warning(f"Could not find exact position for content: {content[:50]}...")
                segments.append(TextSegment(
                    content=content,
                    start_pos=-1,
                    end_pos=-1,
                    source=f"worker_annotator_{subsection.lower()}"
                ))
        
        return segments
    
    def _calculate_confidence(self, segments: List[TextSegment]) -> float:
        """计算置信度 - WORKER通常内容较多"""
        if not segments:
            return 0.0
        
        # WORKER通常包含多个步骤
        base_confidence = min(0.6 + len(segments) * 0.05, 0.9)
        
        # 考虑内容长度
        total_length = sum(len(s.content) for s in segments)
        length_factor = min(total_length / 200, 0.1)
        
        return base_confidence + length_factor