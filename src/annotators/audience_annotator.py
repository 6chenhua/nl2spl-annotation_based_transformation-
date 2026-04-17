"""观众标注器

从原始prompt中提取描述目标用户群体的内容。
AUDIENCE描述：目标用户属性、用户特征、使用场景。
"""

from typing import List
import logging

from .base import BlockAnnotator
from ..models import Annotation, TextSegment, SPLBlockType

logger = logging.getLogger(__name__)


class AudienceAnnotator(BlockAnnotator):
    """观众标注器

    负责从原始prompt中提取描述目标用户群体的内容。
    包括：用户是谁、用户特征、用户需求/目标、使用场景等。
    """

    @property
    def _block_type(self) -> SPLBlockType:
        """返回该标注器对应的SPL块类型"""
        return SPLBlockType.AUDIENCE

    def _get_system_prompt(self) -> str:
        """获取系统提示词

        解释AUDIENCE块的语义，并指导LLM如何提取相关内容。
        """
        return """你是一个专业的SPL（Structured Prompt Language）标注器。

## 你的任务
从用户提供的原始prompt中，提取所有描述**目标用户群体（AUDIENCE）**的内容。

## AUDIENCE块的语义
AUDIENCE描述的是**谁将使用这个系统/功能**，以及他们的特征、需求和使用场景。
它帮助LLM理解是为谁而设计，从而生成更符合目标用户期望的响应。

## 需要提取的内容类型

### 1. 用户身份描述
- 用户是什么人（角色、职业、身份）
- 示例："数据分析师"、"企业管理员"、"普通消费者"

### 2. 用户特征属性
- 技术水平：专家用户、新手、初级、中级、高级
- 权限级别：普通用户、管理员、超级管理员
- 行业领域：医疗、金融、教育、电商等
- 组织规模：个人、小团队、中型企业、大型企业

### 3. 用户需求与目标
- 用户想要完成什么任务
- 用户的核心诉求是什么
- 用户期望达到什么效果
- 示例："想要快速生成销售报表"、"需要管理大量客户信息"

### 4. 使用场景
- 在什么环境下使用
- 什么情况下会使用这个功能
- 典型使用流程或步骤
- 示例："在会议中实时展示数据"、"每日例行数据汇总"

### 5. 用户限制与痛点
- 用户面临的问题或困难
- 现有方案的不足
- 示例："不想每次都手动整理数据"、"现有系统太复杂难用"

## 输出格式
请以JSON格式输出，结构如下：
{
    "segments": [
        {
            "content": "提取的文本内容",
            "reason": "为什么这段内容属于AUDIENCE"
        }
    ]
}

## 重要提示
1. 只提取与目标用户群体相关的内容
2. 保持提取内容的原始语义，不要过度概括或扩展
3. 如果原始prompt中没有明确的用户群体描述，返回空的segments数组
4. 提取的内容应该帮助理解"这个系统是为谁设计的"
5. 注意区分AUDIENCE和PERSONA：AUDIENCE关注用户群体特征，PERSONA关注AI助手的角色设定
"""

    def _parse_response(self, response: dict, original_prompt: str) -> List[TextSegment]:
        """解析LLM响应，提取TextSegment列表

        Args:
            response: LLM的JSON响应
            original_prompt: 原始prompt（用于计算位置）

        Returns:
            List[TextSegment]: 提取的文本片段列表
        """
        segments = []

        try:
            # 提取segments数组
            segments_data = response.get("segments", [])

            for seg_data in segments_data:
                content = seg_data.get("content", "").strip()
                if not content:
                    continue

                # 查找在原始文本中的位置
                start_pos, end_pos = self._find_position(content, original_prompt)

                segment = TextSegment(
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    source=self.__class__.__name__
                )
                segments.append(segment)

            logger.debug(f"解析到 {len(segments)} 个AUDIENCE片段")

        except Exception as e:
            logger.error(f"解析AUDIENCE响应时出错: {e}")
            # 返回空列表，让上层处理
            segments = []

        return segments