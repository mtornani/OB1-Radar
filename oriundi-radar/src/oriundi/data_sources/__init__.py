"""Data source interfaces for the Oriundi pipeline."""

from .base import DataSource, SourceMetadata
from .historical import HistoricalRosterSource
from .web_search import AnyCrawlSearchSource
from .open_registry import OpenRegistrySource

__all__ = [
    "DataSource",
    "SourceMetadata",
    "HistoricalRosterSource",
    "AnyCrawlSearchSource",
    "OpenRegistrySource",
]
