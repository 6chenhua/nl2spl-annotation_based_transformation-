"""SPL合并器

将所有生成的SPL块合并为完整的SPL代码。
"""

import logging
from typing import Dict, Optional

from ..models import SPLBlockType

logger = logging.getLogger(__name__)


class SPLMerger:
    """SPL合并器
    
    按照SPL语法规范，将所有块按正确顺序合并。
    """
    
    # SPL块的标准顺序
    BLOCK_ORDER = [
        SPLBlockType.PERSONA,
        SPLBlockType.AUDIENCE,
        SPLBlockType.CONCEPTS,
        SPLBlockType.CONSTRAINTS,
        SPLBlockType.VARIABLES,
        SPLBlockType.TYPES,
        SPLBlockType.WORKER_MAIN_FLOW,
        SPLBlockType.WORKER_EXAMPLE,
        SPLBlockType.WORKER_FLOW_STEP,
    ]
    
    def __init__(self, agent_name: str = "GeneratedAgent"):
        """初始化合并器
        
        Args:
            agent_name: Agent名称
        """
        self.agent_name = agent_name
    
    def merge(self, blocks: Dict[SPLBlockType, str]) -> str:
        """合并所有SPL块
        
        Args:
            blocks: 各SPL块的代码字典
            
        Returns:
            完整的SPL代码
        """
        logger.info(f"Merging {len(blocks)} SPL blocks")
        
        # 按顺序收集块
        ordered_blocks = []
        
        for block_type in self.BLOCK_ORDER:
            if block_type in blocks and blocks[block_type].strip():
                ordered_blocks.append(blocks[block_type])
        
        # 合并
        merged_content = "\n\n".join(ordered_blocks)
        
        # 包装成完整SPL
        spl_code = self._wrap_agent(merged_content)
        
        # 格式化
        spl_code = self._format_spl(spl_code)
        
        logger.info(f"Merged SPL code: {len(spl_code)} chars")
        
        return spl_code
    
    def _wrap_agent(self, content: str) -> str:
        """包装成完整的Agent定义"""
        return f'''[DEFINE_AGENT: {self.agent_name}]

{content}

[END_AGENT]'''
    
    def _format_spl(self, code: str) -> str:
        """格式化SPL代码"""
        lines = code.split('\n')
        formatted = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # 检查是否需要减少缩进（结束标签）
            if stripped.startswith('[END_'):
                indent_level = max(0, indent_level - 1)
            
            # 添加当前行
            formatted.append('    ' * indent_level + stripped)
            
            # 检查是否需要增加缩进（开始标签）
            if stripped.startswith('[DEFINE_') or stripped.startswith('[INPUTS]') or \
               stripped.startswith('[OUTPUTS]') or stripped.startswith('[MAIN_FLOW]') or \
               stripped.startswith('[ALTERNATIVE_FLOW') or stripped.startswith('[EXCEPTION_FLOW') or \
               stripped.startswith('[EXAMPLES]'):
                indent_level += 1
        
        return '\n'.join(formatted)
    
    def validate_syntax(self, code: str) -> tuple[bool, list[str]]:
        """基本的语法验证
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查是否包含DEFINE_AGENT
        if '[DEFINE_AGENT:' not in code:
            errors.append("Missing [DEFINE_AGENT: ...]")
        
        # 检查是否包含END_AGENT
        if '[END_AGENT]' not in code:
            errors.append("Missing [END_AGENT]")
        
        # 检查标签匹配
        import re
        open_tags = re.findall(r'\[DEFINE_(\w+)', code)
        close_tags = re.findall(r'\[END_(\w+)', code)
        
        for tag in open_tags:
            if tag != 'AGENT' and tag not in close_tags:
                errors.append(f"Missing [END_{tag}] for [DEFINE_{tag}]")
        
        # 检查括号匹配
        if code.count('[') != code.count(']'):
            errors.append("Unmatched brackets")
        
        return len(errors) == 0, errors