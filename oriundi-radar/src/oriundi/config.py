diff --git a//dev/null b/oriundi-radar/src/oriundi/config.py
index 0000000000000000000000000000000000000000..f5c51c6b1b562f4421cb744d0357537478894dd5 100644
--- a//dev/null
+++ b/oriundi-radar/src/oriundi/config.py
@@ -0,0 +1,167 @@
+"""Configuration models for the Oriundi pipeline."""
+
+from __future__ import annotations
+
+import json
+import os
+from dataclasses import asdict, dataclass, field
+from pathlib import Path
+from typing import Any, Dict, List, Optional
+
+try:  # Python 3.11+
+    import tomllib  # type: ignore
+except ModuleNotFoundError:  # pragma: no cover - fallback
+    import tomli as tomllib  # type: ignore
+
+
+@dataclass
+class APISettings:
+    enabled: bool = True
+    base_url: str = "https://api.anycrawl.dev/v1"
+    key: str = ""
+    rate_limit_per_minute: int = 60
+
+
+@dataclass
+class RegistrySettings:
+    enabled: bool = True
+    base_url: Optional[str] = None
+    max_results: int = 200
+
+
+@dataclass
+class StorageSettings:
+    duckdb_path: Path = Path("data/oriundi.duckdb")
+    graph_store_path: Path = Path("output/oriundi_graph.ttl")
+    export_dir: Path = Path("output")
+
+
+@dataclass
+class MLSettings:
+    enable_language_models: bool = False
+    spacy_model: str = ""
+    fuzzy_threshold: int = 90
+
+
+@dataclass
+class HistoricalRosterSettings:
+    enabled: bool = True
+    path: Path = Path("data/historical_callups.csv")
+    max_rows: int = 100
+
+
+@dataclass
+class OriundiSettings:
+    anycrawl: APISettings = field(default_factory=APISettings)
+    genealogic: APISettings = field(
+        default_factory=lambda: APISettings(base_url="https://api.familysearch.org")
+    )
+    registry: RegistrySettings = field(default_factory=RegistrySettings)
+    storage: StorageSettings = field(default_factory=StorageSettings)
+    ml: MLSettings = field(default_factory=MLSettings)
+    historical: HistoricalRosterSettings = field(default_factory=HistoricalRosterSettings)
+    queries: List[str] = field(
+        default_factory=lambda: [
+            "football U20 dual nationality",
+            "player eligible italian passport",
+            "youth prospect residency san marino",
+        ]
+    )
+
+    @classmethod
+    def from_dict(cls, data: Dict[str, Any]) -> "OriundiSettings":
+        settings = cls()
+        settings._update_from_dict(data)
+        return settings
+
+    @classmethod
+    def from_file(cls, path: Path | str) -> "OriundiSettings":
+        path = Path(path)
+        if not path.exists():
+            raise FileNotFoundError(path)
+        if path.suffix.lower() == ".json":
+            data = json.loads(path.read_text(encoding="utf-8"))
+        elif path.suffix.lower() in {".toml", ".tml"}:
+            data = tomllib.loads(path.read_text(encoding="utf-8"))
+        else:
+            raise ValueError("Formato file non supportato. Usa TOML o JSON.")
+        return cls.from_dict(data)
+
+    @classmethod
+    def from_env(cls, prefix: str = "ORIUNDI_") -> "OriundiSettings":
+        data: Dict[str, Any] = {}
+        for key, value in os.environ.items():
+            if not key.startswith(prefix):
+                continue
+            nested_keys = key[len(prefix) :].lower().split("__")
+            current = data
+            for part in nested_keys[:-1]:
+                current = current.setdefault(part, {})
+            current[nested_keys[-1]] = _coerce_env_value(value)
+        return cls.from_dict(data)
+
+    def ensure_directories(self) -> None:
+        self.storage.export_dir.mkdir(parents=True, exist_ok=True)
+        self.storage.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
+        self.storage.graph_store_path.parent.mkdir(parents=True, exist_ok=True)
+        if self.historical.enabled:
+            Path(self.historical.path).expanduser().parent.mkdir(
+                parents=True, exist_ok=True
+            )
+
+    def _update_from_dict(self, data: Dict[str, Any]) -> None:
+        if "anycrawl" in data:
+            self.anycrawl = _merge_dataclass(APISettings, self.anycrawl, data["anycrawl"])
+        if "genealogic" in data:
+            self.genealogic = _merge_dataclass(
+                APISettings, self.genealogic, data["genealogic"]
+            )
+        if "registry" in data:
+            self.registry = _merge_dataclass(
+                RegistrySettings, self.registry, data["registry"]
+            )
+        if "storage" in data:
+            storage = _merge_dataclass(StorageSettings, self.storage, data["storage"])
+            storage.duckdb_path = Path(storage.duckdb_path)
+            storage.graph_store_path = Path(storage.graph_store_path)
+            storage.export_dir = Path(storage.export_dir)
+            self.storage = storage
+        if "ml" in data:
+            self.ml = _merge_dataclass(MLSettings, self.ml, data["ml"])
+        if "queries" in data:
+            self.queries = list(data["queries"])
+        if "historical" in data:
+            historical = _merge_dataclass(
+                HistoricalRosterSettings, self.historical, data["historical"]
+            )
+            historical.path = Path(historical.path)
+            self.historical = historical
+
+
+def _coerce_env_value(value: str) -> Any:
+    lower = value.lower()
+    if lower in {"true", "false"}:
+        return lower == "true"
+    if lower.isdigit():
+        return int(lower)
+    try:
+        return float(value)
+    except ValueError:
+        return value
+
+
+def _merge_dataclass(cls, current, overrides):
+    values = asdict(current)
+    values.update(overrides)
+    return cls(**values)
+
+
+__all__ = [
+    "APISettings",
+    "RegistrySettings",
+    "StorageSettings",
+    "MLSettings",
+    "HistoricalRosterSettings",
+    "OriundiSettings",
+]
+
