"""冲突检测器

检测并聚合多标注器产生的冲突。
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from ..models import Annotation, Conflict, TextSegment, SPLBlockType
from .semantic_matcher import SemanticMatcher
from .cluster_aggregator import ClusterAggregator, Cluster

logger = logging.getLogger(__name__)


class ConflictDetector:
    """冲突检测器
    
    两阶段检测策略：
    1. 语义聚类：使用DBSCAN将相似文本聚类
    2. 位置验证：在聚类内部检查位置重叠
    """
    
    def __init__(self, 
                 semantic_matcher: SemanticMatcher = None,
                 cluster_aggregator: ClusterAggregator = None,
                 similarity_threshold: float = 0.85,
                 overlap_threshold: float = 0.5,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        """初始化冲突检测器
        
        Args:
            semantic_matcher: 语义匹配器
            cluster_aggregator: 聚类聚合器
            similarity_threshold: 语义相似度阈值
            overlap_threshold: 位置重叠度阈值
            api_key: OpenAI API密钥
            base_url: API基础URL
        """
        self.semantic_matcher = semantic_matcher or SemanticMatcher(
            api_key=api_key,
            base_url=base_url
        )
        self.cluster_aggregator = cluster_aggregator or ClusterAggregator(
            semantic_matcher=self.semantic_matcher
        )
        self.similarity_threshold = similarity_threshold
        self.overlap_threshold = overlap_threshold
    
    def detect_conflicts(self, 
                        annotations: Dict[SPLBlockType, Annotation]) -> Tuple[List[Conflict], Dict[SPLBlockType, Annotation]]:
        """检测冲突并返回无冲突的标注
        
        Args:
            annotations: 各SPL块的标注结果
            
        Returns:
            (冲突列表, 无冲突的标注字典)
        """
        logger.info(f"Starting conflict detection from {len(annotations)} block types")
        
        # 1. 提取所有文本片段
        all_segments = self._extract_all_segments(annotations)
        logger.info(f"Extracted {len(all_segments)} total segments")
        
        if not all_segments:
            return [], annotations
        
        # 2. 语义聚类
        clusters = self.cluster_aggregator.aggregate(all_segments)
        logger.info(f"Formed {len(clusters)} semantic clusters")
        
        # 3. 位置验证和合并
        clusters = self.cluster_aggregator.merge_clusters_by_position(
            clusters, self.overlap_threshold
        )
        logger.info(f"After position merging: {len(clusters)} clusters")
        
        # 4. 识别冲突聚类（包含多个标签的聚类）
        conflicting_clusters = self.cluster_aggregator.get_conflicting_clusters(clusters)
        logger.info(f"Found {len(conflicting_clusters)} conflicting clusters")
        
        # 5. 构建冲突对象
        conflicts = self._build_conflicts(conflicting_clusters, annotations)
        
        # 6. 提取无冲突的标注
        clean_annotations = self._extract_clean_annotations(
            clusters, conflicting_clusters, annotations
        )
        
        logger.info(f"Conflict detection complete: {len(conflicts)} conflicts, "
                   f"{len(clean_annotations)} clean blocks")
        
        return conflicts, clean_annotations
    
    def _extract_all_segments(self, 
                               annotations: Dict[SPLBlockType, Annotation]) -> List[TextSegment]:
        """提取所有标注中的文本片段"""
        all_segments = []
        
        for block_type, annotation in annotations.items():
            for segment in annotation.segments:
                # 添加块类型信息到片段
                segment_copy = TextSegment(
                    content=segment.content,
                    start_pos=segment.start_pos,
                    end_pos=segment.end_pos,
                    source=f"{block_type.value}_annotator"
                )
                all_segments.append(segment_copy)
        
        return all_segments
    
    def _build_conflicts(self, 
                        conflicting_clusters: List[Cluster],
                        annotations: Dict[SPLBlockType, Annotation]) -> List[Conflict]:
        """从冲突聚类构建Conflict对象"""
        conflicts = []
        
        for cluster in conflicting_clusters:
            # 提取候选标签
            candidate_labels = self._extract_candidate_labels(cluster.labels)
            
            if len(candidate_labels) < 2:
                continue
            
            # 计算置信度分数
            confidence_scores = self._calculate_confidence_scores(
                cluster, candidate_labels, annotations
            )
            
            conflict = Conflict(
                segments=cluster.segments,
                candidate_labels=candidate_labels,
                confidence_scores=confidence_scores,
                resolution=None
            )
            
            conflicts.append(conflict)
        
        return conflicts
    
    def _extract_candidate_labels(self, labels: Set[str]) -> List[SPLBlockType]:
        """从标签字符串中提取SPLBlockType"""
        candidate_labels = []
        
        for label in labels:
            # 从标签字符串（如"persona_annotator"）提取块类型
            for block_type in SPLBlockType:
                if block_type.value in label.lower():
                    candidate_labels.append(block_type)
                    break
        
        # 去重并保持顺序
        seen = set()
        unique_labels = []
        for label in candidate_labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)
        
        return unique_labels
    
    def _calculate_confidence_scores(self,
                                     cluster: Cluster,
                                     candidate_labels: List[SPLBlockType],
                                     annotations: Dict[SPLBlockType, Annotation]) -> Dict[SPLBlockType, float]:
        """计算每个候选标签的置信度分数"""
        scores = {}
        
        for label in candidate_labels:
            if label in annotations:
                # 使用原始标注的置信度
                scores[label] = annotations[label].confidence
            else:
                # 基于片段数量估算
                scores[label] = 0.5
        
        return scores
    
    def _extract_clean_annotations(self,
                                   clusters: List[Cluster],
                                   conflicting_clusters: List[Cluster],
                                   annotations: Dict[SPLBlockType, Annotation]) -> Dict[SPLBlockType, Annotation]:
        """提取无冲突的标注"""
        # 找出冲突的块类型
        conflicting_types = set()
        for cluster in conflicting_clusters:
            for label in cluster.labels:
                for block_type in SPLBlockType:
                    if block_type.value in label.lower():
                        conflicting_types.add(block_type)
                        break
        
        # 提取无冲突的标注
        clean_annotations = {}
        
        for block_type, annotation in annotations.items():
            if block_type not in conflicting_types:
                # 这个块类型没有冲突，保留整个标注
                clean_annotations[block_type] = annotation
            else:
                # 这个块类型有冲突，只保留无冲突的片段
                clean_segments = self._get_clean_segments(
                    block_type, annotation, conflicting_clusters
                )
                
                if clean_segments:
                    from dataclasses import replace
                    clean_annotations[block_type] = replace(
                        annotation,
                        segments=clean_segments,
                        extracted_content="\n\n".join(s.content for s in clean_segments)
                    )
        
        return clean_annotations
    
    def _get_clean_segments(self,
                           block_type: SPLBlockType,
                           annotation: Annotation,
                           conflicting_clusters: List[Cluster]) -> List[TextSegment]:
        """获取该块类型中无冲突的片段"""
        # 找出所有冲突片段
        conflicting_segments = set()
        for cluster in conflicting_clusters:
            for seg in cluster.segments:
                conflicting_segments.add(id(seg))
        
        # 保留不在冲突中的片段
        clean_segments = [
            seg for seg in annotation.segments
            if id(seg) not in conflicting_segments
        ]
        
        return clean_segments
    
    def resolve_conflict(self, 
                        conflict: Conflict, 
                        resolved_label: SPLBlockType) -> Annotation:
        """解决冲突，生成最终的标注
        
        Args:
            conflict: 冲突对象
            resolved_label: 用户选择的标签
            
        Returns:
            解决后的标注
        """
        conflict.resolution = resolved_label
        
        return Annotation(
            block_type=resolved_label,
            segments=conflict.segments,
            confidence=conflict.confidence_scores.get(resolved_label, 0.7),
            extracted_content="\n\n".join(s.content for s in conflict.segments),
            metadata={"resolved_from_conflict": True, "original_candidates": [c.value for c in conflict.candidate_labels]}
        )