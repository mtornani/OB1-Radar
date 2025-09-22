from __future__ import annotations

from pathlib import Path

from oriundi.config import HistoricalRosterSettings
from oriundi.data_sources.historical import HistoricalRosterSource


def test_historical_roster_source_reads_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "callups.csv"
    csv_path.write_text(
        """
player_name,birth_date,birth_place,current_club,position,team_level,call_up_date,opponent,source_url,scouting_notes
Giulio Verdi,1999-01-20,Roma,Latina Calcio,DF,Senior,2023-10-12,San Marino vs. Nord Irlanda,,Difensore jolly italo-sammarinese.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    settings = HistoricalRosterSettings(enabled=True, path=csv_path, max_rows=10)
    source = HistoricalRosterSource(settings)

    batches = list(source.fetch())
    assert len(batches) == 1
    assert len(batches[0]) == 1
    record = batches[0][0]

    assert record["player.full_name"] == "Giulio Verdi"
    assert record["fsgc.team_level"] == "Senior"
    assert record["__metadata__"].source == "historical_callups"
