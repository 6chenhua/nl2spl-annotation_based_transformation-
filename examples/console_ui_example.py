"""ConsoleUI 交互式示例

此示例演示如何使用 ConsoleUI 进行交互式冲突解决。
当 Pipeline 检测到冲突时，会在终端显示问题并等待用户输入。

适用场景:
- 命令行工具
- Jupyter Notebook
- 开发调试
- 需要人工决策的转换任务
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline import Pipeline
from src.clarification.clarification_ui import ConsoleUI


async def main():
    """ConsoleUI 交互式示例"""

    print("=" * 80)
    print("ConsoleUI 模式示例 - 交互式冲突解决")
    print("=" * 80)
    print("\n此示例将在终端显示冲突澄清问题，需要您手动输入选择。\n")

    # 创建 Pipeline，使用 ConsoleUI 进行交互式提问
    # ConsoleUI 会在终端显示问题并等待键盘输入
    ui = ConsoleUI()
    pipeline = Pipeline(ui=ui)

    # 示例 prompt - 故意设计得模糊以产生冲突
    prompt = """
创建一个智能客服助手。

角色设定：
- 你是一个友好、耐心的客服代表
- 具备专业的产品知识和沟通技巧
- 能够处理用户咨询、投诉和建议

目标用户：
- 主要面向电商平台的消费者
- 年龄层在18-45岁之间
- 需要快速响应和准确解答

工作流程：
1. 接收用户问题
2. 分析问题类型（咨询/投诉/建议）
3. 检索知识库获取答案
4. 生成友好回复
5. 记录对话历史

约束：
- 回复必须在3秒内完成
- 保持礼貌和专业
- 不确定时转接人工客服
- 保护用户隐私信息
"""

    print("开始转换...")
    print("=" * 80)

    try:
        # 执行转换
        # 如果有冲突，ConsoleUI 会暂停并显示问题，等待您输入
        result = await pipeline.convert(prompt)

        print("\n" + "=" * 80)
        print("转换完成!")
        print("=" * 80)

        if result.success:
            print("\n生成的 SPL 代码：")
            print("-" * 80)
            print(result.spl_code)
            print("-" * 80)

            print(f"\n标注统计:")
            for block_type, annotation in result.annotations.items():
                print(f"  {block_type.value}: {len(annotation.segments)} segments, "
                      f"confidence: {annotation.confidence:.2f}")

            print(f"\n冲突数量: {len(result.conflicts)}")
            print(f"澄清历史: {len(result.clarification_history)} 条")

        else:
            print(f"转换失败: {result.errors}")

    except KeyboardInterrupt:
        print("\n\n用户取消操作")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
