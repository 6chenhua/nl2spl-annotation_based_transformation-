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
    
    # SPL块的标准顺序（重构后：TYPES在最前，VARIABLES引用TYPES）
    BLOCK_ORDER = [
        SPLBlockType.TYPES,           # 优先生成，供VARIABLES引用
        SPLBlockType.PERSONA,
        SPLBlockType.AUDIENCE,
        SPLBlockType.CONCEPTS,
        SPLBlockType.CONSTRAINTS,
        SPLBlockType.VARIABLES,       # 引用TYPES中定义的类型
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
    
    def merge(self, blocks: Dict[SPLBlockType, str], auto_fix: bool = True) -> str:
        """合并所有SPL块

        Args:
            blocks: 各SPL块的代码字典
            auto_fix: 是否自动修复未声明变量

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

        # 自动修复未声明变量
        if auto_fix:
            spl_code = self.fix_missing_variables(spl_code)
            # 再次格式化
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
        """基本的语法验证（重构后增强版）

        Returns:
            (是否有效, 错误列表)
        """
        import re

        errors = []

        # 1. 检查是否包含DEFINE_AGENT
        if '[DEFINE_AGENT:' not in code:
            errors.append("Missing [DEFINE_AGENT: ...]")

        # 2. 检查是否包含END_AGENT
        if '[END_AGENT]' not in code:
            errors.append("Missing [END_AGENT]")

        # 3. 检查标签匹配
        open_tags = re.findall(r'\[DEFINE_(\w+)', code)
        close_tags = re.findall(r'\[END_(\w+)', code)

        for tag in open_tags:
            if tag != 'AGENT' and tag not in close_tags:
                errors.append(f"Missing [END_{tag}] for [DEFINE_{tag}]")

        # 4. 检查括号匹配
        if code.count('[') != code.count(']'):
            errors.append("Unmatched brackets")

        # 5. 提取VARIABLES块中的变量定义
        var_pattern = r'\[DEFINE_VARIABLES:\](.*?)\[END_VARIABLES\]'
        var_match = re.search(var_pattern, code, re.DOTALL)
        defined_vars = set()

        if var_match:
            var_content = var_match.group(1)
            # 提取变量名: 模式 "var_name: type" 或 "var_name:type"
            var_defs = re.findall(r'(?:^|\n)\s*(?:\"[^\"]*\"\s+)?(\w+)\s*:', var_content)
            defined_vars.update(var_defs)

        # 6. 检查<REF>引用是否有效
        ref_pattern = r'<REF>\*?(\w+)</REF>'
        refs = re.findall(ref_pattern, code)

        for ref in refs:
            if ref not in defined_vars:
                errors.append(f"Reference to undefined variable: <REF>{ref}</REF>")

        # 7. 检查TYPES块中定义的类型是否被VARIABLES引用
        types_pattern = r'\[DEFINE_TYPES:\](.*?)\[END_TYPES\]'
        types_match = re.search(types_pattern, code, re.DOTALL)
        defined_types = set()

        if types_match:
            types_content = types_match.group(1)
            # 提取类型名: 模式 "TypeName = ..."
            type_defs = re.findall(r'(?:^|\n)\s*(?:\"[^\"]*\"\s+)?(\w+)\s*=', types_content)
            defined_types.update(type_defs)

        # 8. 检查VARIABLES中引用的类型是否存在
        if var_match:
            var_content = var_match.group(1)
            # 提取类型引用（非简单类型）
            # 简单类型: text, image, audio, number, boolean, List[...]
            type_refs = re.findall(r':\s*(\w+)(?:\s*$|\s*\[)', var_content)
            simple_types = {'text', 'image', 'audio', 'number', 'boolean', 'List'}

            for type_ref in type_refs:
                if type_ref not in simple_types and type_ref not in defined_types:
                    errors.append(f"Undefined type referenced: {type_ref}")

        # 9. 检查TYPES是否在VARIABLES之前
        types_pos = code.find('[DEFINE_TYPES:')
        vars_pos = code.find('[DEFINE_VARIABLES:')

        if types_pos > 0 and vars_pos > 0 and types_pos > vars_pos:
            errors.append("TYPES block should come before VARIABLES block")

        return len(errors) == 0, errors

    def fix_missing_variables(self, code: str) -> str:
        """自动修复未声明的变量

        检测在<REF>中引用但未在VARIABLES中声明的变量，
        并自动添加到VARIABLES块中。

        Args:
            code: SPL代码

        Returns:
            修复后的代码
        """
        import re

        # 1. 提取已定义的变量
        var_pattern = r'\[DEFINE_VARIABLES:\](.*?)\[END_VARIABLES\]'
        var_match = re.search(var_pattern, code, re.DOTALL)
        defined_vars = set()

        if var_match:
            var_content = var_match.group(1)
            var_defs = re.findall(r'(?:^|\n)\s*(?:\"[^\"]*\"\s+)?(\w+)\s*:', var_content)
            defined_vars.update(var_defs)

        # 2. 提取所有<REF>引用
        ref_pattern = r'<REF>\*?(\w+)</REF>'
        refs = re.findall(ref_pattern, code)

        # 3. 找出未定义的变量
        undefined_refs = set(refs) - defined_vars

        if not undefined_refs:
            return code  # 没有未定义的变量

        logger.info(f"Auto-fixing {len(undefined_refs)} undefined variables: {undefined_refs}")

        # 4. 推断变量类型（基于名称启发式）
        def infer_type(var_name: str) -> str:
            name_lower = var_name.lower()
            if 'number' in name_lower or 'count' in name_lower or 'id' in name_lower or var_name.endswith('_num'):
                return 'number'
            elif 'bool' in name_lower or 'is_' in name_lower or 'has_' in name_lower or 'can_' in name_lower:
                return 'boolean'
            elif 'image' in name_lower or 'img' in name_lower or 'pic' in name_lower:
                return 'image'
            elif 'audio' in name_lower or 'sound' in name_lower or 'voice' in name_lower:
                return 'audio'
            else:
                return 'text'  # 默认类型

        # 5. 生成变量声明
        new_var_lines = [f'"{var} variable" {var}: {infer_type(var)}' for var in sorted(undefined_refs)]

        # 6. 插入到VARIABLES块
        if var_match:
            # 已有VARIABLES块，在末尾添加
            var_content = var_match.group(1)
            new_var_section = var_content.rstrip() + '\n' + '\n'.join(new_var_lines) + '\n'
            code = code[:var_match.start(1)] + new_var_section + code[var_match.end(1):]
        else:
            # 没有VARIABLES块，创建新的
            new_vars_block = '[DEFINE_VARIABLES:]\n' + '\n'.join(new_var_lines) + '\n[END_VARIABLES]'
            # 插入在WORKER之前
            worker_pos = code.find('[DEFINE_WORKER:')
            if worker_pos > 0:
                code = code[:worker_pos] + new_vars_block + '\n\n' + code[worker_pos:]

        return code