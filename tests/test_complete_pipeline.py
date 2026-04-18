# -*- coding: utf-8 -*-
"""完整Pipeline测试 - 智能客服AI助手用例"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import AsyncOpenAI

# Import pipeline components
from src.pipeline import Pipeline
from src.clarification.clarification_ui import ProgrammaticUI
from src.llm_adapter import LLMClientAdapter
from src.config import OPENAI_API_KEY, OPENAI_BASE_URL


async def test_complete_pipeline():
    """测试完整Pipeline"""
    
    print("=" * 80)
    print("Complete Pipeline Test - Customer Service AI Assistant")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
# Initialize OpenAI client with provided credentials
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable is not set. "
        "Please set it in your .env file or environment."
    )
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL or 'https://api.openai.com/v1'
)
    
    # Test prompt - Customer Service AI Assistant
    test_prompt = """Create an intelligent customer service AI assistant.

This assistant should act as a patient and friendly customer service representative, specializing in handling user inquiries and complaints.
The assistant needs to maintain a professional service attitude, understand user emotions, and provide appropriate responses.

Primarily targeting enterprise clients and individual users, especially those needing after-sales support.

Workflow:
1. Receive user questions
2. Analyze question type (inquiry/complaint/suggestion)
3. Search knowledge base for relevant information
4. Generate appropriate responses
5. If human handling is needed, transfer to human customer service

Constraints:
- Response time must not exceed 3 seconds
- For sensitive issues, must transfer to human
- Must use polite language
- Cannot provide medical or legal advice

The assistant should be available 24/7 and handle multiple languages.
"""
    
    print("\n[Test Input]")
    print("-" * 80)
    print(test_prompt)
    print("-" * 80)
    
    # Wrap client with adapter
    llm_client = LLMClientAdapter(client, model="gpt-4o")
    
    # Create pipeline with programmatic UI (auto-resolve conflicts)
    ui = ProgrammaticUI()
    pipeline = Pipeline(llm_client=llm_client, ui=ui)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "input_prompt": test_prompt,
        "phases": {}
    }
    
    try:
        print("\n[Phase 1] Starting Pipeline...")
        print("-" * 80)
        
        # Run pipeline
        result = await pipeline.convert(test_prompt)
        
        print("\n[Phase 2] Pipeline Execution Complete!")
        print("=" * 80)
        
        # Save results
        results["success"] = result.success
        results["error"] = None
        
        if result.success:
            print("\n[OK] Conversion successful!")
            print(f"  - Total annotation blocks: {len(result.annotations)}")
            print(f"  - Total conflicts found: {len(result.conflicts)}")
            
            # Phase 1: Annotations
            print("\n[Phase 1 Results] Annotations")
            print("-" * 80)
            annotations_data = {}
            for block_type, annotation in result.annotations.items():
                print(f"\n  Block: {block_type.value}")
                print(f"    - Segments: {len(annotation.segments)}")
                print(f"    - Confidence: {annotation.confidence:.2f}")
                print(f"    - Content preview:")
                content_preview = annotation.extracted_content[:200] if annotation.extracted_content else "(empty)"
                print(f"      {content_preview}...")
                
                annotations_data[block_type.value] = {
                    "segments_count": len(annotation.segments),
                    "confidence": annotation.confidence,
                    "content": annotation.extracted_content
                }
            results["phases"]["annotations"] = annotations_data
            
            # Phase 2: Conflicts
            if result.conflicts:
                print("\n[Phase 2 Results] Conflicts")
                print("-" * 80)
                conflicts_data = []
                for i, conflict in enumerate(result.conflicts):
                    print(f"\n  Conflict {i+1}:")
                    print(f"    - Content: {conflict.segments[0].content[:100]}...")
                    print(f"    - Candidate labels: {[c.value for c in conflict.candidate_labels]}")
                    conflicts_data.append({
                        "content": conflict.segments[0].content,
                        "candidates": [c.value for c in conflict.candidate_labels],
                        "resolution": conflict.resolution.value if conflict.resolution else None
                    })
                results["phases"]["conflicts"] = conflicts_data
            else:
                print("\n[Phase 2 Results] No conflicts detected")
                results["phases"]["conflicts"] = []
            
            # Phase 5: Generated SPL
            print("\n[Phase 5 Results] Generated SPL Code")
            print("=" * 80)
            print(result.spl_code)
            print("=" * 80)
            
            results["phases"]["spl_code"] = result.spl_code
            
            # Save to files
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Save SPL code
            spl_file = os.path.join(output_dir, "generated_customer_service.spl")
            with open(spl_file, 'w', encoding='utf-8') as f:
                f.write(result.spl_code)
            print(f"\n[OK] SPL code saved to: {spl_file}")
            
            # Save full results as JSON
            json_file = os.path.join(output_dir, "test_results.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"[OK] Test results saved to: {json_file}")
            
            return True
        else:
            print(f"\n[ERROR] Conversion failed: {result.errors}")
            results["error"] = result.errors
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        results["success"] = False
        results["error"] = str(e)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_complete_pipeline())
    sys.exit(0 if success else 1)