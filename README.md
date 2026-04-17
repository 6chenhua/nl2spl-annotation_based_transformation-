# Annotated NL2SPL Pipeline

基于标注的NL到SPL转换管道，采用多智能体并行标注 + 冲突检测 + 人机交互澄清的策略。

## 核心特性

- **并行标注**：多个SPL块标注器同时运行，独立检测内容归属
- **智能冲突检测**：使用语义相似度匹配识别重复/重叠标注
- **人机交互**：通过自然语言提问解决冲突，用户无需了解SPL技术细节
- **分块生成**：各SPL块独立生成，最后合并为完整SPL

## 架构概览

```
User Prompt'
    │
    ▼
┌─────────────────────────────────────┐
│ Phase 1: 并行块标注                  │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │PERSONA  │ │AUDIENCE │ │CONCEPTS │ │ ... (async)
│ │Annotator│ │Annotator│ │Annotator│ │
│ └────┬────┘ └────┬────┘ └────┬────┘ │
└──────┼──────────┼──────────┼───────┘
       │          │          │
       ▼          ▼          ▼
   Tagged     Tagged     Tagged
   Segments   Segments   Segments
       │          │          │
       └──────────┼──────────┘
                  ▼
┌─────────────────────────────────────┐
│ Phase 2: 冲突检测与聚合              │
│ - 语义相似度匹配                      │
│ - 冲突识别                           │
│ - 聚类分组                           │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ Phase 3: 人机交互澄清 (如有冲突)     │
│ - 生成自然语言问题                   │
│ - 用户回答                          │
│ - 确定最终标签                      │
└─────────────────┬───────────────────┘
                  ▼
    Annotated Prompt' (所有内容已标注)
                  │
                  ▼
┌─────────────────────────────────────┐
│ Phase 4: 分块并行生成                │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │PERSONA  │ │AUDIENCE │ │CONCEPTS │ │ ... (async)
│ │Generator│ │Generator│ │Generator│ │
│ └────┬────┘ └────┬────┘ └────┬────┘ │
└──────┼──────────┼──────────┼───────┘
       │          │          │
       └──────────┼──────────┘
                  ▼
┌─────────────────────────────────────┐
│ Phase 5: 合并与验证                │
│ - 块组合                            │
│ - 语法验证                          │
│ - 输出SPL                          │
└─────────────────────────────────────┘
```

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

```python
from annotated_nl2spl import Pipeline

pipeline = Pipeline()
result = pipeline.convert("创建一个文本校对的AI助手，能够检查拼写和语法错误...")
print(result.spl_code)
```

## 项目结构

```
annotated_nl2spl/
├── src/
│   ├── annotators/          # 块标注器
│   ├── conflict_resolution/ # 冲突检测与匹配
│   ├── clarification/       # 人机交互澄清
│   ├── generators/          # SPL块生成器
│   └── utils/              # 工具函数
├── prompts/                # LLM提示词
├── configs/                # 配置文件
├── tests/                  # 测试
├── examples/               # 示例
└── docs/                   # 文档
```

## 配置

见 `configs/pipeline.yaml`

## 开发

见 `docs/development.md`
