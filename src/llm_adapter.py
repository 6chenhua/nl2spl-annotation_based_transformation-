# -*- coding: utf-8 -*-
"""LLM Client Adapter

适配原始的 AsyncOpenAI 客户端以匹配我们期望的接口
"""

import json
import logging
from typing import Optional, Dict, Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClientAdapter:
    """LLM Client适配器
    
    将 AsyncOpenAI 包装成我们需要的接口
    """
    
    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o"):
        self.client = client
        self.model = model
    
    async def complete(self, 
                       system_prompt: str, 
                       user_prompt: str,
                       response_format: Optional[str] = None) -> Dict[str, Any]:
        """调用LLM完成请求
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response_format: 响应格式 ("text" 或 "json")
            
        Returns:
            解析后的响应字典
        """
        logger.debug(f"Calling LLM with model: {self.model}")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            if response_format == "json":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
            else:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000
                )
            
            content = response.choices[0].message.content
            
            # 如果是JSON格式，尝试解析
            if response_format == "json":
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}")
                    return {"content": content, "error": str(e)}
            
            return {"content": content}
            
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise