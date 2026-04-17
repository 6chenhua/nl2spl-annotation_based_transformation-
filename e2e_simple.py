# -*- coding: utf-8 -*-
"""简化端到端测试 - 只测试标注器"""

import asyncio
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from openai import AsyncOpenAI
from src.annotators.persona_annotator import PersonaAnnotator
from src.annotators.audience_annotator import AudienceAnnotator
from src.annotators.worker_annotator import WorkerAnnotator


async def test_annotators():
    """测试标注器"""
    
    print("=" * 80)
    print("Simplified E2E Test: Testing Annotators")
    print("=" * 80)
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # Test prompt
    test_prompt = """Create a text proofreading AI assistant.

This assistant should act as a professional editor, specializing in checking spelling and grammar errors.
The assistant needs to maintain a friendly but rigorous tone.

Mainly for students and writers who need writing help.

Workflow:
1. Receive text input from user
2. Analyze grammar sentence by sentence
3. Mark discovered errors
4. Provide correction suggestions
5. Output proofread text
"""
    
    print("\nTest Prompt:")
    print("-" * 80)
    print(test_prompt)
    print("-" * 80)
    
    # Test PERSONA annotator
    print("\n[Test 1] PERSONA Annotator")
    print("-" * 80)
    persona_annotator = PersonaAnnotator(client)
    
    try:
        result = await persona_annotator.annotate(test_prompt)
        print(f"[OK] Found {len(result.segments)} segments")
        print(f"[OK] Confidence: {result.confidence:.2f}")
        
        for i, seg in enumerate(result.segments):
            print(f"\n  Segment {i+1}:")
            print(f"    Content: {seg.content}")
            print(f"    Position: {seg.start_pos}-{seg.end_pos}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Test AUDIENCE annotator
    print("\n[Test 2] AUDIENCE Annotator")
    print("-" * 80)
    audience_annotator = AudienceAnnotator(client)
    
    try:
        result = await audience_annotator.annotate(test_prompt)
        print(f"[OK] Found {len(result.segments)} segments")
        print(f"[OK] Confidence: {result.confidence:.2f}")
        
        for i, seg in enumerate(result.segments):
            print(f"\n  Segment {i+1}:")
            print(f"    Content: {seg.content}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Test WORKER annotator
    print("\n[Test 3] WORKER Annotator")
    print("-" * 80)
    worker_annotator = WorkerAnnotator(client)
    
    try:
        result = await worker_annotator.annotate(test_prompt)
        print(f"[OK] Found {len(result.segments)} segments")
        print(f"[OK] Confidence: {result.confidence:.2f}")
        
        for i, seg in enumerate(result.segments):
            print(f"\n  Segment {i+1}:")
            print(f"    Content: {seg.content[:200]}...")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    asyncio.run(test_annotators())