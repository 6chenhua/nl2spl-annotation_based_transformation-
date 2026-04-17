"""角色标注器

从原始prompt中提取描述AI智能体角色、个性和关键属性的内容。
PERSONA定义：AI智能体的主要角色、功能和关键属性。
"""

from typing import List
import logging
import json

from .base import BlockAnnotator
from ..models import Annotation, TextSegment, SPLBlockType

logger = logging.getLogger(__name__)


class PersonaAnnotator(BlockAnnotator):
    """角色标注器

    负责从原始prompt中提取描述AI智能体角色、个性和关键属性的内容。
    包括：主要角色/功能、个性特征、关键能力、风格/语调等。
    """

    @property
    def _block_type(self) -> SPLBlockType:
        """返回该标注器对应的SPL块类型"""
        return SPLBlockType.PERSONA

    def _get_system_prompt(self) -> str:
        """获取系统提示词

        解释PERSONA块的语义，并指导LLM如何提取相关内容。
        """
        return """你是一个专业的SPL（Structured Prompt Language）标注器。

## 你的任务
从用户提供的原始prompt中，提取所有描述**AI智能体角色（PERSONA）**的内容。

## PERSONA块的语义
PERSONA描述的是**AI智能体扮演什么角色、具备什么个性和关键属性**。
它定义了AI助手的身份定位，帮助LLM理解应该如何表现、思考和回应。

根据SPL语法：
- PERSONA := "[DEFINE_PERSONA:]" PERSONA_ASPECTS "[END_PERSONA]"
- PERSONA_ASPECTS := ROLE_ASPECT {OPTIONAL_ASPECT}
- ROLE_ASPECT := ROLE_ASPECT_NAME ":" DESCRIPTION_WITH_REFERENCES
- ROLE_ASPECT_NAME := "ROLE"
- OPTIONAL_ASPECT := OPTIONAL_ASPECT_NAME ":" DESCRIPTION_WITH_REFERENCES

## 需要提取的内容类型

### 1. 主要角色/功能（ROLE）
- AI智能体的核心身份是什么
- 主要提供什么服务或功能
- 示例："客服助手"、"代码审查员"、"数据分析助手"、"写作助手"

### 2. 个性特征
- AI的说话风格和态度
- 性格特点：专业、友好、严谨、幽默、耐心等
- 示例："亲切友好"、"严谨专业"、"简洁明了"

### 3. 关键能力
- AI擅长什么
- 具备哪些专业技能或知识领域
- 示例："熟练掌握Python编程"、"了解金融行业知识"、"擅长文案撰写"

### 4. 风格/语调
- 回应的语言风格
- 正式程度：正式、非正式、学术、口语化
- 示例："专业严谨"、"轻松活泼"、"简洁直接"

### 5. 专业领域/背景
- 所属领域或行业
- 专业知识水平
- 示例："医疗健康领域专家"、"教育行业从业者"、"电商运营专家"

### 6. 行为准则
- AI应该遵循的行为规范
- 服务理念或原则
- 示例："始终以用户需求为中心"、"保持客观中立"

## 输出格式
请以JSON格式输出，结构如下：
{
    "segments": [
        {
            "content": "提取的文本内容",
            "aspect_type": "ROLE|PERSONALITY|CAPABILITY|STYLE|DOMAIN|BEHAVIOR",
            "reason": "为什么这段内容属于PERSONA"
        }
    ]
}

## 重要提示
1. 只提取与AI智能体角色设定相关的内容
2. 保持提取内容的原始语义，不要过度概括或扩展
3. 如果原始prompt中没有明确的角色描述，返回空的segments数组
4. 提取的内容应该帮助理解"这个AI助手是什么样的角色"
5. 注意区分PERSONA和AUDIENCE：PERSONA关注AI助手的角色设定，AUDIENCE关注目标用户群体特征
6. aspect_type用于区分不同类型的角色描述，便于后续处理
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
            if isinstance(response, dict):
                segments_data = response.get("segments", [])
            elif isinstance(response, str):
                # 如果响应是字符串，尝试解析为JSON
                try:
                    parsed = json.loads(response)
                    segments_data = parsed.get("segments", []) if isinstance(parsed, dict) else []
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON response: {response[:200]}...")
                    return segments_data
            else:
                segments_data = []

            for seg_data in segments_data:
                if not isinstance(seg_data, dict):
                    continue

                content = seg_data.get("content", "").strip()
                if not content:
                    continue

                # 查找在原始文本中的位置
                start_pos, end_pos = self._find_position(content, original_prompt)

                # 构建TextSegment
                segment = TextSegment(
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    source="PERSONA"
                )
                segments.append(segment)

            logger.debug(f"Parsed {len(segments)} persona segments from response")

        except Exception as e:
            logger.error(f"Error parsing persona response: {e}")
            # 返回空列表，让调用者知道解析失败

        return segments