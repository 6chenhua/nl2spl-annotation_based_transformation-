"""标注器单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.annotators import (
    PersonaAnnotator, AudienceAnnotator, ConceptsAnnotator,
    ConstraintsAnnotator, WorkerAnnotator
)
from src.models import SPLBlockType


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端"""
    client = MagicMock()
    client.complete = AsyncMock(return_value={
        "segments": [
            {
                "content": "你是一个专业的AI助手",
                "relevance": "high",
                "reason": "这是角色定义"
            }
        ]
    })
    return client


@pytest.mark.asyncio
async def test_persona_annotator(mock_llm_client):
    """测试Persona标注器"""
    annotator = PersonaAnnotator(mock_llm_client)
    
    assert annotator.block_type == SPLBlockType.PERSONA
    
    result = await annotator.annotate("你是一个专业的AI助手")
    
    assert result.block_type == SPLBlockType.PERSONA
    assert len(result.segments) > 0
    mock_llm_client.complete.assert_called_once()


@pytest.mark.asyncio
async def test_audience_annotator(mock_llm_client):
    """测试Audience标注器"""
    annotator = AudienceAnnotator(mock_llm_client)
    
    assert annotator.block_type == SPLBlockType.AUDIENCE
    
    result = await annotator.annotate("面向初学者用户")
    
    assert result.block_type == SPLBlockType.AUDIENCE


@pytest.mark.asyncio
async def test_worker_annotator(mock_llm_client):
    """测试Worker标注器"""
    annotator = WorkerAnnotator(mock_llm_client)
    
    assert annotator.block_type == SPLBlockType.WORKER_MAIN_FLOW


if __name__ == "__main__":
    pytest.main([__file__, "-v"])