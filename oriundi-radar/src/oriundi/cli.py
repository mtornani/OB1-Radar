"""CLI entrypoint for the Oriundi pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import OriundiSettings
from .pipeline import OriundiPipeline

app = typer.Typer(help="Pipeline per scouting oriundi FSGC")


@app.command()
def run(config: Optional[Path] = typer.Option(None, help="Percorso file di configurazione")) -> None:
    """Esegue la pipeline end-to-end."""

    settings = OriundiSettings.from_file(config) if config else OriundiSettings()
    pipeline = OriundiPipeline(settings)
    result = pipeline.run()
    typer.echo(f"Export completato: {result.graph_path}")


if __name__ == "__main__":  # pragma: no cover
    app()

