# -*- coding: utf-8 -*-
"""语义匹配器

使用 OpenAI Embedding API 计算文本片段之间的语义相似度。
"""

import logging
import os
from typing import List, Dict, Tuple, Optional
import numpy as np

from ..models import TextSegment
from ..config import OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """语义匹配器

    使用 OpenAI Embedding API 计算文本片段之间的语义相似度。
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.openai.com/v1",
                 model: str = "text-embedding-3-large",
                 cache_embeddings: bool = True):
        """初始化语义匹配器

        Args:
            api_key: OpenAI API密钥（可选，默认从环境变量读取）
            base_url: API基础URL
            model: 嵌入模型名称
            cache_embeddings: 是否缓存嵌入向量
        """
        # 优先使用传入的参数，其次从环境变量读取
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL or "https://api.openai.com/v1"
        
        if not self.api_key:
            raise ValueError(
                "API key is required. Please set OPENAI_API_KEY in your .env file "
                "or pass it to the constructor."
            )
        
        self.model = model
        self.cache_embeddings = cache_embeddings
        self._client = None
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
    def _get_client(self):
        """获取OpenAI客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key
                )
                logger.info(f"Initialized OpenAI client with model: {self.model}")
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self._client
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def compute_embedding(self, text: str) -> np.ndarray:
        """计算单个文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量 (numpy array)
        """
        if self.cache_embeddings:
            cache_key = self._get_cache_key(text)
            if cache_key in self._embedding_cache:
                return self._embedding_cache[cache_key]
        
        client = self._get_client()
        
        try:
            response = client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = np.array(response.data[0].embedding)
            
            if self.cache_embeddings:
                cache_key = self._get_cache_key(text)
                self._embedding_cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to compute embedding: {e}")
            raise
    
    def compute_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """批量计算文本嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入矩阵 (n_texts x embedding_dim)
        """
        if not texts:
            return np.array([])
        
        client = self._get_client()
        
        # 检查缓存
        if self.cache_embeddings:
            cached_embeddings = []
            texts_to_encode = []
            indices_to_encode = []
            
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._embedding_cache:
                    cached_embeddings.append((i, self._embedding_cache[cache_key]))
                else:
                    texts_to_encode.append(text)
                    indices_to_encode.append(i)
            
            if texts_to_encode:
                response = client.embeddings.create(
                    model=self.model,
                    input=texts_to_encode
                )
                
                new_embeddings = np.array([data.embedding for data in response.data])
                
                # 更新缓存
                for i, text in enumerate(texts_to_encode):
                    cache_key = self._get_cache_key(text)
                    self._embedding_cache[cache_key] = new_embeddings[i]
            else:
                new_embeddings = np.array([])
            
            # 组装结果
            if len(cached_embeddings) > 0:
                dim = cached_embeddings[0][1].shape[0]
            elif len(new_embeddings) > 0:
                dim = new_embeddings.shape[1]
            else:
                dim = 3072  # text-embedding-3-large dimension
            
            result = np.zeros((len(texts), dim))
            for i, emb in cached_embeddings:
                result[i] = emb
            for idx, i in enumerate(indices_to_encode):
                result[i] = new_embeddings[idx]
            
            return result
        else:
            response = client.embeddings.create(
                model=self.model,
                input=texts
            )
            return np.array([data.embedding for data in response.data])
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本之间的余弦相似度
        
        Args:
            text1: 第一个文本
            text2: 第二个文本
            
        Returns:
            余弦相似度 (-1.0 到 1.0)
        """
        emb1 = self.compute_embedding(text1)
        emb2 = self.compute_embedding(text2)
        
        return self._cosine_similarity(emb1, emb2)
    
    def compute_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """计算文本列表之间的相似度矩阵
        
        Args:
            texts: 文本列表
            
        Returns:
            相似度矩阵 (n_texts x n_texts)
        """
        if len(texts) < 2:
            return np.array([[1.0]]) if texts else np.array([])
        
        embeddings = self.compute_embeddings_batch(texts)
        
        # 计算余弦相似度矩阵
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_norm = embeddings / (norm + 1e-8)
        similarity_matrix = np.dot(embeddings_norm, embeddings_norm.T)
        
        return similarity_matrix
    
    def find_similar_pairs(self, 
                          texts: List[str], 
                          threshold: float = 0.85) -> List[Tuple[int, int, float]]:
        """找到相似度超过阈值的文本对
        
        Args:
            texts: 文本列表
            threshold: 相似度阈值
            
        Returns:
            相似文本对列表 [(index1, index2, similarity), ...]
        """
        if len(texts) < 2:
            return []
        
        similarity_matrix = self.compute_similarity_matrix(texts)
        similar_pairs = []
        
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                sim = similarity_matrix[i, j]
                if sim >= threshold:
                    similar_pairs.append((i, j, float(sim)))
        
        return similar_pairs
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算两个向量的余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def clear_cache(self):
        """清空嵌入缓存"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")


def create_matcher(api_key: Optional[str] = None,
                   base_url: Optional[str] = None,
                   model: str = "text-embedding-3-large") -> SemanticMatcher:
    """工厂函数，创建语义匹配器"""
    # 使用默认的 base_url 如果未提供
    actual_base_url = base_url or OPENAI_BASE_URL or "https://api.openai.com/v1"
    return SemanticMatcher(
        api_key=api_key,
        base_url=actual_base_url,
        model=model
    )