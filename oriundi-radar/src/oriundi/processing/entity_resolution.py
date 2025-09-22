"""Entity resolution utilities for candidate consolidation."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List

from ..data_sources.base import RecordBatch


@dataclass(frozen=True)
class ResolutionResult:
    """Cluster metadata for resolved entities."""

    canonical_name: str
    score: float
    members: List[int]


def resolve_candidates(records: RecordBatch, threshold: int = 90) -> RecordBatch:
    """Perform simple clustering using difflib ratio."""

    if not records:
        return []
    visited: set[int] = set()
    clusters: list[ResolutionResult] = []
    for idx, record in enumerate(records):
        if idx in visited:
            continue
        canonical = record.get("player.full_name", "").strip()
        members = [idx]
        for other_idx in range(idx + 1, len(records)):
            if other_idx in visited:
                continue
            other_name = records[other_idx].get("player.full_name", "").strip()
            if not other_name:
                continue
            score = SequenceMatcher(None, canonical.lower(), other_name.lower()).ratio() * 100
            if score >= threshold:
                members.append(other_idx)
                visited.add(other_idx)
                canonical = _merge_names(canonical, other_name)
        visited.add(idx)
        clusters.append(
            ResolutionResult(
                canonical_name=canonical or record.get("player.full_name", ""),
                score=1.0,
                members=members,
            )
        )
    resolved: RecordBatch = []
    for cluster_idx, cluster in enumerate(clusters, start=1):
        for member_idx in cluster.members:
            updated = dict(records[member_idx])
            updated["entity.canonical_name"] = cluster.canonical_name
            updated["entity.cluster_id"] = f"C{cluster_idx:03d}"
            updated["entity.cluster_size"] = len(cluster.members)
            resolved.append(updated)
    return resolved


def _merge_names(name_a: str, name_b: str) -> str:
    parts = set(filter(None, (name_a or "").split() + (name_b or "").split()))
    return " ".join(sorted(parts))


__all__ = ["resolve_candidates", "ResolutionResult"]

