"""标签映射器

将SPL技术标签映射到业务领域语言，以及反向映射。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from ..models import SPLBlockType


@dataclass
class LabelMapping:
    """标签映射"""
    block_type: SPLBlockType
    business_description: str  # 业务描述（用户可见）
    question_phrase: str  # 用于问题的短语
    examples: List[str]  # 示例


class LabelMapper:
    """标签映射器
    
    管理SPL技术标签与业务语言之间的双向映射。
    """
    
    # 预定义的映射表
    _MAPPINGS: Dict[SPLBlockType, LabelMapping] = {
        SPLBlockType.PERSONA: LabelMapping(
            block_type=SPLBlockType.PERSONA,
            business_description="AI助手的角色定位、性格特征和专业背景",
            question_phrase="定义AI是谁、它扮演什么角色",
            examples=[
                "一个专业的编程助手",
                "友好的客服代表",
                "严谨的学术顾问"
            ]
        ),
        SPLBlockType.AUDIENCE: LabelMapping(
            block_type=SPLBlockType.AUDIENCE,
            business_description="目标用户群体的特征和需求",
            question_phrase="描述为谁服务、用户有什么特点",
            examples=[
                "初级程序员",
                "需要技术支持的客户",
                "学术研究人员"
            ]
        ),
        SPLBlockType.CONCEPTS: LabelMapping(
            block_type=SPLBlockType.CONCEPTS,
            business_description="专业术语和领域概念的定义",
            question_phrase="解释专业术语、定义关键概念",
            examples=[
                "API的定义",
                "领域特定的缩写",
                "技术规范的说明"
            ]
        ),
        SPLBlockType.CONSTRAINTS: LabelMapping(
            block_type=SPLBlockType.CONSTRAINTS,
            business_description="AI必须遵守的限制和规则",
            question_phrase="说明AI不能做什么、有什么限制",
            examples=[
                "不能访问敏感数据",
                "必须在5秒内响应",
                "只能使用指定的工具"
            ]
        ),
        SPLBlockType.VARIABLES: LabelMapping(
            block_type=SPLBlockType.VARIABLES,
            business_description="输入数据、输出结果和中间变量",
            question_phrase="描述处理什么数据、需要什么输入",
            examples=[
                "用户提供的文本",
                "待处理的文件",
                "生成的报告"
            ]
        ),
        SPLBlockType.WORKER_MAIN_FLOW: LabelMapping(
            block_type=SPLBlockType.WORKER_MAIN_FLOW,
            business_description="AI的工作流程和处理步骤",
            question_phrase="说明具体的工作步骤和处理流程",
            examples=[
                "先分析输入，然后调用工具，最后输出结果",
                "检查文件格式，验证内容，生成报告"
            ]
        ),
        SPLBlockType.WORKER_EXAMPLE: LabelMapping(
            block_type=SPLBlockType.WORKER_EXAMPLE,
            business_description="使用示例和输入输出样例",
            question_phrase="提供使用示例和案例说明",
            examples=[
                "示例输入和预期输出",
                "具体的使用场景"
            ]
        ),
        SPLBlockType.WORKER_FLOW_STEP: LabelMapping(
            block_type=SPLBlockType.WORKER_FLOW_STEP,
            business_description="具体的工作步骤和动作",
            question_phrase="描述具体的操作步骤",
            examples=[
                "第一步：验证输入",
                "第二步：处理数据"
            ]
        ),
    }
    
    def __init__(self):
        """初始化标签映射器"""
        self._mappings = self._MAPPINGS.copy()
    
    def get_business_description(self, block_type: SPLBlockType) -> str:
        """获取业务描述"""
        if block_type in self._mappings:
            return self._mappings[block_type].business_description
        return f"{block_type.value}相关的内容"
    
    def get_question_phrase(self, block_type: SPLBlockType) -> str:
        """获取问题短语"""
        if block_type in self._mappings:
            return self._mappings[block_type].question_phrase
        return f"描述{block_type.value}相关的内容"
    
    def get_examples(self, block_type: SPLBlockType) -> List[str]:
        """获取示例"""
        if block_type in self._mappings:
            return self._mappings[block_type].examples
        return []
    
    def create_options(self, 
                      block_types: List[SPLBlockType],
                      include_other: bool = True) -> List[Dict]:
        """创建选项列表（用于问题）
        
        Args:
            block_types: 候选标签列表
            include_other: 是否包含"其他"选项
            
        Returns:
            选项列表，每个选项包含显示文本和映射的标签
        """
        options = []
        
        for i, block_type in enumerate(block_types):
            mapping = self._mappings.get(block_type)
            if mapping:
                option = {
                    "id": i + 1,
                    "text": mapping.business_description,
                    "hint": f"例如：{', '.join(mapping.examples[:2])}",
                    "block_type": block_type  # 内部使用，不显示给用户
                }
                options.append(option)
        
        if include_other:
            options.append({
                "id": len(options) + 1,
                "text": "其他（请说明）",
                "hint": "如果以上选项都不符合",
                "block_type": None
            })
        
        return options
    
    def map_response_to_label(self, 
                             response: str, 
                             options: List[Dict]) -> Optional[SPLBlockType]:
        """将用户回答映射回SPL标签
        
        Args:
            response: 用户回答（选项ID或文本）
            options: 选项列表
            
        Returns:
            对应的SPLBlockType，如果无法映射则返回None
        """
        # 尝试解析为选项ID
        try:
            option_id = int(response.strip())
            for option in options:
                if option["id"] == option_id:
                    return option.get("block_type")
        except ValueError:
            pass
        
        # 尝试文本匹配
        response_lower = response.lower()
        for option in options:
            if option["text"].lower() in response_lower:
                return option.get("block_type")
        
        return None
    
    def get_all_mappings(self) -> Dict[SPLBlockType, LabelMapping]:
        """获取所有映射"""
        return self._mappings.copy()
    
    def update_mapping(self, block_type: SPLBlockType, mapping: LabelMapping):
        """更新映射（允许自定义）"""
        self._mappings[block_type] = mapping