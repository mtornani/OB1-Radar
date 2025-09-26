#!/usr/bin/env python3
"""Entry point for OB1 Radar."""

import sys
from pathlib import Path

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "oriundi-radar" / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))

    try:
        from oriundi_radar import pipeline as legacy_pipeline  # type: ignore
    except ImportError:
        legacy_pipeline = None

    try:
        from oriundi.pipeline import main as pipeline_main
    except ImportError:
        pipeline_main = None

    if pipeline_main:
        pipeline_main()
    elif legacy_pipeline and hasattr(legacy_pipeline, "main"):
        legacy_pipeline.main()
    else:
        print("Running in display-only mode: pipeline unavailable.")
