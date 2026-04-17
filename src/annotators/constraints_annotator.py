"""约束条件标注器

从原始prompt中提取限制、需求和护栏相关的内容。
CONSTRAINTS描述：代理不能做什么、必须遵守的限制、必须满足的需求、安全约束等。
"""

from typing import List
import logging

from .base import BlockAnnotator
from ..models import Annotation, TextSegment, SPLBlockType

logger = logging.getLogger(__name__)


class ConstraintsAnnotator(BlockAnnotator):
    """约束条件标注器

    负责从原始prompt中提取限制、需求和护栏相关的内容。
    包括：代理不能做什么、必须遵守的限制、必须满足的需求、安全约束、性能期望等。
    """

    @property
    def _block_type(self) -> SPLBlockType:
        """返回该标注器对应的SPL块类型"""
        return SPLBlockType.CONSTRAINTS

    def _get_system_prompt(self) -> str:
        """获取系统提示词

        解释CONSTRAINTS块的语义，并指导LLM如何提取相关内容。
        """
        return """你是一个专业的SPL（Structured Prompt Language）标注器。

## 你的任务
从用户提供的原始prompt中，提取所有描述**约束条件（CONSTRAINTS）**的内容。

## CONSTRAINTS块的语义
CONSTRAINTS描述的是**代理不能做什么、必须遵守什么限制、必须满足什么需求**。
它帮助LLM明确行为的边界和底线，确保生成安全、合规、可预测的响应。

## 需要提取的内容类型

### 1. 限制（Limitations）
- 代理不能做什么
- 禁止执行的操作
- 不能访问的资源或功能
- 示例："不能访问外部网站"、"不能修改系统配置"、"不能查看其他用户的数据"

### 2. 需求（Requirements）
- 必须满足的条件
- 必须完成的任务
- 必须遵守的规范
- 示例："必须验证用户身份"、"必须在24小时内回复"、"必须遵守数据保护法规"

### 3. 护栏（Guardrails）
- 安全约束
- 合规要求
- 伦理边界
- 示例："不能生成有害内容"、"不能泄露用户隐私"、"必须拒绝非法请求"

### 4. 性能期望（Performance Expectations）
- 响应时间要求
- 准确性要求
- 可用性要求
- 示例："必须在3秒内响应"、"准确率不低于95%"、"服务可用性达到99.9%"

### 5. 边界条件（Boundary Conditions）
- 输入限制
- 适用范围
- 极端情况处理
- 示例："最多支持1000个并发用户"、"仅支持中文输入"、"超出范围的请求应返回错误"

## 输出格式
请以JSON格式输出，结构如下：
{
  "segments": [
    {
      "content": "提取的文本内容",
      "reason": "为什么这段内容属于CONSTRAINTS",
      "category": "限制|需求|护栏|性能期望|边界条件"
    }
  ]
}

## 重要提示
1. 只提取与约束条件相关的内容
2. 保持提取内容的原始语义，不要过度概括或扩展
3. 如果原始prompt中没有明确的约束条件描述，返回空的segments数组
4. 提取的内容应该帮助明确"代理行为的边界在哪里"
5. 注意区分CONSTRAINTS和其他块：
   - CONSTRAINTS关注代理的限制和必须遵守的规则
   - CONCEPTS关注核心概念和定义
   - PERSONA关注AI助手的角色设定
6. 分类标签用于更细粒度地标识约束类型，但不影响核心提取
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

            logger.debug(f"解析到 {len(segments)} 个CONSTRAINTS片段")

        except Exception as e:
            logger.error(f"解析CONSTRAINTS响应时出错: {e}")
            # 返回空列表，让上层处理
            segments = []

        return segments