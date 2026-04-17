"""聚类聚合器

使用DBSCAN聚类算法将语义相似的文本片段聚类。
"""

import logging
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
import numpy as np

from ..models import TextSegment
from .semantic_matcher import SemanticMatcher

logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """聚类结果"""
    cluster_id: int
    segments: List[TextSegment]
    representative: str  # 代表性文本
    labels: Set[str]  # 包含的所有标签


class ClusterAggregator:
    """聚类聚合器
    
    使用DBSCAN算法将语义相似的文本片段聚类到同一组。
    """
    
    def __init__(self, 
                 semantic_matcher: SemanticMatcher,
                 eps: float = 0.3,
                 min_samples: int = 1,
                 metric: str = "cosine"):
        """初始化聚类聚合器
        
        Args:
            semantic_matcher: 语义匹配器
            eps: DBSCAN的邻域半径 (余弦距离，越小越严格)
            min_samples: 最小样本数
            metric: 距离度量
        """
        self.semantic_matcher = semantic_matcher
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric
    
    def aggregate(self, segments: List[TextSegment]) -> List[Cluster]:
        """对文本片段进行聚类
        
        Args:
            segments: 文本片段列表
            
        Returns:
            聚类结果列表
        """
        if not segments:
            return []
        
        if len(segments) == 1:
            return [Cluster(
                cluster_id=0,
                segments=segments,
                representative=segments[0].content,
                labels={segments[0].source}
            )]
        
        # 提取文本内容
        texts = [seg.content for seg in segments]
        
        # 计算嵌入
        logger.info(f"Computing embeddings for {len(segments)} segments")
        embeddings = self.semantic_matcher.compute_embeddings_batch(texts)
        
        # 执行聚类
        logger.info(f"Running DBSCAN clustering (eps={self.eps}, min_samples={self.min_samples})")
        cluster_labels = self._cluster_embeddings(embeddings)
        
        # 构建聚类结果
        clusters = self._build_clusters(segments, cluster_labels)
        
        logger.info(f"Found {len(clusters)} clusters from {len(segments)} segments")
        
        return clusters
    
    def _cluster_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """对嵌入向量进行聚类
        
        Args:
            embeddings: 嵌入矩阵 (n_samples x n_features)
            
        Returns:
            聚类标签数组
        """
        try:
            from sklearn.cluster import DBSCAN
            
            # DBSCAN聚类
            # 注意：DBSCAN使用距离而非相似度，余弦距离 = 1 - 余弦相似度
            clustering = DBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
                metric=self.metric
            )
            
            cluster_labels = clustering.fit_predict(embeddings)
            
            # DBSCAN会将噪声点标记为-1，将它们分配到最近的簇
            cluster_labels = self._handle_noise_points(embeddings, cluster_labels)
            
            return cluster_labels
            
        except ImportError:
            logger.warning("sklearn not installed, using simple similarity clustering")
            return self._simple_clustering(embeddings)
    
    def _handle_noise_points(self, 
                            embeddings: np.ndarray, 
                            labels: np.ndarray) -> np.ndarray:
        """处理噪声点（-1标签），将它们分配到最近的簇
        
        Args:
            embeddings: 嵌入矩阵
            labels: 聚类标签（可能包含-1）
            
        Returns:
            处理后的标签
        """
        noise_mask = labels == -1
        if not np.any(noise_mask):
            return labels
        
        noise_indices = np.where(noise_mask)[0]
        cluster_indices = np.where(~noise_mask)[0]
        
        if len(cluster_indices) == 0:
            # 所有点都是噪声，每个点自成一簇
            return np.arange(len(labels))
        
        # 计算噪声点到所有簇的距离
        for noise_idx in noise_indices:
            noise_emb = embeddings[noise_idx]
            
            # 找到最近的簇
            min_dist = float('inf')
            nearest_cluster = labels[cluster_indices[0]]
            
            for cluster_idx in cluster_indices:
                cluster_emb = embeddings[cluster_idx]
                dist = self._cosine_distance(noise_emb, cluster_emb)
                if dist < min_dist:
                    min_dist = dist
                    nearest_cluster = labels[cluster_idx]
            
            labels[noise_idx] = nearest_cluster
        
        return labels
    
    def _simple_clustering(self, embeddings: np.ndarray, threshold: float = 0.85) -> np.ndarray:
        """简单的基于相似度的聚类（当sklearn不可用时）
        
        Args:
            embeddings: 嵌入矩阵
            threshold: 相似度阈值
            
        Returns:
            聚类标签
        """
        n = len(embeddings)
        labels = np.full(n, -1)
        current_label = 0
        
        # 计算相似度矩阵
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_norm = embeddings / (norm + 1e-8)
        similarity_matrix = np.dot(embeddings_norm, embeddings_norm.T)
        
        for i in range(n):
            if labels[i] != -1:
                continue
            
            # 找到与当前点相似的所有点
            similar_indices = np.where(similarity_matrix[i] >= threshold)[0]
            
            # 分配到同一簇
            for idx in similar_indices:
                if labels[idx] == -1:
                    labels[idx] = current_label
            
            current_label += 1
        
        return labels
    
    def _build_clusters(self, 
                       segments: List[TextSegment], 
                       cluster_labels: np.ndarray) -> List[Cluster]:
        """根据聚类标签构建Cluster对象
        
        Args:
            segments: 原始文本片段
            cluster_labels: 聚类标签
            
        Returns:
            聚类结果列表
        """
        # 按聚类标签分组
        cluster_groups: Dict[int, List[int]] = {}
        for idx, label in enumerate(cluster_labels):
            if label not in cluster_groups:
                cluster_groups[label] = []
            cluster_groups[label].append(idx)
        
        clusters = []
        for cluster_id, indices in sorted(cluster_groups.items()):
            cluster_segments = [segments[i] for i in indices]
            
            # 选择代表性文本（最长的）
            representative = max(cluster_segments, key=lambda s: len(s.content)).content
            
            # 收集所有标签
            labels = set(seg.source for seg in cluster_segments)
            
            clusters.append(Cluster(
                cluster_id=cluster_id,
                segments=cluster_segments,
                representative=representative,
                labels=labels
            ))
        
        return clusters
    
    def _cosine_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦距离"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return 1.0 - similarity
    
    def get_conflicting_clusters(self, clusters: List[Cluster]) -> List[Cluster]:
        """获取包含冲突的聚类（一个聚类包含多个标签）
        
        Args:
            clusters: 所有聚类
            
        Returns:
            包含冲突的聚类
        """
        return [c for c in clusters if len(c.labels) > 1]
    
    def merge_clusters_by_position(self, 
                                   clusters: List[Cluster],
                                   overlap_threshold: float = 0.5) -> List[Cluster]:
        """根据位置重叠合并聚类
        
        如果两个聚类的位置高度重叠，可能是同一内容的不同表述。
        
        Args:
            clusters: 原始聚类
            overlap_threshold: 位置重叠度阈值
            
        Returns:
            合并后的聚类
        """
        if len(clusters) <= 1:
            return clusters
        
        # 计算聚类之间的位置重叠
        merged = []
        merged_flags = [False] * len(clusters)
        
        for i, cluster_i in enumerate(clusters):
            if merged_flags[i]:
                continue
            
            current_cluster = cluster_i
            
            for j in range(i + 1, len(clusters)):
                if merged_flags[j]:
                    continue
                
                cluster_j = clusters[j]
                
                # 计算位置重叠
                if self._clusters_overlap(current_cluster, cluster_j, overlap_threshold):
                    # 合并聚类
                    current_cluster = self._merge_two_clusters(current_cluster, cluster_j)
                    merged_flags[j] = True
            
            merged.append(current_cluster)
        
        return merged
    
    def _clusters_overlap(self, 
                         cluster1: Cluster, 
                         cluster2: Cluster, 
                         threshold: float) -> bool:
        """检查两个聚类是否有显著的位置重叠"""
        from ..utils.text_utils import calculate_overlap
        
        for seg1 in cluster1.segments:
            for seg2 in cluster2.segments:
                overlap = calculate_overlap(
                    (seg1.start_pos, seg1.end_pos),
                    (seg2.start_pos, seg2.end_pos)
                )
                if overlap >= threshold:
                    return True
        
        return False
    
    def _merge_two_clusters(self, cluster1: Cluster, cluster2: Cluster) -> Cluster:
        """合并两个聚类"""
        return Cluster(
            cluster_id=cluster1.cluster_id,
            segments=cluster1.segments + cluster2.segments,
            representative=cluster1.representative if len(cluster1.representative) > len(cluster2.representative) else cluster2.representative,
            labels=cluster1.labels | cluster2.labels
        )