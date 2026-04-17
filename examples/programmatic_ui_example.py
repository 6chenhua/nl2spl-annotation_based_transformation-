"""ProgrammaticUI 程序化示例

此示例演示如何使用 ProgrammaticUI 进行异步/批量化处理。
适用于 Web API、自动化任务或需要前端展示冲突的场景。

适用场景:
- Web API (FastAPI/Flask)
- 异步任务队列 (Celery/RQ)
- 需要预置答案的批量处理
- 自定义前端界面
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline import Pipeline
from src.clarification.clarification_ui import ProgrammaticUI


async def demo_basic_usage():
    """示例1: 基础使用 - 查看冲突但不解决"""

    print("\n" + "=" * 80)
    print("示例1: 基础使用 - 仅查看冲突")
    print("=" * 80)

    # 使用 ProgrammaticUI，不预置任何答案
    ui = ProgrammaticUI()
    pipeline = Pipeline(ui=ui)

    prompt = """
创建一个智能客服助手。

角色设定：
- 你是一个友好、耐心的客服代表
- 具备专业的产品知识和沟通技巧

工作流程：
1. 接收用户问题
2. 分析问题类型
3. 检索知识库获取答案
4. 生成友好回复
"""

    print("开始转换...")
    result = await pipeline.convert(prompt)

    if result.success:
        print(f"\n转换完成!")
        print(f"冲突数量: {len(result.conflicts)}")

        # 查看待处理的问题
        pending = ui.get_pending_questions()
        print(f"\n待澄清问题 ({len(pending)} 个):")

        for i, question in enumerate(pending, 1):
            print(f"\n问题 {i}:")
            print(f"  {question.question_text[:200]}...")
            print(f"  选项: {question.options}")

    return ui, result


async def demo_with_preset_answers():
    """示例2: 预置答案 - 自动化处理"""

    print("\n" + "=" * 80)
    print("示例2: 预置答案 - 自动化处理")
    print("=" * 80)

    ui = ProgrammaticUI()
    pipeline = Pipeline(ui=ui)

    # 场景：我们知道冲突是什么，预先设置答案
    # 例如：我们知道会有角色描述和约束条件的冲突
    # 预置所有可能的答案

    prompt = """
创建一个智能客服助手。

你是一个友好、耐心的客服代表，能够处理各种用户问题。
工作流程包括：接收问题、分析类型、检索答案、生成回复。

约束：
- 回复必须在3秒内完成
- 保持礼貌和专业
- 不确定时转接人工客服
"""

    print("开始转换（带预置答案）...")

    # 先运行一次以获取问题数量
    result = await pipeline.convert(prompt)
    pending = ui.get_pending_questions()

    print(f"\n发现 {len(pending)} 个冲突")

    if pending:
        # 预置答案 - 根据业务规则自动选择
        # 示例：所有冲突都选择第一个选项
        for i in range(len(pending)):
            ui.submit_response(i, "1")  # 选择第一个选项

        # 重新运行以应用答案
        # 注意：需要清除之前的 pending 状态
        ui.pending_questions.clear()
        result = await pipeline.convert(prompt)

    print(f"\n转换完成!")
    print(f"最终冲突数: {len(result.conflicts)}")

    return result


async def demo_async_api_flow():
    """示例3: 模拟 Web API 流程"""

    print("\n" + "=" * 80)
    print("示例3: 模拟 Web API 流程")
    print("=" * 80)

    ui = ProgrammaticUI()
    pipeline = Pipeline(ui=ui)

    prompt = """
创建一个数据分析助手。

你是一个数据分析专家，擅长处理和分析各种数据。
能够生成图表、计算统计指标、发现数据异常。
"""

    print("步骤1: 提交转换请求...")
    result = await pipeline.convert(prompt)

    print(f"\n步骤2: 检查是否需要澄清...")
    pending = ui.get_pending_questions()

    if pending:
        print(f"  需要澄清: {len(pending)} 个问题")

        # 模拟 API 响应给前端
        questions_for_frontend = []
        for i, question in enumerate(pending):
            questions_for_frontend.append({
                "index": i,
                "text": question.question_text,
                "options": question.options,
                "context": question.context[:100]
            })

        print(f"\n  返回给前端的问题:")
        for q in questions_for_frontend:
            print(f"    问题 {q['index']}: {q['text'][:100]}...")

        # 模拟前端返回用户答案
        print(f"\n步骤3: 接收前端返回的答案...")
        user_answers = {
            0: "1",  # 第一个问题选选项1
            1: "2",  # 第二个问题选选项2
        }

        # 应用答案
        for idx, answer in user_answers.items():
            if idx < len(pending):
                ui.submit_response(idx, answer)
                print(f"  已提交问题 {idx} 的答案: {answer}")

        print(f"\n步骤4: 重新运行转换...")
        # 注意：实际API需要保存状态，这里简化演示
        result = await pipeline.convert(prompt)

    else:
        print("  无需澄清")

    print(f"\n转换完成!")
    print(f"SPL 代码长度: {len(result.spl_code)} 字符")

    return result


async def demo_batch_processing():
    """示例4: 批量处理多个 prompts"""

    print("\n" + "=" * 80)
    print("示例4: 批量处理")
    print("=" * 80)

    prompts = [
        "创建一个文案写作助手，擅长营销文案和广告语创作。",
        "创建一个代码审查助手，检查代码质量和潜在bug。",
        "创建一个数据可视化助手，生成各种图表和报告。",
    ]

    results = []

    for i, prompt in enumerate(prompts, 1):
        print(f"\n处理 Prompt {i}/{len(prompts)}...")

        # 每个 prompt 使用新的 UI 实例
        ui = ProgrammaticUI()
        pipeline = Pipeline(ui=ui)

        result = await pipeline.convert(prompt)
        results.append(result)

        # 检查冲突
        pending = ui.get_pending_questions()
        if pending:
            print(f"  发现 {len(pending)} 个冲突，使用默认策略解决...")
            # 批量处理策略：所有冲突选择第一个选项
            for j in range(len(pending)):
                ui.submit_response(j, "1")

    print(f"\n" + "=" * 80)
    print("批量处理完成!")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\nPrompt {i}:")
        print(f"  成功: {result.success}")
        print(f"  SPL 长度: {len(result.spl_code)} 字符")
        print(f"  冲突数: {len(result.conflicts)}")

    return results


async def main():
    """运行所有示例"""

    print("=" * 80)
    print("ProgrammaticUI 模式示例 - 程序化/异步处理")
    print("=" * 80)

    try:
        # 运行各个示例
        await demo_basic_usage()
        await demo_with_preset_answers()
        await demo_async_api_flow()
        await demo_batch_processing()

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("所有示例运行完成!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
