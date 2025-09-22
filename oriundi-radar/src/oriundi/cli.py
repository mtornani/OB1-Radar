"""CLI entrypoint for the Oriundi pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

from .config import OriundiSettings
from .pipeline import OriundiPipeline


def _run_pipeline(config_path: Optional[Path]) -> None:
    settings = OriundiSettings.from_file(config_path) if config_path else OriundiSettings()
    pipeline = OriundiPipeline(settings)
    result = pipeline.run()
    print(f"Export completato: {result.graph_path}")


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="oriundi-pipeline", description="Pipeline per scouting oriundi FSGC"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run"],
        help="Comando da eseguire (solo 'run' supportato)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Percorso file di configurazione JSON/TOML",
    )

    args = parser.parse_args(argv)
    _run_pipeline(args.config)


if __name__ == "__main__":  # pragma: no cover
    main()
