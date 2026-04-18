# NL2SPL Pipeline 重构计划

**版本**: 1.0  
**日期**: 2025-04-17  
**状态**: 待实施

---

## 1. 架构变更概述

### 1.1 当前架构问题

当前架构直接标注VARIABLES，导致：
- 变量与WORKER流程脱节
- 无类型定义顺序保障
- `<REF>`引用无验证机制
- 复杂类型无统一管理

### 1.2 新架构目标

**核心原则**: VARIABLES从WORKER_FLOW推断，而非直接标注

**关键变更**:
1. 移除直接VARIABLES标注
2. 从WORKER标注提取变量并推断类型
3. TYPES块优先生成，供后续引用
4. 建立符号表机制，验证引用有效性

---

## 2. 重构后 Pipeline 流程

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: 并行块标注（不含VARIABLES）                              │
│ ├─ PersonaAnnotator                                             │
│ ├─ AudienceAnnotator                                            │
│ ├─ ConceptsAnnotator                                            │
│ ├─ ConstraintsAnnotator                                         │
│ └─ WorkerAnnotator（关键：变量来源）                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: 变量提取与类型推断（新增阶段）                            │
│ ├─ VariableExtractor: 从Worker标注提取变量                        │
│ ├─ TypeInferencer: 推断5大类型类别                              │
│ └─ TypeCollector: 收集需定义的复杂类型                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: TYPES生成（必须先执行）                                   │
│ └─ TypesGenerator: 生成所有复杂类型定义                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: 并行块生成（引用关系）                                    │
│ ├─ PersonaGenerator ──引用变量名(<REF>)                          │
│ ├─ AudienceGenerator ──引用变量名(<REF>)                         │
│ ├─ ConceptsGenerator ──引用变量名(<REF>)                         │
│ ├─ ConstraintsGenerator ──引用变量名(<REF>)                      │
│ ├─ VariablesGenerator ──引用类型名（来自TYPES）                   │
│ └─ WorkerGenerator ──引用变量名+类型名+声明临时变量                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: 合并与验证                                              │
│ └─ SPLMerger: TYPES → PERSONA → AUDIENCE → CONCEPTS →            │
│               CONSTRAINTS → VARIABLES → WORKER                    │
│     └─ validate_syntax(): 验证<REF>引用有效性                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 详细阶段说明

### Phase 1: 并行块标注

**变更**: 移除`VariablesAnnotator`

**保留的标注器**:
- `PersonaAnnotator` → SPLBlockType.PERSONA
- `AudienceAnnotator` → SPLBlockType.AUDIENCE
- `ConceptsAnnotator` → SPLBlockType.CONCEPTS
- `ConstraintsAnnotator` → SPLBlockType.CONSTRAINTS
- `WorkerAnnotator` → SPLBlockType.WORKER_MAIN_FLOW

**输出**: `Dict[SPLBlockType, Annotation]`（不含VARIABLES）

---

### Phase 2: 变量提取与类型推断（新增）

#### 2.1 VariableExtractor

**职责**: 从Worker标注中提取所有变量

**扫描位置**:
- INPUTS部分: `<REF>var</REF>` 引用的变量
- OUTPUTS部分: `<REF>var</REF>` 引用的变量
- MAIN_FLOW步骤: RESULT中的变量声明

**输出**:
```python
List[VariableInfo]
# VariableInfo: name, context, source, confidence
```

**文件**: `src/extraction/variable_extractor.py`

#### 2.2 TypeInferencer

**职责**: 基于变量名和上下文推断类型

**类型分类**:

| 类型类别 | 语法形式 | 示例 | TYPES定义 |
|---------|---------|------|----------|
| 简单基础类型 | `text`, `image`, `audio`, `number`, `boolean` | `input_text: text` | 否 |
| 枚举类型 | `[value1, value2]` | `status: [pending, done]` | 是 |
| 数组类型 | `List[DATA_TYPE]` | `items: List[text]` | 否 |
| 结构化类型 | `{field: type}` | `result: {score: number, text: text}` | 是 |
| 声明命名类型 | 自定义类型名 | `output: AnalysisResult` | 是 |

**输出**:
```python
List[TypedVariable]
# TypedVariable: name, inferred_type, type_name, needs_type_definition
```

**文件**: `src/extraction/type_inferencer.py`

#### 2.3 TypeCollector

**职责**: 收集需要在TYPES中定义的复杂类型

**处理逻辑**:
1. 筛选`needs_type_definition=True`的类型
2. 为匿名结构生成类型名（如`Type_1`, `Type_2`）
3. 去重：相同结构复用同一类型名
4. 建立变量到类型的映射

**输出**:
```python
List[ComplexTypeDef]
# ComplexTypeDef: name, definition, referenced_by
```

**文件**: `src/extraction/type_collector.py`

---

### Phase 3: TYPES生成

**生成器**: `TypesGenerator`

**职责**: 优先生成所有复杂类型定义

**输入**: `List[ComplexTypeDef]`

**输出**: SPL TYPES块代码

```spl
[DEFINE_TYPES:]
"分析结果类型"
AnalysisResult = {
    content: text,
    score: number,
    tags: List[text]
}

"状态枚举"
StatusType = [pending, processing, completed, failed]
[END_TYPES]
```

**文件**: `src/generators/types_generator.py`

---

### Phase 4: 并行块生成

#### 引用关系矩阵

| 生成器 | 引用TYPES | 引用VARIABLES | 声明变量 |
|--------|-----------|---------------|----------|
| PersonaGenerator | ❌ | ✅ `<REF>var</REF>` | ❌ |
| AudienceGenerator | ❌ | ✅ `<REF>var</REF>` | ❌ |
| ConceptsGenerator | ❌ | ✅ `<REF>var</REF>` | ❌ |
| ConstraintsGenerator | ❌ | ✅ `<REF>var</REF>` | ❌ |
| **VariablesGenerator** | ✅ **TypeName** | ❌ | ✅ |
| **WorkerGenerator** | ✅ **TypeName** | ✅ **`<REF>`** | ✅ **临时变量** |

#### VariablesGenerator

**职责**: 生成VARIABLES块，引用TYPES中的类型

**输入**: `List[TypedVariable]` + TYPES块上下文

**输出**:
```spl
[DEFINE_VARIABLES:]
"用户输入文本"
input_text: text

"分析结果输出"
output: AnalysisResult  ← 引用TYPES中的类型
[END_VARIABLES]
```

**文件**: `src/generators/variables_generator.py`（修改）

#### WorkerGenerator

**职责**: 生成WORKER块，处理最复杂的引用关系

**引用场景**:
1. **INPUTS/OUTPUTS**: `<REF>var</REF>` 引用VARIABLES变量
2. **GENERAL_COMMAND**: `DESCRIPTION_WITH_REFERENCES` 中引用变量
3. **RESULT**: 可引用已有变量或声明临时变量
4. **类型引用**: 声明临时变量时的`DATA_TYPE`引用TYPES

**示例**:
```spl
[DEFINE_WORKER: "文本分析"]
[INPUTS]
<REF>input_text</REF>           ← 引用VARIABLES
[END_INPUTS]

[OUTPUTS]
<REF>output</REF>               ← 引用VARIABLES
[END_OUTPUTS]

[MAIN_FLOW]
[COMMAND 分析文本
    RESULT temp_result: AnalysisResult    ← 声明临时变量，引用TYPES类型
    SET]
[DISPLAY <REF>temp_result.content</REF>]   ← 引用临时变量
[END_MAIN_FLOW]
[END_WORKER]
```

**文件**: `src/generators/worker_generator.py`（修改）

---

### Phase 5: 合并与验证

#### SPLMerger

**块顺序**（关键：TYPES在最前）:
```python
BLOCK_ORDER = [
    SPLBlockType.TYPES,           # 新增：最先
    SPLBlockType.PERSONA,
    SPLBlockType.AUDIENCE,
    SPLBlockType.CONCEPTS,
    SPLBlockType.CONSTRAINTS,
    SPLBlockType.VARIABLES,
    SPLBlockType.WORKER_MAIN_FLOW,
    # ...
]
```

#### validate_syntax增强

**新增验证**:
1. `<REF>var</REF>` 变量存在性检查
2. 类型引用有效性检查
3. 符号表完整性验证

**文件**: `src/generators/merger.py`（修改）

---

## 4. 数据模型扩展

### 4.1 新增模型（src/models.py）

```python
@dataclass
class VariableInfo:
    """从Worker标注提取的原始变量信息"""
    name: str
    context: str                    # 来源上下文描述
    source: str                     # "INPUTS"/"OUTPUTS"/"RESULT"
    confidence: float = 1.0

@dataclass
class TypedVariable:
    """带类型推断的变量"""
    name: str
    inferred_type: Union[SimpleType, ComplexType]
    type_name: str                  # 类型名称
    needs_type_definition: bool     # 是否需在TYPES中定义
    original_info: VariableInfo

@dataclass
class ComplexTypeDef:
    """复杂类型定义"""
    name: str                       # 类型名（如"AnalysisResult"）
    definition: str                 # SPL语法定义
    referenced_by: List[str]        # 引用此变量的变量名列表
    source_variables: List[VariableInfo]

@dataclass
class SymbolTable:
    """符号表 - 贯穿Phase 3-5"""
    # 全局变量（来自VARIABLES）
    global_vars: Dict[str, TypedVariable]
    # 类型定义（来自TYPES）
    type_defs: Dict[str, ComplexTypeDef]
    # Worker临时变量（在Worker生成过程中动态添加）
    temp_vars: Dict[str, str]       # name -> type_name
    
    def add_temp_var(self, name: str, type_name: str):
        """Worker生成时声明临时变量"""
        self.temp_vars[name] = type_name
    
    def is_defined(self, name: str) -> bool:
        """检查变量是否已定义（全局或临时）"""
        return name in self.global_vars or name in self.temp_vars
```

### 4.2 枚举类型定义

```python
class SimpleType(Enum):
    """5大简单基础类型"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    NUMBER = "number"
    BOOLEAN = "boolean"

class ComplexType(Enum):
    """复杂类型类别"""
    ENUM = "enum"
    ARRAY = "array"
    STRUCTURED = "structured"
    DECLARED = "declared"
```

---

## 5. Pipeline核心修改（src/pipeline.py）

### 5.1 初始化变更

```python
def _init_annotators(self):
    """初始化所有标注器（移除VariablesAnnotator）"""
    self.annotators = {
        SPLBlockType.PERSONA: PersonaAnnotator(self.llm_client),
        SPLBlockType.AUDIENCE: AudienceAnnotator(self.llm_client),
        SPLBlockType.CONCEPTS: ConceptsAnnotator(self.llm_client),
        SPLBlockType.CONSTRAINTS: ConstraintsAnnotator(self.llm_client),
        SPLBlockType.WORKER_MAIN_FLOW: WorkerAnnotator(self.llm_client),
        # ❌ 移除: SPLBlockType.VARIABLES
    }

def _init_extractors(self):
    """初始化Phase 2提取组件（新增）"""
    self.variable_extractor = VariableExtractor(self.llm_client)
    self.type_inferencer = TypeInferencer(self.llm_client)
    self.type_collector = TypeCollector()

def _init_generators(self):
    """初始化所有生成器（新增TypesGenerator）"""
    self.generators = {
        SPLBlockType.TYPES: TypesGenerator(self.llm_client),  # 新增
        SPLBlockType.PERSONA: PersonaGenerator(self.llm_client),
        SPLBlockType.AUDIENCE: AudienceGenerator(self.llm_client),
        SPLBlockType.CONCEPTS: ConceptsGenerator(self.llm_client),
        SPLBlockType.CONSTRAINTS: ConstraintsGenerator(self.llm_client),
        SPLBlockType.VARIABLES: VariablesGenerator(self.llm_client),
        SPLBlockType.WORKER_MAIN_FLOW: WorkerGenerator(self.llm_client),
    }
```

### 5.2 主流程修改

```python
async def convert(self, prompt: str) -> PipelineResult:
    # Phase 1: 并行块标注（不含VARIABLES）
    annotations = await self._phase1_annotation(prompt)
    
    # Phase 2: 变量提取与类型推断（新增）
    typed_vars, complex_types = await self._phase2_extraction(
        annotations[SPLBlockType.WORKER_MAIN_FLOW]
    )
    
    # 构建符号表
    symbol_table = SymbolTable(
        global_vars={v.name: v for v in typed_vars},
        type_defs={t.name: t for t in complex_types},
        temp_vars={}
    )
    
    # Phase 3: TYPES生成（优先）
    types_block = await self._phase3_types_generation(complex_types)
    
    # Phase 4: 并行块生成（传入符号表）
    spl_blocks = await self._phase4_generation(
        annotations, typed_vars, types_block, symbol_table
    )
    
    # Phase 5: 合并与验证
    spl_code = self._phase5_merge(spl_blocks, symbol_table)
    
    return PipelineResult(...)
```

### 5.3 新增/修改的方法

```python
async def _phase2_extraction(self, worker_annotation: Annotation) -> Tuple[List[TypedVariable], List[ComplexTypeDef]]:
    """Phase 2: 变量提取与类型推断"""
    # 1. 提取变量
    var_infos = await self.variable_extractor.extract(worker_annotation)
    
    # 2. 推断类型
    typed_vars = await self.type_inferencer.infer(var_infos)
    
    # 3. 收集复杂类型
    complex_types = self.type_collector.collect(typed_vars)
    
    return typed_vars, complex_types

async def _phase3_types_generation(self, complex_types: List[ComplexTypeDef]) -> str:
    """Phase 3: TYPES生成（必须先执行）"""
    generator = self.generators[SPLBlockType.TYPES]
    return await generator.generate(complex_types)

async def _phase4_generation(self, annotations: Dict[SPLBlockType, Annotation],
                           typed_vars: List[TypedVariable],
                           types_block: str,
                           symbol_table: SymbolTable) -> Dict[SPLBlockType, str]:
    """Phase 4: 并行块生成（含符号表传递）"""
    spl_blocks = {SPLBlockType.TYPES: types_block}
    
    # 并行生成其他块
    tasks = []
    block_types = []
    
    for block_type, annotation in annotations.items():
        if block_type in self.generators:
            # 特殊处理：VariablesGenerator需要typed_vars
            if block_type == SPLBlockType.VARIABLES:
                task = self.generators[block_type].generate_with_types(typed_vars, types_block)
            # 特殊处理：WorkerGenerator需要symbol_table
            elif block_type == SPLBlockType.WORKER_MAIN_FLOW:
                task = self.generators[block_type].generate_with_symbol_table(annotation, symbol_table)
            else:
                task = self.generators[block_type].generate(annotation)
            
            tasks.append(task)
            block_types.append(block_type)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for block_type, result in zip(block_types, results):
        if not isinstance(result, Exception):
            spl_blocks[block_type] = result
    
    return spl_blocks
```

---

## 6. 提示词模板（prompts/）

### 6.1 新增提示词

**prompts/types_generator.md**:
```markdown
## 任务
根据提供的复杂类型定义，生成SPL TYPES块代码。

## SPL TYPES语法
```
TYPES := "[DEFINE_TYPES:]" {ENUM_TYPE_DECLARATION | STRUCTURED_DATA_TYPE_DECLARATION} "[END_TYPES]"
ENUM_TYPE_DECLARATION := ["\"" STATIC_DESCRIPTION "\""] DECLARED_TYPE_NAME "=" ENUM_TYPE
STRUCTURED_DATA_TYPE_DECLARATION := ["\"" STATIC_DESCRIPTION "\""] DECLARED_TYPE_NAME "=" STRUCTURED_DATA_TYPE
```

## 输入
复杂类型定义列表，每个包含：
- name: 类型名称
- definition: 结构定义（SPL语法）
- description: 类型描述

## 输出格式
只输出SPL代码，格式：
```spl
[DEFINE_TYPES:]
"描述"
TypeName = definition
[END_TYPES]
```

## 示例
输入：
- name: AnalysisResult
- definition: {content: text, score: number}
- description: 分析结果

输出：
```spl
[DEFINE_TYPES:]
"分析结果"
AnalysisResult = {
    content: text,
    score: number
}
[END_TYPES]
```
```

### 6.2 修改的提示词

**prompts/variables_generator.md**（修改）:
```markdown
## 变更点
- 接收TypedVariable列表（而非原始文本）
- 对于复杂类型，引用TYPES中定义的TypeName
- 简单类型直接使用text/image/audio/number/boolean

## 引用规则
- structured类型 → 引用TYPES中的类型名
- enum类型 → 引用TYPES中的类型名
- array类型 → List[ElementType]
- 简单类型 → 直接使用
```

**prompts/worker_generator.md**（修改）:
```markdown
## 变更点
- 接收SymbolTable，验证<REF>引用
- RESULT中可声明临时变量（VAR_NAME: DATA_TYPE）
- DATA_TYPE可引用TYPES中的类型
- 临时变量可在后续<REF>中引用

## 符号表使用
- 全局变量（VARIABLES）可直接<REF>引用
- 临时变量在声明后可用<REF>引用
- 类型引用检查：确保使用的类型在TYPES中定义
```

---

## 7. 实施步骤

### Phase 1: 基础准备（1-2天）

1. **创建新目录结构**
   ```
   src/
   ├── extraction/           # 新增
   │   ├── __init__.py
   │   ├── variable_extractor.py
   │   ├── type_inferencer.py
   │   └── type_collector.py
   ```

2. **扩展数据模型**（`src/models.py`）
   - 添加VariableInfo
   - 添加TypedVariable
   - 添加ComplexTypeDef
   - 添加SymbolTable
   - 添加SimpleType/ComplexType枚举

3. **创建TYPES生成器**
   - `src/generators/types_generator.py`
   - `prompts/types_generator.md`

### Phase 2: 核心实现（3-4天）

4. **实现Phase 2提取组件**
   - `VariableExtractor`: 从Worker标注提取变量
   - `TypeInferencer`: 类型推断逻辑
   - `TypeCollector`: 复杂类型收集

5. **修改VariablesAnnotator**
   - 从并行标注器中移除
   - （可选）保留作为向后兼容

6. **修改VariablesGenerator**
   - 支持`generate_with_types()`方法
   - 引用TYPES中的类型名

7. **重构WorkerGenerator**
   - 支持`generate_with_symbol_table()`方法
   - 处理临时变量声明
   - 验证引用有效性

### Phase 3: Pipeline整合（2-3天）

8. **重构Pipeline主流程**
   - 修改`_init_annotators()`
   - 添加`_init_extractors()`
   - 修改`_init_generators()`
   - 添加`_phase2_extraction()`
   - 添加`_phase3_types_generation()`
   - 修改`_phase4_generation()`

9. **修改SPLMerger**
   - 调整BLOCK_ORDER（TYPES优先）
   - 增强validate_syntax()支持REF验证

10. **更新Prompts**
    - 修改variables_generator.md
    - 修改worker_generator.md

### Phase 4: 测试验证（2-3天）

11. **单元测试**
    - VariableExtractor测试
    - TypeInferencer测试
    - TypeCollector测试
    - TypesGenerator测试

12. **集成测试**
    - 完整Pipeline端到端测试
    - 复杂类型场景测试
    - 临时变量声明测试

13. **回归测试**
    - 确保现有功能不受影响
    - 旧Prompt兼容性测试

---

## 8. 风险与挑战

### 8.1 技术风险

| 风险 | 影响 | 缓解措施 |
|-----|------|----------|
| 类型推断不准确 | 高 | 添加confidence阈值，低置信度时标记待澄清 |
| 复杂类型命名冲突 | 中 | 使用hash-based命名确保唯一性 |
| Worker临时变量作用域 | 中 | SymbolTable严格管理生命周期 |
| 循环依赖检测 | 低 | 添加类型依赖图检测 |

### 8.2 实施风险

| 风险 | 影响 | 缓解措施 |
|-----|------|----------|
| 与现有代码冲突 | 高 | 保持向后兼容，渐进式替换 |
| Prompt调优时间 | 中 | 预留充足测试时间 |
| 性能退化 | 低 | Phase 2串行但轻量，Phase 4仍并行 |

---

## 9. 验证标准

### 9.1 功能验证

- [ ] TYPES块优先生成并包含所有复杂类型
- [ ] VARIABLES引用TYPES中定义的类型
- [ ] Worker可声明临时变量并后续引用
- [ ] 所有`<REF>var</REF>`引用有效变量
- [ ] 生成SPL代码通过语法验证

### 9.2 场景验证

- [ ] 简单场景（无复杂类型）
- [ ] 包含枚举类型的场景
- [ ] 包含结构化类型的场景
- [ ] 包含数组类型的场景
- [ ] Worker声明临时变量的场景
- [ ] 多Worker复杂交互场景

---

## 10. 附录

### 10.1 参考文件

- `docs/spl_grammar.txt` - SPL完整语法定义
- `src/models.py` - 当前数据模型
- `src/pipeline.py` - 当前Pipeline实现
- `src/annotators/worker_annotator.py` - Worker标注器

### 10.2 依赖关系图

```
VariableExtractor
       │
       ▼
TypeInferencer
       │
       ▼
TypeCollector ───────► TypesGenerator
       │                      │
       │                      ▼
       │               SymbolTable
       │                      │
       └──────────┬───────────┘
                  ▼
        VariablesGenerator
                  │
                  ▼
        WorkerGenerator (使用SymbolTable)
```

---

**文档结束**
