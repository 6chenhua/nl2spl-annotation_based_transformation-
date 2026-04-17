"""端到端测试 - 使用真实LLM API"""

import asyncio
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import AsyncOpenAI
from annotated_nl2spl.src.pipeline import Pipeline
from annotated_nl2spl.src.clarification.clarification_ui import ProgrammaticUI


async def test_e2e():
    """端到端测试"""
    
    print("=" * 80)
    print("端到端测试 - Annotated NL2SPL Pipeline")
    print("=" * 80)
    
    # 初始化LLM客户端
    llm_client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # 创建Pipeline
    ui = ProgrammaticUI()
    pipeline = Pipeline(llm_client=llm_client, ui=ui)
    
    # 测试prompt
    test_prompt = """创建一个智能客服AI助手。

这个助手应该扮演一个耐心、友好的客服代表角色，擅长处理用户咨询和投诉。
助手需要保持专业的服务态度，理解用户情绪并给出合适的回应。

主要面向企业客户和个人用户，特别是需要售后服务支持的用户群体。

工作流程：
1. 接收用户问题
2. 分析问题类型（咨询/投诉/建议）
3. 搜索知识库获取相关信息
4. 生成合适的回复
5. 如果需要人工处理，转接给人工客服

约束条件：
- 响应时间不超过3秒
- 对于敏感问题必须转人工
- 必须使用礼貌用语
- 不能提供医疗或法律建议
"""
    
    print("\n测试Prompt:")
    print("-" * 80)
    print(test_prompt[:300] + "...")
    print("-" * 80)
    
    try:
        print("\n开始转换...")
        result = await pipeline.convert(test_prompt)
        
        print("\n" + "=" * 80)
        print("转换完成!")
        print("=" * 80)
        
        if result.success:
            print("\n✓ 转换成功!")
            print(f"✓ 发现 {len(result.annotations)} 个标注块")
            print(f"✓ 发现 {len(result.conflicts)} 个冲突")
            
            print("\n标注详情:")
            for block_type, annotation in result.annotations.items():
                print(f"  - {block_type.value:20s}: {len(annotation.segments)} segments, "
                      f"confidence: {annotation.confidence:.2f}")
            
            if result.conflicts:
                print("\n冲突详情:")
                for i, conflict in enumerate(result.conflicts):
                    print(f"  Conflict {i+1}: {conflict.segments[0].content[:50]}...")
                    print(f"    Candidates: {[c.value for c in conflict.candidate_labels]}")
            
            print("\n生成的SPL代码预览:")
            print("-" * 80)
            print(result.spl_code[:1000])
            if len(result.spl_code) > 1000:
                print("...")
            print("-" * 80)
            
            # 保存结果
            output_file = "e2e_test_result.spl"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.spl_code)
            print(f"\n完整SPL代码已保存到: {output_file}")
            
            return True
        else:
            print(f"✗ 转换失败: {result.errors}")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_e2e())
    sys.exit(0 if success else 1)