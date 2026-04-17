# -*- coding: utf-8 -*-
"""完整Pipeline测试"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from openai import AsyncOpenAI
from src.pipeline import Pipeline
from src.clarification.clarification_ui import ProgrammaticUI
from src.llm_adapter import LLMClientAdapter


async def main():
    print("=" * 80)
    print("Annotated NL2SPL Pipeline - Full Test")
    print("=" * 80)
    
    # 初始化客户端
    client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # 包装客户端
    llm_client = LLMClientAdapter(client, model="gpt-4o")
    
    # 测试用例
    test_prompt = """Create an intelligent customer service AI assistant.

This assistant should act as a patient and friendly customer service representative.
It specializes in handling user inquiries and complaints.
The assistant maintains professional service attitude and understands user emotions.

Target users: enterprise clients and individual users needing after-sales support.

Workflow:
1. Receive user questions
2. Analyze question type (inquiry/complaint/suggestion)  
3. Search knowledge base
4. Generate appropriate responses
5. Transfer to human if needed

Constraints:
- Response time under 3 seconds
- Transfer sensitive issues to human
- Use polite language
- No medical or legal advice
"""
    
    print("\n[Test Prompt]")
    print("-" * 80)
    print(test_prompt[:300] + "...")
    print("-" * 80)
    
    # 创建pipeline
    ui = ProgrammaticUI()
    pipeline = Pipeline(llm_client=llm_client, ui=ui)
    
    try:
        print("\n[Running Pipeline...]")
        result = await pipeline.convert(test_prompt)
        
        print("\n" + "=" * 80)
        print("Results")
        print("=" * 80)
        
        if result.success:
            print(f"\n[OK] Success!")
            print(f"  Blocks: {len(result.annotations)}")
            print(f"  Conflicts: {len(result.conflicts)}")
            
            print("\n[Annotations]")
            for bt, ann in result.annotations.items():
                print(f"  {bt.value}: {len(ann.segments)} segments")
            
            print("\n[SPL Code]")
            print("-" * 80)
            print(result.spl_code)
            print("-" * 80)
            
            # 保存结果
            os.makedirs("test_output", exist_ok=True)
            with open("test_output/final_result.spl", "w", encoding="utf-8") as f:
                f.write(result.spl_code)
            print("\n[Saved] test_output/final_result.spl")
            
            return True
        else:
            print(f"\n[Failed] {result.errors}")
            return False
            
    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)