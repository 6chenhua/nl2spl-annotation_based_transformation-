# Annotators Module

## OVERVIEW
Phase 1 of the pipeline. Extracts content from natural language prompts and assigns to SPL block types.

## STRUCTURE
```
annotators/
├── base.py                  # BlockAnnotator ABC (139 lines)
├── persona_annotator.py     # PERSONA block extraction
├── audience_annotator.py   # AUDIENCE block extraction
├── concepts_annotator.py   # CONCEPTS block extraction
├── constraints_annotator.py # CONSTRAINTS block extraction
├── variables_annotator.py  # VARIABLES block extraction
├── worker_annotator.py     # WORKER_MAIN_FLOW extraction
└── __init__.py             # Package exports
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new block type | `base.py` + new file | Inherit from BlockAnnotator |
| Modify extraction logic | `{block}_annotator.py` | Edit `_get_system_prompt()` or `_parse_response()` |
| Change confidence calc | `base.py::_calculate_confidence()` | Default heuristic in base class |
| Position matching | `base.py::_find_position()` | Exact + fuzzy regex matching |
| Export new annotator | `__init__.py` | Add to `__all__` |

## CONVENTIONS

### Required Implementation
Every annotator must implement:
- `_block_type`: Returns `SPLBlockType.XXX` enum value
- `_get_system_prompt()`: Returns LLM prompt string defining block semantics
- `_parse_response()`: Parses LLM JSON response into `List[TextSegment]`

### Response Format
All annotators expect LLM to return JSON with `segments` array:
```json
{
  "segments": [
    {"content": "...", "aspect_type": "...", "reason": "..."}
  ]
}
```

### Position Tracking
Always call `self._find_position(content, original_prompt)` to compute `(start_pos, end_pos)` for each segment. Returns `(-1, -1)` if not found.

## ANTI-PATTERNS
- **DO NOT** skip calling `_find_position()` - segments need valid positions for conflict detection
- **DO NOT** modify `original_prompt` before position lookup - fuzzy matching relies on original text
- **NEVER** return `TextSegment` with empty content - filter in `_parse_response()`
- **AVOID** overriding `annotate()` - use `_get_system_prompt()` and `_parse_response()` instead
- **DO NOT** hardcode block type strings - always use `SPLBlockType` enum
