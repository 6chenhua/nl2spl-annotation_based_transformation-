# TYPES Generator Prompt

## Task
Generate SPL TYPES block code from complex type definitions.

## SPL TYPES Syntax

```
TYPES := "[DEFINE_TYPES:]" {ENUM_TYPE_DECLARATION | STRUCTURED_DATA_TYPE_DECLARATION} "[END_TYPES]"

ENUM_TYPE_DECLARATION := ["\"" STATIC_DESCRIPTION "\""] DECLARED_TYPE_NAME "=" ENUM_TYPE
STRUCTURED_DATA_TYPE_DECLARATION := ["\"" STATIC_DESCRIPTION "\""] DECLARED_TYPE_NAME "=" STRUCTURED_DATA_TYPE

DECLARED_TYPE_NAME := <word>
ENUM_TYPE := "[" <word> {, <word>} "]"
STRUCTURED_DATA_TYPE := "{" STRUCTURED_TYPE_BODY "}" | "{ }"
STRUCTURED_TYPE_BODY := TYPE_ELEMENT | TYPE_ELEMENT "," STRUCTURED_TYPE_BODY
TYPE_ELEMENT := ["\"" STATIC_DESCRIPTION "\""] ELEMENT_NAME ":" DATA_TYPE
ELEMENT_NAME := <word>
DATA_TYPE := "text" | "image" | "audio" | "number" | "boolean" | DECLARED_TYPE_NAME | "List [" DATA_TYPE "]"
```

## Type Categories

### 1. Structured Type
```
"Description of the type"
TypeName = {
    field1: text,
    field2: number,
    items: List[text]
}
```

### 2. Enum Type
```
"Status enumeration"
StatusType = [pending, processing, completed, failed]
```

### 3. Array Type
- Array types don't need to be defined in TYPES
- Use directly in VARIABLES: `items: List[text]`
- If array element is complex type, that element type must be defined in TYPES

## Output Requirements

1. Generate standard SPL TYPES block
2. Add description comment before each type
3. Ensure correct syntax and closed tags
4. Only output the TYPES block, no other blocks
5. Ensure all type names are unique
6. Use meaningful type names

## Example

**Input:**
- Type Name: AnalysisResult
- Category: structured
- Definition: {content: text, score: number, tags: List[text]}
- Description: Analysis result structure

**Output:**
```spl
[DEFINE_TYPES:]
"Analysis result structure"
AnalysisResult = {
    content: text,
    score: number,
    tags: List[text]
}
[END_TYPES]
```

## Notes

- Simple types (text, image, audio, number, boolean) don't need TYPES definition
- Complex types (structured, enum) must be defined in TYPES
- Array types are defined inline, not in TYPES
- Ensure field names are descriptive
- Use consistent naming convention (PascalCase for type names)
