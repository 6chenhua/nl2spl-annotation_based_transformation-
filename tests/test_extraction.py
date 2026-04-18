"""变量提取与类型推断模块单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.extraction import VariableExtractor, TypeInferencer, TypeCollector
from src.models import (
    VariableInfo, TypedVariable, ComplexTypeDef,
    Annotation, TextSegment, SPLBlockType, ComplexTypeCategory
)


class TestVariableExtractor:
    """测试VariableExtractor"""

    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端"""
        client = MagicMock()
        client.complete = AsyncMock(return_value={
            "variables": [
                {"name": "input_text", "context": "用户输入", "source": "INPUTS"},
                {"name": "output", "context": "分析结果", "source": "OUTPUTS"}
            ]
        })
        return client

    def test_extract_from_inputs_section(self):
        """测试从INPUTS部分提取变量"""
        extractor = VariableExtractor()

        content = """
[INPUTS]
<REF>input_text</REF>
<REF>config</REF>
[END_INPUTS]
"""
        annotation = Annotation(
            block_type=SPLBlockType.WORKER_MAIN_FLOW,
            segments=[TextSegment(content=content, start_pos=0, end_pos=len(content))],
            confidence=0.9,
            extracted_content=content
        )

        import asyncio
        vars_info = asyncio.run(extractor.extract(annotation))

        assert len(vars_info) >= 2
        assert any(v.name == "input_text" for v in vars_info)
        assert any(v.name == "config" for v in vars_info)

    def test_extract_from_results(self):
        """测试从RESULT部分提取变量声明"""
        extractor = VariableExtractor()

        content = """
[MAIN_FLOW]
[COMMAND 分析文本
    RESULT temp_result: AnalysisResult
    SET]
[END_MAIN_FLOW]
"""
        annotation = Annotation(
            block_type=SPLBlockType.WORKER_MAIN_FLOW,
            segments=[TextSegment(content=content, start_pos=0, end_pos=len(content))],
            confidence=0.9,
            extracted_content=content
        )

        import asyncio
        vars_info = asyncio.run(extractor.extract(annotation))

        assert any(v.name == "temp_result" for v in vars_info)


class TestTypeInferencer:
    """测试TypeInferencer"""

    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端"""
        client = MagicMock()
        return client

    def test_infer_text_type(self, mock_llm_client):
        """测试推断text类型"""
        inferencer = TypeInferencer(mock_llm_client)

        var_info = VariableInfo(
            name="input_text",
            context="用户输入的文本内容",
            source="INPUTS"
        )

        import asyncio
        typed_vars = asyncio.run(inferencer.infer([var_info]))

        assert len(typed_vars) == 1
        assert typed_vars[0].name == "input_text"
        assert typed_vars[0].type_name == "text"
        assert typed_vars[0].is_simple_type is True

    def test_infer_number_type(self, mock_llm_client):
        """测试推断number类型"""
        inferencer = TypeInferencer(mock_llm_client)

        var_info = VariableInfo(
            name="score_count",
            context="分数计数",
            source="OUTPUTS"
        )

        import asyncio
        typed_vars = asyncio.run(inferencer.infer([var_info]))

        assert typed_vars[0].type_name == "number"

    def test_infer_array_type(self, mock_llm_client):
        """测试推断数组类型"""
        inferencer = TypeInferencer(mock_llm_client)

        var_info = VariableInfo(
            name="item_list",
            context="项目列表",
            source="OUTPUTS"
        )

        import asyncio
        typed_vars = asyncio.run(inferencer.infer([var_info]))

        assert "List[" in typed_vars[0].type_name


class TestTypeCollector:
    """测试TypeCollector"""

    def test_collect_simple_types(self):
        """测试简单类型不生成复杂类型"""
        collector = TypeCollector()

        typed_vars = [
            TypedVariable(
                name="text_var",
                type_name="text",
                is_simple_type=True,
                needs_type_definition=False,
                original_info=VariableInfo("text_var", "", "")
            ),
            TypedVariable(
                name="num_var",
                type_name="number",
                is_simple_type=True,
                needs_type_definition=False,
                original_info=VariableInfo("num_var", "", "")
            )
        ]

        complex_types = collector.collect(typed_vars)

        assert len(complex_types) == 0

    def test_collect_structured_types(self):
        """测试收集结构化类型"""
        collector = TypeCollector()

        typed_vars = [
            TypedVariable(
                name="result",
                type_name="Struct_result",
                is_simple_type=False,
                needs_type_definition=True,
                original_info=VariableInfo("result", "分析结果", "OUTPUTS")
            )
        ]

        complex_types = collector.collect(typed_vars)

        assert len(complex_types) == 1
        assert complex_types[0].category == ComplexTypeCategory.STRUCTURED
        assert "Result" in complex_types[0].name

    def test_collect_enum_types(self):
        """测试收集枚举类型"""
        collector = TypeCollector()

        typed_vars = [
            TypedVariable(
                name="status",
                type_name="Enum_status",
                is_simple_type=False,
                needs_type_definition=True,
                original_info=VariableInfo("status", "状态可以是 [pending, done]", "INPUTS")
            )
        ]

        complex_types = collector.collect(typed_vars)

        assert len(complex_types) == 1
        assert complex_types[0].category == ComplexTypeCategory.ENUM


class TestExtractionIntegration:
    """集成测试：完整提取流程"""

    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端"""
        client = MagicMock()
        client.complete = AsyncMock(return_value={
            "variables": [],
            "refined_types": []
        })
        return client

    def test_full_extraction_pipeline(self, mock_llm_client):
        """测试完整提取流程"""
        # 模拟Worker标注
        worker_content = """
[INPUTS]
<REF>input_text</REF>
<REF>config</REF>
[END_INPUTS]

[OUTPUTS]
<REF>result</REF>
[END_OUTPUTS]

[MAIN_FLOW]
[COMMAND 分析
    RESULT temp_var: text
    SET]
[END_MAIN_FLOW]
"""
        annotation = Annotation(
            block_type=SPLBlockType.WORKER_MAIN_FLOW,
            segments=[TextSegment(content=worker_content, start_pos=0, end_pos=len(worker_content))],
            confidence=0.9,
            extracted_content=worker_content
        )

        # 1. 提取变量
        extractor = VariableExtractor(mock_llm_client)
        import asyncio
        var_infos = asyncio.run(extractor.extract(annotation))

        # 2. 推断类型
        inferencer = TypeInferencer(mock_llm_client)
        typed_vars = asyncio.run(inferencer.infer(var_infos))

        # 3. 收集复杂类型
        collector = TypeCollector()
        complex_types = collector.collect(typed_vars)

        # 验证流程完成
        assert len(var_infos) > 0
        assert len(typed_vars) > 0
        # 简单类型不生成complex_types

    def test_extraction_with_complex_types(self, mock_llm_client):
        """测试包含复杂类型的提取"""
        worker_content = """
[INPUTS]
<REF>input_data</REF>
[END_INPUTS]

[OUTPUTS]
<REF>analysis_result</REF>
[END_OUTPUTS]
"""
        annotation = Annotation(
            block_type=SPLBlockType.WORKER_MAIN_FLOW,
            segments=[TextSegment(content=worker_content, start_pos=0, end_pos=len(worker_content))],
            confidence=0.9,
            extracted_content=worker_content
        )

        extractor = VariableExtractor(mock_llm_client)
        import asyncio
        var_infos = asyncio.run(extractor.extract(annotation))

        # 应该提取到变量
        assert len(var_infos) >= 2
        assert any(v.name == "input_data" for v in var_infos)
        assert any(v.name == "analysis_result" for v in var_infos)
