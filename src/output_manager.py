"""输出管理器 - 负责保存中间结果和最终SPL

提供统一的文件输出管理，支持：
- 自动创建输出目录结构
- 保存各阶段中间结果为JSON格式
- 保存最终SPL代码为.spl文件
- 支持自定义案例名称
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict, is_dataclass
from enum import Enum

from .models import (
    Annotation, Conflict, ClarificationQuestion,
    TypedVariable, ComplexTypeDef, SPLBlockType
)

logger = logging.getLogger(__name__)


class DataclassEncoder(json.JSONEncoder):
    """自定义JSON编码器，支持dataclass和Enum"""

    def default(self, obj):
        if is_dataclass(obj):
            result = asdict(obj)
            # 递归处理字典中的枚举键
            return self._convert_enum_keys(result)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

    def _convert_enum_keys(self, obj):
        """递归转换字典中的枚举键为字符串"""
        if isinstance(obj, dict):
            return {key.value if isinstance(key, Enum) else key: self._convert_enum_keys(value)
                    for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_enum_keys(item) for item in obj]
        elif isinstance(obj, Enum):
            return obj.value
        return obj


class OutputManager:
    """输出管理器

    负责管理所有中间结果和最终输出的文件保存。
    输出目录结构：
    output/
    └── {case_name}/
        ├── phase1_annotations.json    # Phase 1: 块标注结果
        ├── phase2_extraction.json     # Phase 2: 变量提取结果
        ├── phase3_types.json          # Phase 3: TYPES生成结果
        ├── phase4_conflicts.json      # Phase 4: 冲突检测结果
        ├── phase5_clarification.json  # Phase 5: 澄清历史
        ├── phase6_spl_blocks.json     # Phase 6: 各SPL块生成结果
        ├── metadata.json              # 元数据（时间戳、配置等）
        └── final.spl                 # 最终合并的SPL代码
    """

    def __init__(
        self,
        base_dir: str = "output",
        case_name: Optional[str] = None,
        save_intermediate: bool = True,
        pretty_print: bool = True
    ):
        """初始化输出管理器

        Args:
            base_dir: 输出基础目录
            case_name: 案例名称，如果为None则自动生成时间戳
            save_intermediate: 是否保存中间结果
            pretty_print: JSON是否美化输出
        """
        self.base_dir = Path(base_dir)
        self.case_name = case_name or self._generate_case_name()
        self.save_intermediate = save_intermediate
        self.pretty_print = pretty_print

        # 构建完整输出路径
        self.output_dir = self.base_dir / self.case_name

        # 元数据
        self.metadata: Dict[str, Any] = {
            "case_name": self.case_name,
            "created_at": datetime.now().isoformat(),
            "phases_completed": []
        }

        # 确保输出目录存在
        self._ensure_output_dir()
        logger.info(f"Output directory initialized: {self.output_dir}")

    def _generate_case_name(self) -> str:
        """生成默认案例名称（时间戳格式）"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save_json(self, filename: str, data: Dict, indent: int = 2) -> Path:
        """保存数据为JSON文件

        Args:
            filename: 文件名
            data: 要保存的数据
            indent: JSON缩进

        Returns:
            保存的文件路径
        """
        filepath = self.output_dir / filename

        if self.pretty_print:
            json_str = json.dumps(data, cls=DataclassEncoder, indent=indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, cls=DataclassEncoder, ensure_ascii=False)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_str)

        logger.debug(f"Saved: {filepath}")
        return filepath

    def _save_text(self, filename: str, content: str) -> Path:
        """保存文本内容

        Args:
            filename: 文件名
            content: 文本内容

        Returns:
            保存的文件路径
        """
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.debug(f"Saved: {filepath}")
        return filepath

    def save_phase1_annotations(
        self,
        annotations: Dict[SPLBlockType, Annotation],
        original_prompt: str
    ) -> Optional[Path]:
        """保存Phase 1: 块标注结果

        Args:
            annotations: 标注结果字典
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径，如果未启用则返回None
        """
        if not self.save_intermediate:
            return None

        data = {
            "phase": "phase1_annotation",
            "original_prompt": original_prompt,
            "annotations": {
                block_type.value: annotation
                for block_type, annotation in annotations.items()
            }
        }

        filepath = self._save_json("phase1_annotations.json", data)
        self.metadata["phases_completed"].append("phase1")
        logger.info(f"Phase 1 annotations saved to {filepath}")
        return filepath

    def save_phase2_extraction(
        self,
        typed_vars: List[TypedVariable],
        complex_types: List[ComplexTypeDef],
        original_prompt: str
    ) -> Optional[Path]:
        """保存Phase 2: 变量提取与类型推断结果

        Args:
            typed_vars: 带类型的变量列表
            complex_types: 复杂类型定义列表
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径，如果未启用则返回None
        """
        if not self.save_intermediate:
            return None

        data = {
            "phase": "phase2_extraction",
            "original_prompt": original_prompt,
            "typed_variables": typed_vars,
            "complex_types": complex_types,
            "stats": {
                "total_variables": len(typed_vars),
                "total_complex_types": len(complex_types)
            }
        }

        filepath = self._save_json("phase2_extraction.json", data)
        self.metadata["phases_completed"].append("phase2")
        logger.info(f"Phase 2 extraction saved to {filepath}")
        return filepath

    def save_phase3_types(
        self,
        types_block: str,
        original_prompt: str
    ) -> Optional[Path]:
        """保存Phase 3: TYPES生成结果

        Args:
            types_block: TYPES块代码
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径，如果未启用则返回None
        """
        if not self.save_intermediate:
            return None

        data = {
            "phase": "phase3_types_generation",
            "original_prompt": original_prompt,
            "types_block": types_block,
            "stats": {
                "block_length": len(types_block) if types_block else 0,
                "has_types": bool(types_block)
            }
        }

        filepath = self._save_json("phase3_types.json", data)
        self.metadata["phases_completed"].append("phase3")
        logger.info(f"Phase 3 types saved to {filepath}")
        return filepath

    def save_phase4_conflicts(
        self,
        conflicts: List[Conflict],
        clean_annotations: Dict[SPLBlockType, Annotation],
        original_prompt: str
    ) -> Optional[Path]:
        """保存Phase 4: 冲突检测结果

        Args:
            conflicts: 冲突列表
            clean_annotations: 清理后的标注
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径，如果未启用则返回None
        """
        if not self.save_intermediate:
            return None

        data = {
            "phase": "phase4_conflict_detection",
            "original_prompt": original_prompt,
            "conflicts": conflicts,
            "clean_annotations": {
                block_type.value: annotation
                for block_type, annotation in clean_annotations.items()
            },
            "stats": {
                "total_conflicts": len(conflicts),
                "total_clean_annotations": len(clean_annotations)
            }
        }

        filepath = self._save_json("phase4_conflicts.json", data)
        self.metadata["phases_completed"].append("phase4")
        logger.info(f"Phase 4 conflicts saved to {filepath}")
        return filepath

    def save_phase5_clarification(
        self,
        clarification_history: List[Dict[str, Any]],
        final_annotations: Dict[SPLBlockType, Annotation],
        original_prompt: str
    ) -> Optional[Path]:
        """保存Phase 5: 澄清历史

        Args:
            clarification_history: 澄清历史记录
            final_annotations: 最终标注结果
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径，如果未启用则返回None
        """
        if not self.save_intermediate:
            return None

        data = {
            "phase": "phase5_clarification",
            "original_prompt": original_prompt,
            "clarification_history": clarification_history,
            "final_annotations": {
                block_type.value: annotation
                for block_type, annotation in final_annotations.items()
            },
            "stats": {
                "total_clarifications": len(clarification_history),
                "total_final_annotations": len(final_annotations)
            }
        }

        filepath = self._save_json("phase5_clarification.json", data)
        self.metadata["phases_completed"].append("phase5")
        logger.info(f"Phase 5 clarification saved to {filepath}")
        return filepath

    def save_phase6_spl_blocks(
        self,
        spl_blocks: Dict[SPLBlockType, str],
        original_prompt: str
    ) -> Optional[Path]:
        """保存Phase 6: 各SPL块生成结果

        Args:
            spl_blocks: SPL块代码字典
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径，如果未启用则返回None
        """
        if not self.save_intermediate:
            return None

        data = {
            "phase": "phase6_generation",
            "original_prompt": original_prompt,
            "spl_blocks": {
                block_type.value: code
                for block_type, code in spl_blocks.items()
            },
            "stats": {
                "total_blocks": len(spl_blocks),
                "block_lengths": {
                    block_type.value: len(code) if code else 0
                    for block_type, code in spl_blocks.items()
                }
            }
        }

        filepath = self._save_json("phase6_spl_blocks.json", data)
        self.metadata["phases_completed"].append("phase6")
        logger.info(f"Phase 6 SPL blocks saved to {filepath}")
        return filepath

    def save_final_spl(self, spl_code: str, original_prompt: str) -> Path:
        """保存最终SPL代码

        Args:
            spl_code: 最终SPL代码
            original_prompt: 原始输入提示

        Returns:
            保存的文件路径
        """
        # 保存为.spl文件
        spl_filepath = self._save_text("final.spl", spl_code)

        # 同时保存元数据
        self.metadata["final_spl"] = {
            "file": "final.spl",
            "code_length": len(spl_code),
            "line_count": len(spl_code.split('\n'))
        }
        self.metadata["phases_completed"].append("phase7")

        logger.info(f"Final SPL saved to {spl_filepath}")
        return spl_filepath

    def finalize(self, spl_code: str, original_prompt: str):
        """完成输出，保存元数据和最终SPL

        Args:
            spl_code: 最终SPL代码
            original_prompt: 原始输入提示
        """
        # 更新元数据
        self.metadata["original_prompt"] = original_prompt
        self.metadata["completed_at"] = datetime.now().isoformat()
        self.metadata["total_phases"] = len(self.metadata["phases_completed"])

        # 保存元数据
        metadata_path = self._save_json("metadata.json", self.metadata)

        # 保存最终SPL
        spl_path = self.save_final_spl(spl_code, original_prompt)

        logger.info(f"Output finalized. Files saved to: {self.output_dir}")
        logger.info(f"  - Metadata: {metadata_path}")
        logger.info(f"  - SPL: {spl_path}")

    def get_output_dir(self) -> Path:
        """获取输出目录路径"""
        return self.output_dir

    def get_case_name(self) -> str:
        """获取案例名称"""
        return self.case_name


# 便捷函数：从配置创建OutputManager
def create_output_manager(config: Dict[str, Any]) -> Optional[OutputManager]:
    """从配置字典创建OutputManager

    Args:
        config: 配置字典，应包含output部分

    Returns:
        OutputManager实例，如果输出被禁用则返回None
    """
    output_config = config.get('output', {})

    if not output_config.get('enabled', True):
        logger.info("Output saving is disabled in config")
        return None

    return OutputManager(
        base_dir=output_config.get('base_dir', 'output'),
        case_name=output_config.get('case_name'),
        save_intermediate=output_config.get('save_intermediate', True),
        pretty_print=output_config.get('pretty_print', True)
    )
