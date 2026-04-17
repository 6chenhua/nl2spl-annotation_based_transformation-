# Annotated NL2SPL 开发计划

## 项目概述

基于标注的NL到SPL转换管道，采用多智能体并行标注 + 语义匹配 + 人机交互澄清的策略。

## 架构设计

### 核心流程

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: 并行块标注 (Parallel Block Annotation)                  │
│ ─────────────────────────────────────────────────────────────── │
│ 输入: 原始自然语言 Prompt'                                        │
│ 输出: 各SPL块的标注结果列表                                        │
│                                                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│ │ PERSONA    │  │ AUDIENCE   │  │ CONCEPTS   │  ...          │
│ │ Annotator  │  │ Annotator  │  │ Annotator  │                 │
│ │ (async)    │  │ (async)    │  │ (async)    │                 │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└────────┼────────────────┼────────────────┼─────────────────────┘
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │Tagged   │      │Tagged   │      │Tagged   │
    │Segments │      │Segments │      │Segments │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│ Phase 2: 冲突检测与聚合 (Conflict Detection & Aggregation)      │
│ ─────────────────────────────────────────────────────────────  │
│ 输入: 各块的标注片段列表                                          │
│ 输出: 冲突列表 + 无冲突的标注                                     │
│                                                                  │
│ ┌────────────────────────────────────────┐                    │
│ │ 1. 语义相似度计算 (Semantic Similarity) │                    │
│ │    - 使用 sentence-transformers       │                    │
│ │    - 阈值: similarity > 0.85          │                    │
│ │                                        │                    │
│ │ 2. 位置重叠检测 (Position Overlap)     │                    │
│ │    - 计算文本位置重叠度                 │                    │
│ │                                        │                    │
│ │ 3. 冲突识别 (Conflict Identification)  │                    │
│ │    - 同一内容被标注为多个块             │                    │
│ │                                        │                    │
│ │ 4. 聚类聚合 (Cluster Aggregation)      │                    │
│ │    - 将相似片段聚类为统一表示          │                    │
│ └────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ 冲突?                                     │
    │ ┌─────┐                                  │
    └─┤ YES ├──► Phase 3: 人机交互澄清          │
      └──┬──┘                                  │
         │ NO                                   │
         ▼                                      │
    直接进入Phase 4                              │
    └─────────────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│ Phase 3: 人机交互澄清 (Human-in-the-Loop Clarification)         │
│ ─────────────────────────────────────────────────────────────  │
│ 输入: 冲突列表                                                    │
│ 输出: 解决后的标注分配                                            │
│                                                                  │
│ ┌────────────────────────────────────────┐                    │
│ │ 1. 生成间接问题 (Indirect Question     │                    │
│ │    Generation)                         │                    │
│ │    - 用户看不到"SPL"、"PERSONA"等术语  │                    │
│ │    - 使用业务领域语言提问              │                    │
│ │                                        │                    │
│ │    例: "这段描述的是AI助手的角色定位    │                    │
│ │         还是目标用户群体特征？"          │                    │
│ │                                        │                    │
│ │ 2. 用户回答收集                        │                    │
│ │    - Console UI / Web UI / API        │                    │
│ │                                        │                    │
│ │ 3. 标签映射回SPL块                     │                    │
│ │    - 将业务答案映射回技术标签          │                    │
│ └────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────▼─────────────────────────────────────┐
│ Phase 4: 分块并行生成 (Parallel Block Generation)              │
│ ─────────────────────────────────────────────────────────────  │
│ 输入: 已标注的最终内容                                            │
│ 输出: 各SPL块的代码                                               │
│                                                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│ │ PERSONA    │  │ AUDIENCE   │  │ CONCEPTS   │  ...          │
│ │ Generator  │  │ Generator  │  │ Generator  │                 │
│ │ (async)    │  │ (async)    │  │ (async)    │                 │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└────────┼────────────────┼────────────────┼─────────────────────┘
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │SPL Code │      │SPL Code │      │SPL Code │
    │Block    │      │Block    │      │Block    │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│ Phase 5: 合并与验证 (Merge & Validation)                         │
│ ─────────────────────────────────────────────────────────────  │
│ 输入: 各SPL块代码                                                 │
│ 输出: 完整SPL代码                                                 │
│                                                                  │
│ ┌────────────────────────────────────────┐                    │
│ │ 1. 按SPL语法顺序组合块                  │                    │
│ │    - DEFINE_AGENT                      │                    │
│ │    - DEFINE_PERSONA                    │                    │
│ │    - DEFINE_AUDIENCE                   │                    │
│ │    - DEFINE_CONCEPTS                   │                    │
│ │    - DEFINE_CONSTRAINTS                │                    │
│ │    - DEFINE_VARIABLES                  │                    │
│ │    - DEFINE_WORKER                     │                    │
│ │    - END_AGENT                         │                    │
│ │                                        │                    │
│ │ 2. 语法验证                            │                    │
│ │    - 括号匹配                          │                    │
│ │    - 标签闭合                          │                    │
│ │    - 引用有效性                        │                    │
│ │                                        │                    │
│ │ 3. 格式化输出                          │                    │
│ └────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## 关键算法: 语义相似度匹配

### 问题

当多个标注器提取同一段内容时，由于LLM的生成差异，文本可能不完全相同：

```
Annotator A: "你是一个专业的文本校对助手"
Annotator B: "你是一个文本校对助手，很专业"
Annotator C: "这个助手是专业的文本校对员"
```

### 解决方案: 两阶段匹配

#### Stage 1: 嵌入向量聚类

```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN

# 加载模型
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 计算嵌入
embeddings = model.encode(all_segments)

# 聚类（密度聚类，自动确定簇数量）
clustering = DBSCAN(eps=0.3, min_samples=1, metric='cosine')
clusters = clustering.fit_predict(embeddings)
```

#### Stage 2: 簇内位置验证

```python
def validate_cluster(cluster_segments, original_text):
    """验证簇内片段是否确实指向同一内容"""
    conflicts = []
    
    for seg1, seg2 in combinations(cluster_segments, 2):
        # 计算位置重叠
        overlap = calculate_overlap(
            (seg1.start_pos, seg1.end_pos),
            (seg2.start_pos, seg2.end_pos)
        )
        
        # 如果位置重叠度 > 50%，认为是真正的冲突
        if overlap > 0.5:
            conflicts.append((seg1, seg2))
    
    return conflicts
```

#### 复杂度优化

**原始方案**: O(n^m) 其中 n=每个块的标注数, m=块数量

**优化方案**: 
1. 先聚类为 K 个簇: O(n * embedding_dim)
2. 只在簇内检查冲突: O(K * (n/K)^2) = O(n^2/K)
3. 对于K个簇，总复杂度: O(n^2/K * K) = O(n^2)，但常数项大幅减小

## 模块设计

### 1. Annotators 模块

**职责**: 每个SPL块类型对应一个标注器

**核心类**:
- `BlockAnnotator` (ABC): 基类
- `PersonaAnnotator`: 标注角色相关内容
- `AudienceAnnotator`: 标注目标用户
- `ConceptsAnnotator`: 标注领域概念
- `ConstraintsAnnotator`: 标注约束条件
- `VariablesAnnotator`: 标注变量定义
- `WorkerAnnotator`: 标注工作流

**关键方法**:
```python
async def annotate(self, prompt: str) -> Annotation:
    # 1. 加载块特定prompt
    # 2. 调用LLM
    # 3. 解析响应
    # 4. 返回标注结果
```

### 2. Conflict Resolution 模块

**职责**: 检测和聚合冲突

**核心类**:
- `ConflictDetector`: 冲突检测器
- `SemanticMatcher`: 语义匹配引擎
- `ClusterAggregator`: 聚类聚合器

**关键算法**:
```python
class ConflictDetector:
    def detect_conflicts(self, annotations: Dict[SPLBlockType, Annotation]) -> List[Conflict]:
        # 1. 提取所有片段
        all_segments = self._extract_segments(annotations)
        
        # 2. 计算相似度矩阵
        similarity_matrix = self._compute_similarity(all_segments)
        
        # 3. 聚类
        clusters = self._cluster_segments(similarity_matrix)
        
        # 4. 识别冲突（一个簇包含多个标签）
        conflicts = self._identify_conflicts(clusters)
        
        return conflicts
```

### 3. Clarification 模块

**职责**: 人机交互澄清

**核心类**:
- `QuestionGenerator`: 问题生成器
- `ClarificationUI`: 交互界面（Console/Web/API）
- `LabelMapper`: 标签映射器

**关键流程**:
```python
class QuestionGenerator:
    def generate_question(self, conflict: Conflict) -> ClarificationQuestion:
        # 1. 分析冲突内容
        # 2. 使用LLM生成自然语言问题（不含SPL术语）
        # 3. 创建选项到标签的隐式映射
        # 4. 返回问题对象
```

### 4. Generators 模块

**职责**: 为每个SPL块生成代码

**核心类**:
- `BlockGenerator` (ABC): 基类
- `PersonaGenerator`: 生成PERSONA块
- `WorkerGenerator`: 生成WORKER块
- ... 等

### 5. Pipeline 模块

**职责**: 编排整个流程

**核心类**:
- `Pipeline`: 主流程控制器
- `Phase1Annotator`: Phase 1 协调器
- `Phase2ConflictResolver`: Phase 2 协调器
- `Phase3Clarification`: Phase 3 协调器
- `Phase4Generator`: Phase 4 协调器
- `Phase5Merger`: Phase 5 协调器

## 数据结构

### Annotation
```python
@dataclass
class Annotation:
    block_type: SPLBlockType
    segments: List[TextSegment]
    confidence: float
    extracted_content: str
```

### Conflict
```python
@dataclass
class Conflict:
    segments: List[TextSegment]
    candidate_labels: List[SPLBlockType]
    confidence_scores: Dict[SPLBlockType, float]
    resolution: Optional[SPLBlockType]
```

### ClarificationQuestion
```python
@dataclass
class ClarificationQuestion:
    conflict: Conflict
    question_text: str
    options: List[Dict[str, Any]]  # 包含隐式标签映射
    context: str
```

## 开发阶段

### Phase 0: 项目初始化 (1天)
- [x] 创建项目目录结构
- [x] 定义核心数据模型
- [x] 编写README和开发计划
- [ ] 设置CI/CD
- [ ] 编写基础工具函数

### Phase 1: 块标注器系统 (3天)
- [ ] 实现BlockAnnotator基类
- [ ] 实现各具体标注器（Persona, Audience等）
- [ ] 编写标注器prompt
- [ ] 单元测试

### Phase 2: 冲突检测引擎 (3天)
- [ ] 实现语义相似度计算
- [ ] 实现聚类算法
- [ ] 实现冲突识别
- [ ] 单元测试

### Phase 3: 人机交互澄清 (2天)
- [ ] 实现问题生成器
- [ ] 实现Console UI
- [ ] 实现标签映射
- [ ] 单元测试

### Phase 4: 分块生成器 (2天)
- [ ] 实现BlockGenerator基类
- [ ] 实现各块生成器
- [ ] 编写生成器prompt
- [ ] 单元测试

### Phase 5: 集成与测试 (2天)
- [ ] 实现Pipeline主流程
- [ ] 端到端测试
- [ ] 性能优化
- [ ] 修复bug

### Phase 6: 文档与示例 (1天)
- [ ] 编写完整文档
- [ ] 创建示例
- [ ] 编写使用指南

**总计: 14天**

## 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| LLM Client | OpenAI/Anthropic SDK | 兼容性好，易于切换模型 |
| Embeddings | sentence-transformers | 本地运行，无需API调用，支持多语言 |
| Clustering | scikit-learn DBSCAN | 自动确定簇数量，适合此场景 |
| Async | asyncio | 天然支持并行标注器 |
| Config | YAML | 易于人类阅读和编辑 |
| Testing | pytest + pytest-asyncio | Python标准测试框架 |

## Prompt设计原则

### 标注器Prompt结构

```yaml
system_prompt: |
  你是一名专业的SPL内容标注专家。
  
  ## 任务
  从用户的自然语言描述中，识别并提取属于{BLOCK_NAME}的内容。
  
  ## {BLOCK_NAME}定义
  {BLOCK_DEFINITION}
  
  ## 输出格式
  以JSON格式返回提取的段落列表：
  ```json
  {
    "segments": [
      {
        "content": "提取的文本内容",
        "relevance": "high/medium/low",
        "reason": "为什么这段内容属于{BLOCK_NAME}"
      }
    ]
  }
  ```
  
  ## 注意
  - 只提取确定属于{BLOCK_NAME}的内容
  - 如果没有相关内容，返回空数组
  - 保持文本原样，不要改写
```

### 问题生成Prompt

```yaml
system_prompt: |
  你是一名专业的需求澄清专家。
  
  ## 任务
  用户描述了一段内容，这段内容可能属于多个不同的方面。
  请生成一个自然语言问题，帮助确定这段内容最准确的归属。
  
  ## 要求
  - 问题必须使用业务领域的语言
  - 不要出现技术术语如"SPL"、"PERSONA"、"CONSTRAINTS"等
  - 提供选项供用户选择
  - 每个选项对应一个技术标签（在后台处理）
```

## 配置文件示例

```yaml
# configs/pipeline.yaml

pipeline:
  # 阶段配置
  phases:
    annotation:
      parallel: true
      max_workers: 10
      
    conflict_resolution:
      similarity_threshold: 0.85
      clustering:
        algorithm: "dbscan"
        eps: 0.3
        min_samples: 1
      
    clarification:
      enabled: true
      ui_type: "console"  # console / web / api
      max_questions: 10
      
    generation:
      parallel: true
      
  # 块配置
  blocks:
    - name: "persona"
      enabled: true
      required: true
      annotator_prompt: "prompts/persona_annotator.txt"
      generator_prompt: "prompts/persona_generator.txt"
      
    - name: "audience"
      enabled: true
      required: false
      annotator_prompt: "prompts/audience_annotator.txt"
      generator_prompt: "prompts/audience_generator.txt"
      
    # ... 其他块

  # LLM配置
  llm:
    model: "gpt-4o"
    temperature: 0.3
    max_tokens: 4000
    
  # 嵌入模型配置
  embedding:
    model: "paraphrase-multilingual-MiniLM-L12-v2"
    device: "cpu"  # cpu / cuda
```

## 使用示例

### 基础使用

```python
from annotated_nl2spl import Pipeline

# 创建管道
pipeline = Pipeline.from_config("configs/pipeline.yaml")

# 转换
result = await pipeline.convert(
    prompt="创建一个文本校对的AI助手，能够检查拼写和语法错误..."
)

# 输出SPL
print(result.spl_code)
```

### 带人机交互

```python
from annotated_nl2spl import Pipeline, ConsoleUI

# 创建带UI的管道
ui = ConsoleUI()
pipeline = Pipeline(ui=ui)

# 转换（会触发交互式问题）
result = await pipeline.convert(prompt)
```

## 测试策略

### 单元测试
- 每个标注器的独立测试
- 冲突检测算法测试
- 聚类算法测试
- 问题生成器测试

### 集成测试
- 端到端流程测试
- 多冲突场景测试
- 边界条件测试

### 示例测试
- 使用真实prompt测试
- 对比输出质量

## 注意事项

1. **语义匹配的阈值**: 需要通过实验确定最佳阈值（建议0.80-0.90）
2. **LLM温度**: 标注阶段使用较低温度（0.3），生成阶段可适当提高
3. **错误处理**: 每个阶段都应有健壮的错误处理和回退机制
4. **性能**: 注意嵌入计算的缓存，避免重复计算
