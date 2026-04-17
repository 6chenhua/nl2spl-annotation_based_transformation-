# -*- coding: utf-8 -*-
"""端到端测试 - 使用真实LLM API"""

import asyncio
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import AsyncOpenAI
from src.pipeline import Pipeline
from src.clarification.clarification_ui import ProgrammaticUI


async def test_pipeline():
    """测试完整Pipeline"""
    
    print("=" * 80)
    print("End-to-End Test: Annotated NL2SPL Pipeline")
    print("=" * 80)
    
    # Initialize OpenAI client with the provided credentials
    client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # Create pipeline with programmatic UI (no interactive questions)
    ui = ProgrammaticUI()
    pipeline = Pipeline(llm_client=client, ui=ui)
    
    # Test prompt
    test_prompt = """Create a text proofreading AI assistant.

This assistant should act as a professional editor, specializing in checking spelling and grammar errors in Chinese text.
The assistant needs to maintain a friendly but rigorous tone, identifying errors and providing correction suggestions.

Mainly for students, writers, and professionals who need writing help.
Users can directly input text to be proofread or upload document files.

Workflow:
1. Receive text input from user
2. Analyze grammar and wording sentence by sentence
3. Mark discovered errors
4. Provide correction suggestions
5. Output proofread text

Constraints:
- Must respect the original meaning of user text, only modify errors without changing style
- For uncertain errors, should list them for user selection
- Response time within 3 seconds
"""
    
    print("\nTest Prompt:")
    print("-" * 80)
    print(test_prompt[:300] + "...")
    print("-" * 80)
    
    try:
        print("\nStarting conversion...")
        print("Phase 1: Parallel block annotation")
        
        result = await pipeline.convert(test_prompt)
        
        print("\n" + "=" * 80)
        print("Conversion Complete!")
        print("=" * 80)
        
        if result.success:
            print("\n[OK] Conversion successful!")
            print(f"[INFO] Found {len(result.annotations)} annotation blocks")
            print(f"[INFO] Found {len(result.conflicts)} conflicts")
            
            print("\nAnnotation Details:")
            for block_type, annotation in result.annotations.items():
                print(f"  - {block_type.value:25s}: {len(annotation.segments)} segments, "
                      f"confidence: {annotation.confidence:.2f}")
                if annotation.segments:
                    print(f"    Content preview: {annotation.extracted_content[:80]}...")
            
            if result.conflicts:
                print("\nConflict Details:")
                for i, conflict in enumerate(result.conflicts):
                    print(f"  Conflict {i+1}: {conflict.segments[0].content[:50]}...")
                    print(f"    Candidates: {[c.value for c in conflict.candidate_labels]}")
            
            print("\nGenerated SPL Code:")
            print("-" * 80)
            print(result.spl_code)
            print("-" * 80)
            
            # Save result
            output_file = "test_output.spl"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.spl_code)
            print(f"\n[INFO] Full SPL code saved to: {output_file}")
            
            return True
        else:
            print(f"[ERROR] Conversion failed: {result.errors}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pipeline())
    sys.exit(0 if success else 1)