# -*- coding: utf-8 -*-
"""SPL块生成器"""

from .base import BlockGenerator
from .prompt_builder import get_block_prompt
from ..models import SPLBlockType


class PersonaGenerator(BlockGenerator):
    """PERSONA块生成器"""
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.PERSONA
    
    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.PERSONA)


class AudienceGenerator(BlockGenerator):
    """AUDIENCE块生成器"""
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.AUDIENCE
    
    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.AUDIENCE)


class ConceptsGenerator(BlockGenerator):
    """CONCEPTS块生成器"""
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.CONCEPTS
    
    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.CONCEPTS)


class ConstraintsGenerator(BlockGenerator):
    """CONSTRAINTS块生成器"""
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.CONSTRAINTS
    
    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.CONSTRAINTS)


class VariablesGenerator(BlockGenerator):
    """VARIABLES块生成器"""
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.VARIABLES
    
    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.VARIABLES)


class WorkerGenerator(BlockGenerator):
    """WORKER块生成器"""
    
    @property
    def _block_type(self) -> SPLBlockType:
        return SPLBlockType.WORKER_MAIN_FLOW
    
    def _get_system_prompt(self) -> str:
        return get_block_prompt(SPLBlockType.WORKER_MAIN_FLOW)