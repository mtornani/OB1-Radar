# Oriundi Radar Pipeline

Pipeline modulare per supportare la FSGC nell'identificazione di calciatori potenzialmente naturalizzabili (oriundi).
È pensata per funzionare anche senza integrazioni esterne grazie a uno storico CSV
incluso nella repo, utile quando GitHub segnala conflitti o si lavora da ambienti
offline.

## Caratteristiche principali

- **Ingest** da sorgenti configurabili (storico convocazioni locale, SERP AnyCrawl, registri open data, ecc.).
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

## Modalità offline con lo storico convocazioni

Se non hai fonti esterne disponibili puoi far girare la pipeline solo sui tuoi archivi
di convocazioni recenti:

1. Duplica `data/historical_callups.sample.csv` in `data/historical_callups.csv` e
   popola fino a ~100 righe con le ultime convocazioni (Senior + U21). Ogni riga
   rappresenta un giocatore/convocazione con note opzionali.
2. Aggiorna `config/settings.toml` impostando `anycrawl.enabled = false` e lasciando
   `historical.enabled = true` (eventualmente regola `max_rows` se vuoi espandere o
   restringere la finestra temporale).
3. Esegui `oriundi-pipeline run --config config/settings.toml`: il motore userà il
   CSV locale come sorgente primaria, arricchendo i record con punteggi social/NLP e
   raggruppando i duplicati in base ai dati anagrafici.

Lo stesso file CSV può essere aggiornato manualmente dopo ogni finestra
internazionale, mantenendo uno storico progressivo senza dover dipendere da API
esterne.

## Esecuzione via GitHub Actions

Per avviare la pipeline anche da mobile (o senza shell locale) puoi usare il
workflow manuale `Oriundi Radar Pipeline` definito in
`.github/workflows/oriundi-radar.yml`.

1. Apri le impostazioni della repository su GitHub e aggiungi i secret che ti
   servono:
   - `ORIUNDI_ANYCRAWL_KEY` (obbligatorio per interrogare AnyCrawl).
   - opzionali: `ORIUNDI_ANYCRAWL_URL`, `ORIUNDI_ANYCRAWL_RATE_LIMIT`,
     `ORIUNDI_GENEALOGIC_KEY`, `ORIUNDI_GENEALOGIC_URL` per endpoint/quote
     personalizzati.
2. Vai in **Actions → Oriundi Radar Pipeline → Run workflow** e scegli le
   opzioni:
   - `use_sample_data` è attivo di default e fa girare la pipeline in modalità
     offline (nessuna chiamata esterna, utile per smoke test rapidi).
   - imposta `use_sample_data` a `false` per utilizzare le fonti reali,
     opzionalmente fornendo query personalizzate (una per riga) e attivando i
     registri open data (`registry_enabled` + `registry_base_url`).
   - `fuzzy_threshold` permette di regolare la sensibilità del clustering.
3. A fine esecuzione troverai gli artefatti scaricabili (`oriundi-radar-output`)
   che includono `output/resolved_candidates.json`, `output/oriundi_graph.ttl` e
   una copia redatta della configurazione usata.

Il workflow installa automaticamente il pacchetto con le dipendenze opzionali,
genera un file di configurazione temporaneo e lancia `oriundi-pipeline run`.
Puoi quindi farlo partire anche da smartphone/tablet senza dover preparare un
ambiente locale.

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
