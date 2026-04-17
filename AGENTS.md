# Annotated NL2SPL Knowledge Base

**Generated:** 2025-04-17

## OVERVIEW

Multi-agent pipeline for converting Natural Language to SPL (Structured Prompt Language). 5-phase architecture: parallel annotation → conflict detection → human clarification → code generation → merge validation.

## STRUCTURE

```
annotated_nl2spl/
├── src/
│   ├── annotators/         # Phase 1: SPL block annotators (8 modules)
│   ├── conflict_resolution/ # Phase 2: Semantic matching & clustering (4 modules)
│   ├── clarification/       # Phase 3: Human-in-the-loop UI (4 modules)
│   ├── generators/          # Phase 4: SPL code generators (4 modules)
│   ├── utils/               # Shared utilities (LLM client, text tools)
│   ├── models.py            # Core data models (Annotation, Conflict, etc.)
│   └── pipeline.py          # Main orchestrator (275 lines)
├── configs/                 # YAML configuration
├── prompts/                 # LLM prompt templates
├── tests/                   # Test suite (e2e + unit + integration)
├── examples/                # Usage examples
└── docs/                    # Documentation
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new SPL block | `src/annotators/`, `src/generators/` | Implement base class pattern |
| Fix conflict detection | `src/conflict_resolution/semantic_matcher.py` | Uses sentence-transformers + DBSCAN |
| UI customization | `src/clarification/clarification_ui.py` | ConsoleUI base class |
| Pipeline config | `configs/pipeline.yaml` | All phase settings |
| Run tests | `tests/e2e_test.py`, `tests/test_annotators.py` | Requires API key |
| Entry point | `src/pipeline.py::Pipeline` | Main `convert()` method |

## CONVENTIONS

### Code Organization
- **One block = one annotator + one generator**: Each SPL block type has parallel implementations
- **Async-first**: All LLM calls use `async/await`
- **Base class pattern**: `BlockAnnotator` (ABC), `BlockGenerator` (ABC)
- **Dataclass models**: All domain objects are `@dataclass` in `models.py`

### Naming
- **Files**: `snake_case.py`
- **Classes**: `PascalCase` (e.g., `PersonaAnnotator`, `ConflictDetector`)
- **SPL blocks**: `SCREAMING_SNAKE_CASE` enum in `SPLBlockType`

### Dependencies
- **LLM**: OpenAI/Anthropic SDK via `src/utils/llm_client.py`
- **Embeddings**: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Config**: YAML with `pyyaml`

## ANTI-PATTERNS

- **DO NOT** call LLM synchronously - use `await` consistently
- **NEVER** import `annotators` directly from generators - use `models.py` abstractions
- **ALWAYS** use `SPLBlockType` enum instead of raw strings for block types
- **AVOID** modifying `models.py` without updating all dependent phases

## COMMANDS

```bash
# Run end-to-end test
python tests/e2e_test.py

# Run specific test file
python -m pytest tests/test_annotators.py -v

# Simple API test
python test_api.py

# Install dependencies
pip install -r requirements.txt
```

## NOTES

- **Hardcoded API key**: `test_api.py` and `e2e_test*.py` contain `sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b`
- **Typo in pipeline**: Line 81 has `VORKER_MAIN_FLOW` (should be `WORKER_MAIN_FLOW`)
- **Empty prompts dir**: Prompt templates not yet migrated from `DEVELOPMENT_PLAN.md`
- **Phase 5 validation**: Currently placeholder - no actual SPL syntax validation
- **Deep module nesting**: annotators/ has 8 files with interdependent prompt logic
