# Oriundi Radar Pipeline

Pipeline modulare per supportare la FSGC nell'identificazione di calciatori potenzialmente naturalizzabili (oriundi).

## Caratteristiche principali

- **Ingest** da sorgenti configurabili (SERP AnyCrawl, registri anagrafici open data, ecc.).
- **Normalizzazione** e **entity resolution** con fuzzy matching per aggregare duplicati.
- **Enrichment** opzionale (heuristiche social, NLP spaCy) e scoring geografico.
- **Knowledge graph** esportato in formato Turtle con `networkx` + `rdflib`.
- **Persistenza** in DuckDB e file JSON/Parquet per analisi successive.

## Setup rapido

```bash
cd oriundi-radar
python -m venv .venv && source .venv/bin/activate
pip install -e .  # usa -e .[full] per le dipendenze opzionali
cp config/settings.example.toml config/settings.toml
oriundi-pipeline run --config config/settings.toml
```

Il comando CLI produce `output/resolved_candidates.json` e `output/oriundi_graph.ttl`,
pronti per essere condivisi con analisti e staff federale.

## Struttura della mini-repo

```
oriundi-radar/
├─ pyproject.toml
├─ README.md
├─ config/
│  └─ settings.example.toml
├─ docs/
│  └─ oriundi_architecture.md
├─ src/oriundi/
│  ├─ cli.py
│  ├─ config.py
│  ├─ pipeline.py
│  ├─ data_sources/
│  ├─ enrichment/
│  ├─ graph/
│  └─ processing/
└─ tests/
   └─ test_pipeline.py
```

Per i dettagli architetturali consulta `docs/oriundi_architecture.md`.
