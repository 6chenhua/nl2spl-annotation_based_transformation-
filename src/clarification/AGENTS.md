# Clarification Module

## OVERVIEW
Human-in-the-loop conflict resolution. Translates technical SPL labels into business language questions, collects user answers, maps back to SPLBlockType.

## STRUCTURE
```
src/clarification/
├── question_generator.py   # Creates natural language questions from conflicts
├── clarification_ui.py     # ClarificationUI (ABC) + ConsoleUI + ProgrammaticUI
├── label_mapper.py         # SPLBlockType <-> business language bidirectional mapping
└── __init__.py             # Exports: QuestionGenerator, ClarificationUI, ConsoleUI, LabelMapper
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new question format | `question_generator.py::_generate_question_text()` | Keep under 200 chars display |
| Customize business descriptions | `label_mapper.py::_MAPPINGS` | Update `business_description` field |
| Add Web/API UI | `clarification_ui.py` | Subclass `ClarificationUI`, implement `present_question()` + `collect_response()` |
| Change option format | `label_mapper.py::create_options()` | Controls how choices appear to users |
| Handle custom responses | `label_mapper.py::map_response_to_label()` | Add text matching logic |

## CONVENTIONS

### Business Language Rule
Questions use business concepts, NEVER technical terms. Users never see "SPL", "PERSONA", "WORKER_MAIN_FLOW".

| SPLBlockType | Business Description |
|--------------|---------------------|
| PERSONA | "AI助手的角色定位、性格特征和专业背景" |
| AUDIENCE | "目标用户群体的特征和需求" |
| WORKER_MAIN_FLOW | "AI的工作流程和处理步骤" |

### UI Pattern
- `ClarificationUI` is abstract base with async `resolve_conflicts_batch()`
- `ConsoleUI` for terminal interaction
- `ProgrammaticUI` for API mode (queues questions, accepts pre-set responses)
- Always validate input against valid option IDs

### Question Flow
1. `QuestionGenerator.generate_question()` creates `ClarificationQuestion`
2. `ClarificationUI.present_question()` displays to user
3. `ClarificationUI.collect_response()` gets answer
4. `LabelMapper.map_response_to_label()` converts to `SPLBlockType`

## ANTI-PATTERNS
- **NEVER** expose `SPLBlockType.value` in user-facing text
- **NEVER** use technical abbreviations in questions (no "API", "SPL", "LLM")
- **AVOID** asking yes/no questions about labels. Always provide concrete options
- **DON'T** modify `_MAPPINGS` at runtime without calling `update_mapping()`
- **NEVER** assume response is valid integer. Handle `ValueError` in `map_response_to_label()`
