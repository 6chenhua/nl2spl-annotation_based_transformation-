#!/usr/bin/env python3
"""测试输出管理器功能"""

import sys
sys.path.insert(0, '.')

from src.output_manager import OutputManager
from src.models import (
    Annotation, Conflict, TextSegment, SPLBlockType,
    TypedVariable, ComplexTypeDef, ComplexTypeCategory, VariableInfo
)
from datetime import datetime


def test_output_manager():
    """测试输出管理器的各项功能"""

    print("=" * 80)
    print("测试 OutputManager - 中间结果保存功能")
    print("=" * 80)

    # 1. 测试初始化
    print("\n[1/8] 测试初始化...")
    manager = OutputManager(
        base_dir="output",
        case_name="test_case_001",
        save_intermediate=True,
        pretty_print=True
    )
    print(f"[OK] 输出目录: {manager.get_output_dir()}")
    print(f"[OK] 案例名称: {manager.get_case_name()}")

    # 2. 测试 Phase 1: 标注结果
    print("\n[2/8] 测试 Phase 1 - 标注结果保存...")
    annotations = {
        SPLBlockType.PERSONA: Annotation(
            block_type=SPLBlockType.PERSONA,
            segments=[TextSegment(content="AI助手", start_pos=0, end_pos=4, source="persona_annotator")],
            confidence=0.95,
            extracted_content="AI助手"
        ),
        SPLBlockType.AUDIENCE: Annotation(
            block_type=SPLBlockType.AUDIENCE,
            segments=[TextSegment(content="开发者", start_pos=5, end_pos=8, source="audience_annotator")],
            confidence=0.88,
            extracted_content="开发者"
        )
    }
    manager.save_phase1_annotations(annotations, "创建一个AI助手，面向开发者")
    print("[OK] Phase 1 结果已保存")

    # 3. 测试 Phase 2: 变量提取
    print("\n[3/8] 测试 Phase 2 - 变量提取结果保存...")
    var_info = VariableInfo(name="user_input", context="用户输入", source="INPUTS")
    typed_vars = [
        TypedVariable(
            name="user_input",
            type_name="text",
            is_simple_type=True,
            needs_type_definition=False,
            original_info=var_info,
            confidence=0.92
        )
    ]
    complex_types = [
        ComplexTypeDef(
            name="AnalysisResult",
            category=ComplexTypeCategory.STRUCTURED,
            definition="AnalysisResult { score: number; summary: text; }",
            description="分析结果类型"
        )
    ]
    manager.save_phase2_extraction(typed_vars, complex_types, "测试输入")
    print("[OK] Phase 2 结果已保存")

    # 4. 测试 Phase 3: TYPES生成
    print("\n[4/8] 测试 Phase 3 - TYPES生成结果保存...")
    types_block = "[TYPES]\nAnalysisResult = Structured { score: number; summary: text; }\n[/TYPES]"
    manager.save_phase3_types(types_block, "测试输入")
    print("[OK] Phase 3 结果已保存")

    # 5. 测试 Phase 4: 冲突检测
    print("\n[5/8] 测试 Phase 4 - 冲突检测结果保存...")
    conflicts = [
        Conflict(
            segments=[TextSegment(content="AI助手功能", start_pos=0, end_pos=6, source="annotator_a")],
            candidate_labels=[SPLBlockType.PERSONA, SPLBlockType.WORKER_MAIN_FLOW],
            confidence_scores={SPLBlockType.PERSONA: 0.7, SPLBlockType.WORKER_MAIN_FLOW: 0.6}
        )
    ]
    clean_annotations = {k: v for k, v in annotations.items()}
    manager.save_phase4_conflicts(conflicts, clean_annotations, "测试输入")
    print("[OK] Phase 4 结果已保存")

    # 6. 测试 Phase 5: 澄清历史
    print("\n[6/8] 测试 Phase 5 - 澄清历史保存...")
    clarification_history = [
        {
            "question_index": 0,
            "conflict_segments": ["AI助手功能"],
            "candidate_labels": ["persona", "worker_main_flow"],
            "user_response": "1",
            "is_other": False,
            "resolved_label": "persona",
            "success": True
        }
    ]
    manager.save_phase5_clarification(clarification_history, clean_annotations, "测试输入")
    print("[OK] Phase 5 结果已保存")

    # 7. 测试 Phase 6: SPL块生成
    print("\n[7/8] 测试 Phase 6 - SPL块生成结果保存...")
    spl_blocks = {
        SPLBlockType.PERSONA: "[PERSONA]\n你是专业的AI助手\n[/PERSONA]",
        SPLBlockType.AUDIENCE: "[AUDIENCE]\n面向开发者\n[/AUDIENCE]",
        SPLBlockType.TYPES: types_block
    }
    manager.save_phase6_spl_blocks(spl_blocks, "测试输入")
    print("[OK] Phase 6 结果已保存")

    # 8. 测试 Phase 7: 最终SPL
    print("\n[8/8] 测试 Phase 7 - 最终SPL保存...")
    spl_code = """[DEFINE_AGENT TestAgent]

[PERSONA]
你是专业的AI助手
[/PERSONA]

[AUDIENCE]
面向开发者
[/AUDIENCE]

[TYPES]
AnalysisResult = Structured { score: number; summary: text; }
[/TYPES]

[END_AGENT]"""
    manager.finalize(spl_code, "创建一个AI助手，面向开发者")
    print("[OK] Phase 7 结果已保存")

    print("\n" + "=" * 80)
    print("测试完成!")
    print(f"输出目录: {manager.get_output_dir()}")
    print("生成的文件列表:")

    import os
    output_dir = manager.get_output_dir()
    if output_dir.exists():
        for file in sorted(output_dir.iterdir()):
            size = file.stat().st_size
            print(f"  - {file.name} ({size} bytes)")

    print("=" * 80)


def test_from_config():
    """测试从配置创建输出管理器"""
    print("\n" + "=" * 80)
    print("测试从配置创建 OutputManager")
    print("=" * 80)

    config = {
        "output": {
            "enabled": True,
            "base_dir": "output",
            "case_name": "test_from_config",
            "save_intermediate": True,
            "pretty_print": True
        }
    }

    from src.output_manager import create_output_manager

    manager = create_output_manager(config)
    if manager:
        print(f"[OK] 从配置成功创建 OutputManager")
        print(f"  - 输出目录: {manager.get_output_dir()}")
        print(f"  - 案例名称: {manager.get_case_name()}")
    else:
        print("[FAIL] 输出管理器创建失败或被禁用")

    # 测试禁用输出
    config_disabled = {"output": {"enabled": False}}
    manager_disabled = create_output_manager(config_disabled)
    if manager_disabled is None:
        print("[OK] 禁用输出功能正常")
    else:
        print("[FAIL] 禁用输出功能异常")


if __name__ == "__main__":
    test_output_manager()
    test_from_config()
    print("\n所有测试完成!")
