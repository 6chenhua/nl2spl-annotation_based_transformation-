"""简单测试重构后的代码"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models import (
    VariableInfo, TypedVariable, ComplexTypeDef,
    Annotation, TextSegment, SPLBlockType, ComplexTypeCategory
)
from src.extraction import VariableExtractor, TypeInferencer, TypeCollector
from src.generators import TypesGenerator, SPLMerger
from src.generators.spl_block_generator import VariablesGenerator, WorkerGenerator


class MockLLMClient:
    """模拟LLM客户端"""

    async def complete(self, system_prompt, user_prompt, response_format=None):
        return {"content": "```spl\n[TEST]\n[END_TEST]\n```"}


def test_variable_extractor():
    """测试变量提取"""
    print("Testing VariableExtractor...")

    extractor = VariableExtractor()
    test_content = """
[INPUTS]
<REF>user_input</REF>
<REF>settings</REF>
[END_INPUTS]
[MAIN_FLOW]
[COMMAND 处理 RESULT result: text SET]
[END_MAIN_FLOW]
"""

    annotation = Annotation(
        block_type=SPLBlockType.WORKER_MAIN_FLOW,
        segments=[TextSegment(content=test_content, start_pos=0, end_pos=len(test_content))],
        confidence=0.9,
        extracted_content=test_content
    )

    var_infos = asyncio.run(extractor.extract(annotation))

    print(f"  Extracted {len(var_infos)} variables")
    for v in var_infos:
        print(f"    - {v.name} (from {v.source})")

    # 验证
    assert len(var_infos) >= 3, f"Expected at least 3 variables, got {len(var_infos)}"
    assert any(v.name == "user_input" for v in var_infos), "user_input not found"
    assert any(v.name == "settings" for v in var_infos), "settings not found"
    assert any(v.name == "result" for v in var_infos), "result not found"

    print("  PASS")
    return var_infos


def test_type_inferencer(var_infos):
    """测试类型推断"""
    print("Testing TypeInferencer...")

    inferencer = TypeInferencer()
    typed_vars = asyncio.run(inferencer.infer(var_infos))

    print(f"  Inferred {len(typed_vars)} variable types")
    for tv in typed_vars:
        print(f"    - {tv.name}: {tv.type_name}")

    assert len(typed_vars) == len(var_infos), "Type count mismatch"
    print("  PASS")
    return typed_vars


def test_type_collector(typed_vars):
    """测试类型收集"""
    print("Testing TypeCollector...")

    collector = TypeCollector()
    complex_types = collector.collect(typed_vars)

    print(f"  Collected {len(complex_types)} complex types")
    for ct in complex_types:
        print(f"    - {ct.name}: {ct.category.value}")

    print("  PASS")
    return complex_types


def test_models():
    """测试数据模型"""
    print("Testing data models...")

    # VariableInfo
    var = VariableInfo(name="test", context="test context", source="INPUTS")
    print(f"  VariableInfo: {var.name}")

    # TypedVariable
    typed = TypedVariable(
        name="test",
        type_name="text",
        is_simple_type=True,
        needs_type_definition=False,
        original_info=var
    )
    print(f"  TypedVariable: {typed.name} -> {typed.type_name}")

    # ComplexTypeDef
    complex_type = ComplexTypeDef(
        name="TestType",
        category=ComplexTypeCategory.STRUCTURED,
        definition="{field: text}",
        referenced_by=["var1", "var2"]
    )
    print(f"  ComplexTypeDef: {complex_type.name}")

    # SymbolTable
    from src.models import SymbolTable
    st = SymbolTable()
    st.global_vars["test"] = typed
    st.add_temp_var("temp", "number")

    print(f"  SymbolTable: {len(st.global_vars)} globals, {len(st.temp_vars)} temps")
    assert st.is_defined("test"), "test should be defined"
    assert st.is_defined("temp"), "temp should be defined"
    assert not st.is_defined("undefined"), "undefined should not be defined"

    print("  PASS")


def test_merger():
    """测试SPL合并器"""
    print("Testing SPLMerger...")

    merger = SPLMerger(agent_name="TestAgent")

    # 测试块顺序
    assert merger.BLOCK_ORDER[0] == SPLBlockType.TYPES, "TYPES should be first"
    assert SPLBlockType.VARIABLES in merger.BLOCK_ORDER, "VARIABLES should be in order"
    vars_index = merger.BLOCK_ORDER.index(SPLBlockType.VARIABLES)
    types_index = merger.BLOCK_ORDER.index(SPLBlockType.TYPES)
    assert types_index < vars_index, "TYPES should come before VARIABLES"

    # 测试验证功能
    test_code = """
[DEFINE_AGENT: Test]
[DEFINE_TYPES:]
TestType = {field: text}
[END_TYPES]
[DEFINE_VARIABLES:]
var1: text
var2: TestType
[END_VARIABLES]
[COMMAND test RESULT <REF>var1</REF> SET]
[END_AGENT]
"""
    is_valid, errors = merger.validate_syntax(test_code)
    print(f"  Validation: valid={is_valid}, errors={len(errors)}")
    for e in errors:
        print(f"    - {e}")

    print("  PASS")


def main():
    print("=" * 60)
    print("Refactored Pipeline Component Tests")
    print("=" * 60)
    print()

    try:
        # Test models
        test_models()
        print()

        # Test VariableExtractor
        var_infos = test_variable_extractor()
        print()

        # Test TypeInferencer
        typed_vars = test_type_inferencer(var_infos)
        print()

        # Test TypeCollector
        complex_types = test_type_collector(typed_vars)
        print()

        # Test SPLMerger
        test_merger()
        print()

        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"FAIL: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
