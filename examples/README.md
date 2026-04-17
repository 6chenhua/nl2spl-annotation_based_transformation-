# Annotated NL2SPL 示例

本目录包含使用 Annotated NL2SPL Pipeline 的各种示例。

## 文件说明

### 1. `console_ui_example.py` - ConsoleUI 交互式示例

**运行方式:**
```bash
python examples/console_ui_example.py
```

**特点:**
- 终端交互式提问
- 当 Pipeline 检测到冲突时，会暂停并显示问题
- 用户在终端输入选择（如 "1", "2" 等）
- 适合命令行工具、开发调试

**使用场景:**
- Python 脚本直接运行
- Jupyter Notebook 交互
- 开发调试阶段
- 需要人工决策的转换任务

---

### 2. `programmatic_ui_example.py` - ProgrammaticUI 程序化示例

**运行方式:**
```bash
python examples/programmatic_ui_example.py
```

**特点:**
- 异步处理，不阻塞程序
- 问题进入队列，可批量处理
- 支持预置答案（自动化）
- 适合 Web API、批量任务

**包含的示例:**
1. **基础使用** - 查看冲突但不解决
2. **预置答案** - 使用预置答案自动处理冲突
3. **模拟 Web API 流程** - 演示 API 请求-响应模式
4. **批量处理** - 处理多个 prompts

**使用场景:**
- FastAPI/Flask Web 服务
- 异步任务队列 (Celery/RQ)
- 需要前端界面的应用
- 批量自动化处理

---

### 3. `basic_usage.py` - 基础使用示例

**运行方式:**
```bash
python examples/basic_usage.py
```

**特点:**
- 展示最基础的 Pipeline 使用
- 使用 ProgrammaticUI（不交互）
- 使用自定义 LLM 客户端

---

## 快速对比

| 特性 | ConsoleUI | ProgrammaticUI |
|------|-----------|----------------|
| 交互方式 | 终端实时输入 | 队列 + 预置响应 |
| 是否阻塞 | 是 | 否 |
| 适用场景 | CLI、调试 | Web API、批处理 |
| 冲突处理 | 人工决策 | 自动/异步决策 |

## 示例代码对比

### ConsoleUI
```python
from src.pipeline import Pipeline
from src.clarification.clarification_ui import ConsoleUI

ui = ConsoleUI()
pipeline = Pipeline(ui=ui)
result = await pipeline.convert("你的 prompt...")
# 如果有冲突，程序会暂停，在终端显示问题并等待输入
```

### ProgrammaticUI
```python
from src.pipeline import Pipeline
from src.clarification.clarification_ui import ProgrammaticUI

ui = ProgrammaticUI()
pipeline = Pipeline(ui=ui)
result = await pipeline.convert("你的 prompt...")

# 检查待处理问题
questions = ui.get_pending_questions()
for i, question in enumerate(questions):
    print(f"问题 {i}: {question.question_text}")

# 提交答案
ui.submit_response(0, "1")  # 第一个问题选择选项1
ui.submit_response(1, "2")  # 第二个问题选择选项2

# 重新运行以应用答案
result = await pipeline.convert("你的 prompt...")
```

## 运行环境要求

- Python 3.8+
- 已安装项目依赖: `pip install -r requirements.txt`
- 配置 OpenAI API 密钥（或使用默认提供的测试密钥）

## 输出文件

运行示例后会生成 `output.spl` 文件，包含生成的 SPL 代码。
