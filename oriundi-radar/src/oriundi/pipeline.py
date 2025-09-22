diff --git a//dev/null b/oriundi-radar/src/oriundi/pipeline.py
index 0000000000000000000000000000000000000000..4eb2fb359cf9a5754a561ad6a2fea0561c556898 100644
--- a//dev/null
+++ b/oriundi-radar/src/oriundi/pipeline.py
@@ -0,0 +1,97 @@
+"""High-level orchestration for the Oriundi pipeline."""
+
+from __future__ import annotations
+
+import json
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Sequence
+
+from .config import OriundiSettings
+from .data_sources import (
+    AnyCrawlSearchSource,
+    DataSource,
+    HistoricalRosterSource,
+    OpenRegistrySource,
+)
+from .data_sources.base import RecordBatch
+from .enrichment import GeoEligibilityModel, enrich_with_social_signals
+from .graph import build_graph, export_graph
+from .processing import normalize_candidates, resolve_candidates
+
+
+@dataclass(slots=True)
+class PipelineResult:
+    resolved_records: RecordBatch
+    graph_path: Path
+    resolved_path: Path
+
+
+class OriundiPipeline:
+    """Composable ETL pipeline for oriundi scouting."""
+
+    def __init__(
+        self,
+        settings: OriundiSettings,
+        sources: Sequence[DataSource] | None = None,
+    ) -> None:
+        self.settings = settings
+        self.settings.ensure_directories()
+        self.sources = list(sources) if sources is not None else self._default_sources()
+
+    def _default_sources(self) -> list[DataSource]:
+        sources: list[DataSource] = []
+        if self.settings.historical.enabled:
+            sources.append(HistoricalRosterSource(self.settings.historical))
+        if self.settings.anycrawl.enabled and self.settings.anycrawl.key:
+            sources.append(
+                AnyCrawlSearchSource(
+                    self.settings.anycrawl, self.settings.queries, pages=1, limit=25
+                )
+            )
+        if self.settings.registry.enabled:
+            sources.append(OpenRegistrySource(self.settings.registry))
+        return sources
+
+    def run(self) -> PipelineResult:
+        raw_batches = []
+        for source in self.sources:
+            raw_batches.extend(source.fetch())
+
+        normalized = normalize_candidates(raw_batches)
+        enriched = enrich_with_social_signals([normalized])
+        geo_model = GeoEligibilityModel(self.settings.ml)
+        enriched = geo_model.annotate_batch(enriched)
+        resolved = resolve_candidates(enriched, threshold=self.settings.ml.fuzzy_threshold)
+        graph = build_graph(resolved)
+        export_graph(graph, self.settings.storage.graph_store_path)
+        self._persist_to_duckdb(resolved)
+        export_path = self._export_resolved(resolved)
+        return PipelineResult(
+            resolved_records=resolved,
+            graph_path=self.settings.storage.graph_store_path,
+            resolved_path=export_path,
+        )
+
+    def _export_resolved(self, records: RecordBatch) -> Path:
+        export_path = self.settings.storage.export_dir / "resolved_candidates.json"
+        export_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
+        return export_path
+
+    def _persist_to_duckdb(self, records: RecordBatch) -> None:
+        if not records:
+            return
+        try:
+            import duckdb  # type: ignore
+        except ImportError:  # pragma: no cover - optional dependency
+            return
+        con = duckdb.connect(str(self.settings.storage.duckdb_path))
+        con.execute("CREATE TABLE IF NOT EXISTS candidates (payload JSON)")
+        con.execute("DELETE FROM candidates")
+        for record in records:
+            con.execute("INSERT INTO candidates VALUES (?)", [json.dumps(record)])
+        con.close()
+
+
+__all__ = ["OriundiPipeline", "PipelineResult"]
+
