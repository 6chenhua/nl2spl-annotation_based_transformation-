# Tests Knowledge Base

## OVERVIEW
Test suite for the Annotated NL2SPL Pipeline using pytest + pytest-asyncio.

## STRUCTURE
```
tests/
├── e2e_test.py          # End-to-end test with real LLM API
├── test_annotators.py   # Annotator unit tests (mocked LLM)
├── integration/         # Integration tests (empty - placeholder)
└── unit/                # Unit tests (empty - placeholder)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Run all tests | `pytest tests/` | Requires API key for e2e |
| Run e2e only | `python tests/e2e_test.py` | Uses real OpenAI API (gpt-4o) |
| Run annotator tests | `pytest tests/test_annotators.py -v` | Mocked LLM client |
| Add new annotator test | `test_annotators.py` | Follow existing `@pytest.mark.asyncio` pattern |
| Mock LLM responses | `test_annotators.py::mock_llm_client` | Returns dict with `segments` key |

## CONVENTIONS

### Test Patterns
- **Async tests**: Use `@pytest.mark.asyncio` decorator
- **Mock LLM**: Use `unittest.mock.AsyncMock` for annotator tests
- **E2E tests**: Use `ProgrammaticUI` (non-interactive) to bypass user input
- **Fixtures**: Define reusable mocks in `@pytest.fixture` functions

### API Key
E2E tests require OpenAI API key (hardcoded in `e2e_test.py`):
```python
api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
```

## ANTI-PATTERNS
- **DO NOT** commit real API keys (current hardcoded key is for dev only)
- **NEVER** run e2e tests in CI without mocking
- **AVOID** testing multiple phases in one test (use integration/ for that)
- **DO NOT** forget `await` in async test assertions
