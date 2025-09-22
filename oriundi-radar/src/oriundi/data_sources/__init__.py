diff --git a//dev/null b/oriundi-radar/src/oriundi/data_sources/__init__.py
index 0000000000000000000000000000000000000000..c91fc090023fa3beb11734ecc5bbaf433e314335 100644
--- a//dev/null
+++ b/oriundi-radar/src/oriundi/data_sources/__init__.py
@@ -0,0 +1,14 @@
+"""Data source interfaces for the Oriundi pipeline."""
+
+from .base import DataSource, SourceMetadata
+from .historical import HistoricalRosterSource
+from .web_search import AnyCrawlSearchSource
+from .open_registry import OpenRegistrySource
+
+__all__ = [
+    "DataSource",
+    "SourceMetadata",
+    "HistoricalRosterSource",
+    "AnyCrawlSearchSource",
+    "OpenRegistrySource",
+]
