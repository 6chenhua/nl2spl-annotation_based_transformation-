"""概念标注器 - 提取领域特定术语和定义"""

from typing import List
import logging

from .base import BlockAnnotator
from ..models import Annotation, TextSegment, SPLBlockType

logger = logging.getLogger(__name__)


class ConceptsAnnotator(BlockAnnotator):
    """CONCEPTS块标注器

    负责从原始prompt中提取领域特定的概念、术语和定义。
    CONCEPTS块包含：
    - 术语-定义对
    - 领域特定知识
    - 技术概念
    - 缩略语及其全称
    """

    @property
    def _block_type(self) -> SPLBlockType:
        """返回该标注器对应的SPL块类型"""
        return SPLBlockType.CONCEPTS

    def _get_system_prompt(self) -> str:
        """获取系统提示词

        指导LLM如何从prompt中提取概念和定义信息。
        """
        return """你是一个专业的领域概念提取专家。你的任务是从用户输入的prompt中识别和提取领域特定的概念、术语和定义。

## 你的任务

从给定的prompt中提取以下类型的信息：

1. **技术术语及其含义**：识别prompt中使用的专业术语，并提取其定义或解释
2. **领域概念**：识别与问题领域相关的核心概念
3. **定义**：任何明确定义的内容，包括"XX是指..."、"XX定义为..."等模式
4. **缩略语和全称**：提取所有缩略语及其对应的完整表达

## 输出格式

请以JSON格式输出，结构如下：

```json
{
  "concepts": [
    {
      "term": "术语名称",
      "definition": "术语的定义或解释",
      "type": "term|concept|acronym|definition",
      "source_text": "在原文中对应的文本"
    }
  ]
}
```

## 提取原则

1. **准确性**：只提取prompt中明确提到的概念，不要推测或添加不存在的内容
2. **完整性**：如果一个术语有多个相关解释，全部提取
3. **上下文感知**：注意术语在特定上下文中的特殊含义
4. **优先级**：
   - 优先提取有明确定义的术语
   - 其次提取有解释的术语
   - 最后提取无解释但属于领域特定的概念

## 注意事项

- 如果prompt中没有明显的概念或定义信息，返回空的concepts数组
- 缩略语需要同时提供缩写和全称
- source_text字段应该包含原文中用于提取该概念的完整句子或段落

请开始提取。"""

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
            concepts_data = response.get("concepts", [])

            if not concepts_data:
                logger.warning(f"{self.block_type.value}: LLM响应中未找到concepts字段")
                return segments

            for concept in concepts_data:
                term = concept.get("term", "").strip()
                definition = concept.get("definition", "").strip()
                source_text = concept.get("source_text", "").strip()

                # 优先使用source_text定位，否则使用term+definition组合
                if source_text:
                    content = source_text
                elif term and definition:
                    content = f"{term}：{definition}"
                elif term:
                    content = term
                else:
                    continue

                # 查找在原始文本中的位置
                start_pos, end_pos = self._find_position(content, original_prompt)

                # 如果找不到，使用term作为内容
                if start_pos == -1 and term:
                    start_pos, end_pos = self._find_position(term, original_prompt)
                    if start_pos != -1:
                        content = term

                if start_pos == -1:
                    # 使用词法位置估计（作为后备）
                    logger.warning(
                        f"{self.block_type.value}: 无法在原文中找到概念 '{term}' 的位置"
                    )
                    start_pos = 0
                    end_pos = len(content)

                segments.append(
                    TextSegment(
                        content=content,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        source=self.__class__.__name__
                    )
                )

            logger.info(f"{self.block_type.value}: 成功提取 {len(segments)} 个概念")

        except Exception as e:
            logger.error(f"{self.block_type.value}: 解析响应时出错: {e}")
            raise

        return segments