# Conflict Resolution

## OVERVIEW
Two-phase semantic conflict detection: embedding similarity + position overlap to identify annotations requiring human clarification.

## STRUCTURE
```
conflict_resolution/
├── conflict_detector.py    # Main orchestrator, coordinates matching and clustering
├── semantic_matcher.py     # Embedding similarity with sentence-transformers
├── cluster_aggregator.py   # DBSCAN clustering (eps=0.3, min_samples=1)
└── __init__.py             # Exports: ConflictDetector, SemanticMatcher, ClusterAggregator
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Tune similarity threshold | `semantic_matcher.py` | Default: 0.85 cosine similarity |
| Adjust clustering | `cluster_aggregator.py` | DBSCAN eps/min_samples params |
| Add conflict type | `conflict_detector.py` | Conflict dataclass extensions |
| Debug matches | `semantic_matcher.py::find_similar_segments()` | Returns (segment, score) tuples |

## CONVENTIONS

### Two-Phase Algorithm
1. **Embedding similarity**: cosine > threshold (0.85)
2. **Position overlap**: character span overlap > 50%
Both must pass for conflict candidacy.

### Clustering Logic
- DBSCAN groups similar segments
- Conflict = cluster containing segments from different `SPLBlockType`
- Same-type overlaps are merged, not conflicts

### Complexity
Optimized O(n^2/K) via embedding pre-filtering vs naive O(n^m) pairwise.

## ANTI-PATTERNS
- **DO NOT** skip position overlap check. Embedding-only matching creates false positives on distant similar phrases.
- **NEVER** mutate annotation segments during matching. Create new Conflict objects instead.
- **AVOID** tuning DBSCAN eps below 0.2. Creates excessive micro-clusters.
- **DO NOT** block on embedding model load. Initialize once in `__init__`.
