"""Data processing utilities for Oriundi."""

from .normalization import normalize_candidates
from .entity_resolution import resolve_candidates

__all__ = ["normalize_candidates", "resolve_candidates"]
