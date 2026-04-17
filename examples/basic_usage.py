"""基本使用示例"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from openai import AsyncOpenAI
from src.pipeline import Pipeline
from src.llm_adapter import LLMClientAdapter
from src.clarification.clarification_ui import ProgrammaticUI


async def main():
    """基本使用示例"""
    
    # 初始化OpenAI客户端（使用提供的API凭证）
    client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # 包装客户端
    llm_client = LLMClientAdapter(client, model="gpt-4o")
    
    # 创建Pipeline
    ui = ProgrammaticUI()  # 使用程序化UI（自动处理冲突）
    pipeline = Pipeline(llm_client=llm_client, ui=ui)
    
    # 示例prompt
    prompt = """
    创建一个文本校对的AI助手。
    
    这个角色应该是一名专业的编辑，擅长检查中文文本的拼写和语法错误。
    助手需要保持友好但严谨的语气，找出错误并给出修改建议。
    
    主要面向需要写作帮助的学生、作家和职场人士。
    用户可以直接输入待校对的文本，或者上传文档文件。
    
    工作流程：
    1. 接收用户输入的文本
    2. 逐句分析语法和用词
    3. 标记发现的错误
    4. 提供修改建议
    5. 输出校对后的文本
    
    约束：
    - 必须尊重用户原文的意思，只修改错误不改变风格
    - 对于不确定的错误，应该列出供用户选择
    - 响应时间控制在3秒内
    """
    
    print("开始转换...")
    print("=" * 80)
    
    # 执行转换
    result = await pipeline.convert(prompt)
    
    print("\n" + "=" * 80)
    print("转换完成!")
    print("=" * 80)
    
    if result.success:
        print("\n生成的SPL代码：")
        print("-" * 80)
        print(result.spl_code)
        print("-" * 80)
        
        print(f"\n标注统计:")
        for block_type, annotation in result.annotations.items():
            print(f"  {block_type.value}: {len(annotation.segments)} segments, "
                  f"confidence: {annotation.confidence:.2f}")
        
        print(f"\n冲突数量: {len(result.conflicts)}")
        
    else:
        print(f"转换失败: {result.errors}")


if __name__ == "__main__":
    asyncio.run(main())