# Utils Knowledge Base

## OVERVIEW
Shared utilities for LLM abstraction and text processing. Stateless functions and async clients used across all pipeline phases.

## STRUCTURE
```
src/utils/
├── llm_client.py      # LLM abstraction layer
├── text_utils.py      # Text processing utilities
└── __init__.py        # Package exports
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Create LLM client | `llm_client.py::create_llm_client()` | Factory with provider/model params |
| Custom LLM provider | `llm_client.py::BaseLLMClient` | Extend ABC, implement `complete()` |
| Retry logic | `llm_client.py::_retry_with_backoff()` | Exponential backoff, handles 429s |
| Text normalization | `text_utils.py::normalize_text()` | Lowercase, strip whitespace |
| Find substring positions | `text_utils.py::find_substring_positions()` | Returns list of (start, end) tuples |
| Calculate overlap | `text_utils.py::calculate_overlap()` | Returns 0.0-1.0 overlap ratio |
| Split sentences | `text_utils.py::split_sentences()` | Chinese and English punctuation aware |

## CONVENTIONS

### LLM Client
- **Factory pattern**: `create_llm_client({"provider": "openai", "api_key": "..."})`
- **Providers**: "openai" or "anthropic" (case-insensitive)
- **Response format**: "text" or "json" (auto-parsed)
- **Exceptions**: `RateLimitError`, `AuthenticationError`, `RetryExhaustedError`

### Text Utilities
- **Pure functions**: No side effects, same input = same output
- **Unicode aware**: Handles Chinese and English text
- **Positions**: All ranges are (start, end) with end exclusive

## ANTI-PATTERNS
- **DO NOT** instantiate `OpenAIClient` or `AnthropicClient` directly, use factory
- **DO NOT** catch generic `Exception` for LLM calls, catch specific `LLMClientError` subclasses
- **NEVER** pass API keys in code, always from config/env
- **AVOID** calling `normalize_text()` repeatedly on same string, cache results
