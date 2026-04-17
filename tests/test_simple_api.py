"""简单测试 - 验证API调用"""

import asyncio
import json
from openai import AsyncOpenAI


async def test_api():
    """测试API调用"""
    
    print("=" * 80)
    print("测试 LLM API 调用")
    print("=" * 80)
    
    # 初始化客户端
    client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # 测试prompt
    system_prompt = """你是一个SPL标注专家。从用户的描述中提取属于PERSONA（角色定义）的内容。

PERSONA描述AI Agent的角色、性格和专业背景。

以JSON格式返回：
{
    "segments": [
        {
            "content": "提取的文本",
            "relevance": "high"
        }
    ]
}"""

    user_prompt = """创建一个智能客服AI助手。

这个助手应该扮演一个耐心、友好的客服代表角色，擅长处理用户咨询和投诉。
助手需要保持专业的服务态度，理解用户情绪并给出合适的回应。

主要面向企业客户和个人用户，特别是需要售后服务支持的用户群体。
"""
    
    print("\n调用API...")
    print("-" * 80)
    print(f"Model: gpt-4o")
    print(f"System prompt length: {len(system_prompt)} chars")
    print(f"User prompt length: {len(user_prompt)} chars")
    print("-" * 80)
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        print("\n[OK] API调用成功!")
        print("-" * 80)
        print("响应内容:")
        print(content)
        print("-" * 80)
        
        # 解析JSON
        try:
            result = json.loads(content)
            print("\n[OK] JSON解析成功!")
            print(f"  发现 {len(result.get('segments', []))} 个片段")
            
            for i, seg in enumerate(result.get('segments', [])):
                print(f"  片段 {i+1}: {seg.get('content', '')[:100]}...")
                
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析失败: {e}")
            
        return True
        
    except Exception as e:
        print(f"\n[ERROR] API调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_api())
    exit(0 if success else 1)