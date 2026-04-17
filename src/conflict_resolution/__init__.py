"""冲突检测与解决模块

负责检测多标注器产生的冲突，并通过语义匹配和聚类进行聚合。
"""

from .semantic_matcher import SemanticMatcher
from .conflict_detector import ConflictDetector
from .cluster_aggregator import ClusterAggregator

__all__ = ["SemanticMatcher", "ConflictDetector", "ClusterAggregator"]