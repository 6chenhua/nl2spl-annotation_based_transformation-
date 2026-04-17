"""代码生成器基类"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from ..models import Annotation, SPLBlockType

logger = logging.getLogger(__name__)


class BlockGenerator(ABC):
    """SPL块代码生成器基类"""
    
    def __init__(self, llm_client, config: Optional[dict] = None):
        """初始化生成器
        
        Args:
            llm_client: LLM客户端
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.block_type = self._block_type
    
    @property
    @abstractmethod
    def _block_type(self) -> SPLBlockType:
        """返回该生成器对应的SPL块类型"""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass
    
    async def generate(self, annotation: Annotation) -> str:
        """生成SPL代码块
        
        Args:
            annotation: 标注结果
            
        Returns:
            SPL代码字符串
        """
        logger.info(f"Generating {self.block_type.value} block")
        
        # 加载提示词
        system_prompt = self._get_system_prompt()
        
        # 构建用户提示
        user_prompt = self._build_user_prompt(annotation)
        
        # 调用LLM
        response = await self.llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # 提取代码
        code = self._extract_code(response)
        
        # 后处理
        code = self._post_process(code)
        
        logger.info(f"Generated {self.block_type.value} block: {len(code)} chars")
        
        return code
    
    def _build_user_prompt(self, annotation: Annotation) -> str:
        """构建用户提示"""
        return f"""请根据以下内容生成SPL {self.block_type.value.upper()} 块代码：

[内容开始]
{annotation.extracted_content}
[内容结束]

要求：
- 严格遵循SPL语法规范
- 只输出生成的代码块，不要包含其他说明
- 确保标签正确闭合
"""
    
    def _extract_code(self, response) -> str:
        """从响应中提取代码"""
        # 处理不同格式的响应
        if isinstance(response, dict):
            content = response.get("content", "")
        elif isinstance(response, str):
            content = response
        else:
            content = str(response)
        
        # 尝试提取代码块
        import re
        code_pattern = r'```(?:spl)?\n?(.*?)```'
        match = re.search(code_pattern, content, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有代码块，返回整个内容
        return content.strip()
    
    def _post_process(self, code: str) -> str:
        """后处理代码"""
        # 去除多余空行
        lines = [line for line in code.split('\n') if line.strip()]
        return '\n'.join(lines)
