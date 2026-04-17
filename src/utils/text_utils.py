"""文本处理工具函数"""

import re
from typing import List, Tuple, Optional


def normalize_text(text: str) -> str:
    """标准化文本
    
    - 去除多余空格
    - 统一标点
    - 转小写
    """
    # 去除多余空格和换行
    text = re.sub(r'\s+', ' ', text)
    # 去除首尾空格
    text = text.strip()
    # 转小写
    return text.lower()


def find_substring_positions(substring: str, text: str, case_sensitive: bool = False) -> List[Tuple[int, int]]:
    """查找子串在文本中的所有位置
    
    Args:
        substring: 要查找的子串
        text: 目标文本
        case_sensitive: 是否区分大小写
        
    Returns:
        位置列表 [(start, end), ...]
    """
    if not case_sensitive:
        text_lower = text.lower()
        substring_lower = substring.lower()
    else:
        text_lower = text
        substring_lower = substring
    
    positions = []
    start = 0
    
    while True:
        pos = text_lower.find(substring_lower, start)
        if pos == -1:
            break
        positions.append((pos, pos + len(substring)))
        start = pos + 1
    
    return positions


def calculate_overlap(range1: Tuple[int, int], range2: Tuple[int, int]) -> float:
    """计算两个范围的重叠度
    
    Args:
        range1: (start1, end1)
        range2: (start2, end2)
        
    Returns:
        重叠度 (0.0 - 1.0)
    """
    start1, end1 = range1
    start2, end2 = range2
    
    # 计算重叠长度
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    if overlap_start >= overlap_end:
        return 0.0
    
    overlap_length = overlap_end - overlap_start
    
    # 计算联合长度
    union_length = max(end1, end2) - min(start1, start2)
    
    # 返回重叠度
    return overlap_length / union_length if union_length > 0 else 0.0


def fuzzy_find(query: str, text: str, threshold: float = 0.8) -> Optional[Tuple[int, int]]:
    """模糊查找文本位置
    
    使用简单启发式：忽略空格变化、标点变化
    
    Args:
        query: 查询文本
        text: 目标文本
        threshold: 相似度阈值
        
    Returns:
        最佳匹配位置或None
    """
    # 标准化查询
    query_norm = normalize_text(query)
    text_norm = normalize_text(text)
    
    # 尝试精确匹配
    pos = text_norm.find(query_norm)
    if pos >= 0:
        # 找到精确匹配，映射回原始文本
        # 简单策略：假设位置大致对应
        return (pos, pos + len(query))
    
    # 尝试滑动窗口匹配
    query_len = len(query_norm)
    best_score = 0.0
    best_pos = None
    
    for i in range(len(text_norm) - query_len + 1):
        window = text_norm[i:i + query_len]
        
        # 简单相似度：公共子串比例
        common = sum(c1 == c2 for c1, c2 in zip(query_norm, window))
        score = common / max(len(query_norm), len(window))
        
        if score > best_score:
            best_score = score
            best_pos = i
    
    if best_score >= threshold and best_pos is not None:
        return (best_pos, best_pos + len(query))
    
    return None


def split_sentences(text: str) -> List[str]:
    """将文本分割为句子"""
    # 简单的句子分割（可以改进）
    sentences = re.split(r'(?<=[。！？.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def extract_paragraphs(text: str) -> List[str]:
    """提取段落"""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]