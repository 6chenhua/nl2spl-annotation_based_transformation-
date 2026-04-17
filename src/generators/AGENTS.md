# Generators Knowledge Base

## OVERVIEW
SPL code generators. Each generator produces code for one SPL block type from annotated content.

## STRUCTURE
```
generators/
├── base.py                 # BlockGenerator ABC (103 lines)
├── persona_generator.py    # 6 concrete generators (Persona, Audience, etc.)
├── merger.py               # SPLMerger for block ordering and validation
└── __init__.py             # Package exports
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new block type | `base.py` + new file | Inherit from `BlockGenerator` |
| Fix code extraction | `base.py::_extract_code()` | Regex for code blocks |
| Change block order | `merger.py::BLOCK_ORDER` | Defines output sequence |
| Fix SPL formatting | `merger.py::_format_spl()` | Indentation logic |
| Add validation | `merger.py::validate_syntax()` | Basic bracket/tag checks |
| Customize prompts | `persona_generator.py` | System prompts per block type |

## CONVENTIONS

### Generator Pattern
- `_block_type`: Property returning `SPLBlockType` enum value
- `_get_system_prompt()`: Returns LLM system prompt with SPL syntax rules
- `_build_user_prompt()`: Formats annotation content for LLM
- `generate()`: Async entry point, returns SPL code string

### Code Extraction
- Uses regex `r'```(?:spl)?\n?(.*?)```'` to extract code blocks
- Falls back to full response if no code block found

### Post-Processing
- `_post_process()` removes extra blank lines
- Preserves intentional single blank lines between sections

## BLOCK ORDER (SPLMerger)

```
DEFINE_AGENT (wrapper)
  → PERSONA
  → AUDIENCE
  → CONCEPTS
  → CONSTRAINTS
  → VARIABLES
  → TYPES
  → WORKER_MAIN_FLOW
  → WORKER_EXAMPLE
  → WORKER_FLOW_STEP
END_AGENT
```

## ANTI-PATTERNS

- **DO NOT** parse annotations directly in generators. Use `annotation.extracted_content` only.
- **NEVER** skip `_post_process()`. Raw LLM output often has extra whitespace.
- **AVOID** hardcoding block order outside `BLOCK_ORDER` list. Centralize ordering logic.
- **DO NOT** validate SPL syntax by executing it. Use pattern matching only.
- **NEVER** return partial blocks. Always wrap with complete `[DEFINE_*]` / `[END_*]` tags.
