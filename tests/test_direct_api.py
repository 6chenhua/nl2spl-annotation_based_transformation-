# -*- coding: utf-8 -*-
"""直接测试 - 使用AsyncOpenAI"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import AsyncOpenAI


async def test_direct():
    """直接测试API"""
    
    print("=" * 80)
    print("Direct API Test")
    print("=" * 80)
    
    # Create client with provided credentials
    client = AsyncOpenAI(
        base_url='https://api.rcouyi.com/v1',
        api_key="sk-V0s4xmnT70wbwPPe160dBaCc96A74fB9Ae850fFc6dE6136b"
    )
    
    # System prompt for PERSONA annotation
    system_prompt = """You are an SPL annotation expert. Extract content belonging to PERSONA (role definition) from the user's description.

PERSONA describes the AI Agent's role, personality, and professional background.

Content types to extract:
1. Role identity (professional editor, customer service representative, etc.)
2. Personality traits (patient, friendly, rigorous, professional)
3. Professional background and expertise
4. Style/tone of communication

Return in JSON format:
{
    "segments": [
        {
            "content": "Extracted text",
            "relevance": "high"
        }
    ]
}"""

    user_prompt = """Create a text proofreading AI assistant.

This assistant should act as a professional editor, specializing in checking spelling and grammar errors.
The assistant needs to maintain a friendly but rigorous tone, identifying errors and providing correction suggestions.

Mainly for students, writers, and professionals who need writing help.
"""
    
    print("\nCalling API with model: gpt-4o")
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
        
        print("[SUCCESS] API call successful!")
        print("-" * 80)
        print("Response:")
        print(content)
        print("-" * 80)
        
        # Parse and display
        import json
        try:
            result = json.loads(content)
            segments = result.get('segments', [])
            print(f"\n[INFO] Found {len(segments)} segments:")
            for i, seg in enumerate(segments):
                print(f"  {i+1}. {seg.get('content', '')}")
            return True
        except Exception as e:
            print(f"[WARNING] Could not parse JSON: {e}")
            return True
            
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_direct())
    sys.exit(0 if success else 1)