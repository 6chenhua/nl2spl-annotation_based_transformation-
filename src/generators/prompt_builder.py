# -*- coding: utf-8 -*-
"""SPL Prompt Builder

根据EBNF语法构建生成器的system prompt。
Prompt内容从prompts目录下的文件中加载。
"""

import os
from ..models import SPLBlockType


class SPLPromptBuilder:
    """基于EBNF语法的SPL Prompt构建器"""

    # Cache for loaded prompts
    _prompt_cache: dict = {}

    @staticmethod
    def _get_prompts_dir() -> str:
        """获取prompts目录的路径"""
        # Get the project root directory (parent of src)
        current_file = os.path.abspath(__file__)
        src_dir = os.path.dirname(os.path.dirname(current_file))
        project_root = os.path.dirname(src_dir)
        return os.path.join(project_root, 'prompts')

    @staticmethod
    def _load_prompt(filename: str) -> str:
        """从文件加载prompt内容"""
        if filename in SPLPromptBuilder._prompt_cache:
            return SPLPromptBuilder._prompt_cache[filename]

        prompts_dir = SPLPromptBuilder._get_prompts_dir()
        filepath = os.path.join(prompts_dir, filename)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                SPLPromptBuilder._prompt_cache[filename] = content
                return content
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {filepath}")
        except Exception as e:
            raise RuntimeError(f"Failed to load prompt file {filepath}: {e}")

    @staticmethod
    def get_system_prompt(block_type: SPLBlockType) -> str:
        """获取指定块的system prompt"""

        prompt_files = {
            SPLBlockType.PERSONA: 'persona_generator.md',
            SPLBlockType.AUDIENCE: 'audience_generator.md',
            SPLBlockType.CONCEPTS: 'concepts_generator.md',
            SPLBlockType.CONSTRAINTS: 'constraints_generator.md',
            SPLBlockType.VARIABLES: 'variables_generator.md',
            SPLBlockType.WORKER_MAIN_FLOW: 'worker_generator.md',
        }

        if block_type in prompt_files:
            return SPLPromptBuilder._load_prompt(prompt_files[block_type])
        else:
            raise ValueError(f"Unknown block type: {block_type}")


def get_block_prompt(block_type: SPLBlockType) -> str:
    """获取指定SPL块的生成prompt"""
    return SPLPromptBuilder.get_system_prompt(block_type)
