from __future__ import annotations

from pathlib import Path

import pytest

from oriundi.config import OriundiSettings
from oriundi.pipeline import OriundiPipeline
from oriundi.data_sources.base import DataSource, RecordBatch


class FakeSource:
    def __init__(self, batch: RecordBatch) -> None:
        self.batch = batch

    def fetch(self):
        return [self.batch]


@pytest.fixture()
def candidate_batch() -> RecordBatch:
    return [
        {
            "player.full_name": "Marco De Rossi",
            "player.birth_date": "2004-05-12",
            "player.birth_place": "Buenos Aires",
            "player.current_club": "Club Atletico",
            "player.position": "MF",
            "article.url": "https://example.com/a",
            "article.text": "Marco De Rossi scored and has Italian heritage.",
        },
        {
            "player.full_name": "Marco DeRossi",
            "player.birth_date": "12/05/2004",
            "player.birth_place": "Buenos Aires",
            "player.current_club": "Club Atletico",
            "player.position": "MF",
            "article.url": "https://example.com/b",
            "article.text": "Il talento argentino Marco De Rossi parla italiano.",
        },
    ]


def test_pipeline_runs_with_fake_source(tmp_path: Path, candidate_batch: RecordBatch) -> None:
    settings = OriundiSettings.from_dict(
        {
            "storage": {
                "duckdb_path": str(tmp_path / "oriundi.duckdb"),
                "graph_store_path": str(tmp_path / "graph.ttl"),
                "export_dir": str(tmp_path),
            },
            "ml": {"fuzzy_threshold": 85},
        }
    )
    pipeline = OriundiPipeline(settings, sources=[FakeSource(candidate_batch)])
    result = pipeline.run()

    assert result.graph_path.exists()
    assert result.resolved_path.exists()
    assert len(result.resolved_records) == 2
    assert any(record["entity.cluster_size"] == 2 for record in result.resolved_records)

