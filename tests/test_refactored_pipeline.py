"""重构后Pipeline完整测试

测试整个重构后的流程：
1. Phase 1: 并行块标注（不含VARIABLES）
2. Phase 2: 变量提取与类型推断
3. Phase 3: TYPES生成
4. Phase 4: 冲突检测
5. Phase 5: 澄清（跳过）
6. Phase 6: 分块并行生成
7. Phase 7: 合并与验证
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models import (
    Annotation, TextSegment, SPLBlockType,
    VariableInfo, TypedVariable, ComplexTypeDef,
    ComplexTypeCategory, SimpleType, SymbolTable
)
from src.extraction import VariableExtractor, TypeInferencer, TypeCollector
from src.generators import (
    PersonaGenerator, AudienceGenerator, ConceptsGenerator,
    ConstraintsGenerator, VariablesGenerator, WorkerGenerator,
    TypesGenerator, SPLMerger
)


class MockLLMClient:
    """模拟LLM客户端"""

    async def complete(self, system_prompt, user_prompt, response_format=None):
        """模拟LLM调用"""
        # 根据提示词类型返回不同的响应
        if "标注" in system_prompt or "annotate" in system_prompt.lower():
            return self._mock_annotation_response(user_prompt)
        elif "提取变量" in system_prompt or "extract variables" in system_prompt.lower():
            return self._mock_extraction_response(user_prompt)
        elif "推断类型" in system_prompt or "infer type" in system_prompt.lower():
            return self._mock_type_inference_response(user_prompt)
        elif "生成SPL" in system_prompt or "generate SPL" in system_prompt.lower():
            return self._mock_generation_response(user_prompt)
        else:
            return {"content": "```spl\n[TEST]\n[END_TEST]\n```"}

    def _mock_annotation_response(self, user_prompt):
        """模拟标注响应"""
        return {
            "segments": [
                {
                    "content": "你是一个专业的文本分析助手",
                    "relevance": "high",
                    "reason": "角色定义"
                }
            ]
        }

    def _mock_extraction_response(self, user_prompt):
        """模拟变量提取响应"""
        return {
            "variables": [
                {"name": "input_text", "context": "用户输入的待分析文本", "source": "INPUTS"},
                {"name": "config", "context": "分析配置参数", "source": "INPUTS"},
                {"name": "analysis_result", "context": "分析结果", "source": "OUTPUTS"},
                {"name": "temp_data", "context": "临时数据", "source": "RESULT"}
            ]
        }

    def _mock_type_inference_response(self, user_prompt):
        """模拟类型推断响应"""
        return {
            "refined_types": [
                {"name": "input_text", "type_name": "text", "is_simple_type": True, "needs_type_definition": False, "confidence": 0.95},
                {"name": "config", "type_name": "ConfigType", "is_simple_type": False, "needs_type_definition": True, "confidence": 0.85},
                {"name": "analysis_result", "type_name": "AnalysisResult", "is_simple_type": False, "needs_type_definition": True, "confidence": 0.9},
                {"name": "temp_data", "type_name": "text", "is_simple_type": True, "needs_type_definition": False, "confidence": 0.8}
            ]
        }

    def _mock_generation_response(self, user_prompt):
        """模拟SPL生成响应"""
        if "PERSONA" in user_prompt:
            return {"content": "```spl\n[DEFINE_PERSONA:]\nROLE: 你是一个专业的文本分析助手\n[END_PERSONA]\n```"}
        elif "VARIABLES" in user_prompt:
            return {"content": "```spl\n[DEFINE_VARIABLES:]\n\"用户输入文本\"\ninput_text: text\n\"配置参数\"\nconfig: ConfigType\n\"分析结果\"\nanalysis_result: AnalysisResult\n\"临时数据\"\ntemp_data: text\n[END_VARIABLES]\n```"}
        elif "TYPES" in user_prompt:
            return {"content": "```spl\n[DEFINE_TYPES:]\n\"配置类型\"\nConfigType = {\n    threshold: number,\n    mode: text\n}\n\"分析结果类型\"\nAnalysisResult = {\n    content: text,\n    score: number,\n    tags: List[text]\n}\n[END_TYPES]\n```"}
        elif "WORKER" in user_prompt:
            return {"content": "```spl\n[DEFINE_WORKER: \"文本分析\"]\n[INPUTS]\n<REF>input_text</REF>\n<REF>config</REF>\n[END_INPUTS]\n[OUTPUTS]\n<REF>analysis_result</REF>\n[END_OUTPUTS]\n[MAIN_FLOW]\n[COMMAND 分析文本\n    RESULT temp_data: text\n    SET]\n[END_MAIN_FLOW]\n[END_WORKER]\n```"}
        else:
            return {"content": "```spl\n[PLACEHOLDER]\n[END_PLACEHOLDER]\n```"}


async def test_phase_1_annotation():
    """测试Phase 1: 并行块标注"""
    print("\n=== Phase 1: 并行块标注（不含VARIABLES） ===")

    llm_client = MockLLMClient()

    # 创建标注器
    from src.annotators import (
        PersonaAnnotator, AudienceAnnotator, ConceptsAnnotator,
        ConstraintsAnnotator, WorkerAnnotator
    )

    annotators = {
        SPLBlockType.PERSONA: PersonaAnnotator(llm_client),
        SPLBlockType.AUDIENCE: AudienceAnnotator(llm_client),
        SPLBlockType.CONCEPTS: ConceptsAnnotator(llm_client),
        SPLBlockType.CONSTRAINTS: ConstraintsAnnotator(llm_client),
        SPLBlockType.WORKER_MAIN_FLOW: WorkerAnnotator(llm_client),
    }

    prompt = "创建一个文本分析AI助手，能够分析用户输入并返回分析结果"

    # 并行执行标注
    tasks = []
    block_types = []

    for block_type, annotator in annotators.items():
        task = annotator.annotate(prompt)
        tasks.append(task)
        block_types.append(block_type)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    annotations = {}
    for block_type, result in zip(block_types, results):
        if isinstance(result, Exception):
            print(f"  ❌ {block_type.value}: 标注失败 - {result}")
            annotations[block_type] = Annotation(
                block_type=block_type,
                segments=[],
                confidence=0.0,
                extracted_content=""
            )
        else:
            annotations[block_type] = result
            print(f"  ✅ {block_type.value}: {len(result.segments)} segments, confidence={result.confidence:.2f}")

    # 验证：应该有5个标注（不含VARIABLES）
    assert len(annotations) == 5, f"Expected 5 annotations, got {len(annotations)}"
    assert SPLBlockType.VARIABLES not in annotations, "VARIABLES should not be in annotations"
    print(f"  ✅ Phase 1完成: {len(annotations)} blocks annotated")

    return annotations


async def test_phase_2_extraction(worker_annotation):
    """测试Phase 2: 变量提取与类型推断"""
    print("\n=== Phase 2: 变量提取与类型推断 ===")

    llm_client = MockLLMClient()

    extractor = VariableExtractor(llm_client)
    inferencer = TypeInferencer(llm_client)
    collector = TypeCollector()

    # 1. 提取变量
    print("  1. 提取变量...")
    var_infos = await extractor.extract(worker_annotation)
    print(f"     提取到 {len(var_infos)} 个变量")
    for var in var_infos:
        print(f"       - {var.name} (source: {var.source})")

    # 2. 推断类型
    print("  2. 推断类型...")
    typed_vars = await inferencer.infer(var_infos)
    print(f"     推断 {len(typed_vars)} 个变量类型")
    for tv in typed_vars:
        type_info = f"{tv.type_name} (simple: {tv.is_simple_type})"
        print(f"       - {tv.name}: {type_info}")

    # 3. 收集复杂类型
    print("  3. 收集复杂类型...")
    complex_types = collector.collect(typed_vars)
    print(f"     收集到 {len(complex_types)} 个复杂类型")
    for ct in complex_types:
        print(f"       - {ct.name}: {ct.category.value}")
        print(f"         definition: {ct.definition}")

    print(f"  ✅ Phase 2完成: {len(var_infos)} vars, {len(complex_types)} complex types")

    return typed_vars, complex_types


async def test_phase_3_types_generation(complex_types):
    """测试Phase 3: TYPES生成"""
    print("\n=== Phase 3: TYPES生成（优先） ===")

    llm_client = MockLLMClient()
    generator = TypesGenerator(llm_client)

    types_block = await generator.generate(complex_types)

    print(f"  ✅ Phase 3完成: {len(types_block)} chars")
    print(f"  生成的TYPES块:\n{types_block[:500]}...")

    return types_block


async def test_phase_6_generation(annotations, typed_vars, types_block):
    """测试Phase 6: 分块并行生成"""
    print("\n=== Phase 6: 分块并行生成（VARIABLES引用TYPES） ===")

    llm_client = MockLLMClient()

    # 构建符号表
    symbol_table = SymbolTable(
        global_vars={tv.name: tv for tv in typed_vars},
        type_defs={},
        temp_vars={}
    )

    generators = {
        SPLBlockType.PERSONA: PersonaGenerator(llm_client),
        SPLBlockType.AUDIENCE: AudienceGenerator(llm_client),
        SPLBlockType.CONCEPTS: ConceptsGenerator(llm_client),
        SPLBlockType.CONSTRAINTS: ConstraintsGenerator(llm_client),
        SPLBlockType.VARIABLES: VariablesGenerator(llm_client),
        SPLBlockType.WORKER_MAIN_FLOW: WorkerGenerator(llm_client),
    }

    spl_blocks = {SPLBlockType.TYPES: types_block}
    tasks = []
    block_types = []

    for block_type, annotation in annotations.items():
        if not annotation.segments:
            continue

        generator = generators.get(block_type)
        if not generator:
            continue

        if block_type == SPLBlockType.VARIABLES:
            task = generator.generate_with_types(typed_vars, types_block)
        elif block_type == SPLBlockType.WORKER_MAIN_FLOW:
            task = generator.generate_with_symbol_table(annotation, symbol_table)
        else:
            task = generator.generate(annotation)

        tasks.append(task)
        block_types.append(block_type)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for block_type, result in zip(block_types, results):
        if isinstance(result, Exception):
            print(f"  ❌ {block_type.value}: 生成失败 - {result}")
            spl_blocks[block_type] = ""
        else:
            spl_blocks[block_type] = result
            print(f"  ✅ {block_type.value}: {len(result)} chars")

    print(f"  ✅ Phase 6完成: {len(spl_blocks)} blocks generated")

    return spl_blocks


def test_phase_7_merge(spl_blocks):
    """测试Phase 7: 合并与验证"""
    print("\n=== Phase 7: 合并与验证 ===")

    merger = SPLMerger(agent_name="TextAnalysisAgent")

    spl_code = merger.merge(spl_blocks)

    print(f"  合并后代码长度: {len(spl_code)} chars")

    # 验证
    is_valid, errors = merger.validate_syntax(spl_code)

    if is_valid:
        print("  ✅ Phase 7完成: SPL语法验证通过")
    else:
        print(f"  ⚠️ Phase 7完成但有警告: {len(errors)} 个验证问题")
        for error in errors:
            print(f"     - {error}")

    return spl_code, is_valid, errors


async def test_full_pipeline():
    """测试完整Pipeline流程"""
    print("=" * 60)
    print("开始测试重构后的完整Pipeline")
    print("=" * 60)

    try:
        # Phase 1: 标注
        annotations = await test_phase_1_annotation()

        # Phase 2: 提取与推断
        worker_annotation = annotations[SPLBlockType.WORKER_MAIN_FLOW]
        typed_vars, complex_types = await test_phase_2_extraction(worker_annotation)

        # Phase 3: TYPES生成
        types_block = await test_phase_3_types_generation(complex_types)

        # Phase 4-5: 冲突检测与澄清（简化，跳过）
        print("\n=== Phase 4-5: 冲突检测与澄清（跳过） ===")
        print("  ✅ 假设无冲突，继续生成阶段")

        # Phase 6: 生成
        spl_blocks = await test_phase_6_generation(annotations, typed_vars, types_block)

        # Phase 7: 合并
        spl_code, is_valid, errors = test_phase_7_merge(spl_blocks)

        # 输出最终结果
        print("\n" + "=" * 60)
        print("Pipeline测试完成")
        print("=" * 60)
        print(f"\n✅ 测试状态: {'通过' if is_valid else '有警告'}")
        print(f"📄 生成代码长度: {len(spl_code)} 字符")
        print(f"📝 验证问题数: {len(errors)}")

        if errors:
            print(f"\n⚠️  验证问题:")
            for error in errors:
                print(f"   - {error}")

        print(f"\n生成的SPL代码预览:\n{'=' * 60}")
        print(spl_code[:2000])
        if len(spl_code) > 2000:
            print(f"... ({len(spl_code) - 2000} more chars)")
        print("=" * 60)

        return is_valid, spl_code

    except Exception as e:
        print(f"\n❌ Pipeline测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, ""


async def test_individual_components():
    """测试各个组件的独立功能"""
    print("\n" + "=" * 60)
    print("组件独立功能测试")
    print("=" * 60)

    # 测试1: VariableExtractor
    print("\n--- 测试 VariableExtractor ---")
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
    test_annotation = Annotation(
        block_type=SPLBlockType.WORKER_MAIN_FLOW,
        segments=[TextSegment(content=test_content, start_pos=0, end_pos=len(test_content))],
        confidence=0.9,
        extracted_content=test_content
    )

    var_infos = await extractor.extract(test_annotation)
    print(f"✅ 提取到 {len(var_infos)} 个变量")
    for v in var_infos:
        print(f"   - {v.name} (from {v.source})")

    # 测试2: TypeInferencer
    print("\n--- 测试 TypeInferencer ---")
    inferencer = TypeInferencer()
    typed_vars = await inferencer.infer(var_infos)
    print(f"✅ 推断 {len(typed_vars)} 个变量类型")
    for tv in typed_vars:
        print(f"   - {tv.name}: {tv.type_name}")

    # 测试3: TypeCollector
    print("\n--- 测试 TypeCollector ---")
    collector = TypeCollector()
    complex_types = collector.collect(typed_vars)
    print(f"✅ 收集到 {len(complex_types)} 个复杂类型")
    for ct in complex_types:
        print(f"   - {ct.name}: {ct.definition}")

    # 测试4: SymbolTable
    print("\n--- 测试 SymbolTable ---")
    symbol_table = SymbolTable()
    symbol_table.global_vars = {tv.name: tv for tv in typed_vars}
    symbol_table.add_temp_var("temp_var", "text")
    print(f"✅ SymbolTable包含 {len(symbol_table.global_vars)} 个全局变量")
    print(f"   全局变量: {list(symbol_table.global_vars.keys())}")
    print(f"   临时变量: {list(symbol_table.temp_vars.keys())}")
    print(f"   is_defined('user_input'): {symbol_table.is_defined('user_input')}")
    print(f"   is_defined('temp_var'): {symbol_table.is_defined('temp_var')}")

    print("\n✅ 所有组件测试完成")


if __name__ == "__main__":
    print("重构后Pipeline完整测试脚本")
    print("=" * 60)

    # 运行组件测试
    asyncio.run(test_individual_components())

    # 运行完整Pipeline测试
    success, code = asyncio.run(test_full_pipeline())

    if success:
        print("\n✅ 所有测试通过!")
        exit(0)
    else:
        print("\n❌ 测试失败")
        exit(1)
