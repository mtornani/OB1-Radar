# Daily Kickoff · 2025-09-18

## Focus mix (90' + 90')
- **[FIEND][OB1] Region Gate Rework (South America + Africa)**  
  - **Obiettivo 90'**: mappare errori attuali sul radar giornaliero, definire matrice paese→fonti e impostare checklist test automatizzabile.  
  - **Steps**: 1) Audit di `docs/daily-2025-09-18.json` per classificare falsi positivi/"unknown". 2) Tracciare fonti affidabili per Brasile, Argentina, Nigeria, Sudafrica (≥3 totali). 3) Disegnare bozza `reports/region-gate-rework-sa-africa.md` con sezione DoD e schema test.  
  - **Deliverable mattutino**: outline del report + tabella mapping in `engine/` (draft) pronta per hardening pomeridiano.

- **[FIREFLY][OB1] Daily Signal Report v1 (MD+PDF)**  
  - **Obiettivo 90'**: produrre versione MD con almeno 3 segnali solidi (Why + fonti) e definire comando export → PDF.  
  - **Steps**: 1) Selezionare 3 highlight dal radar odierno (es. Botafogo Sub-20, Sudamericano Sub-20 kickoff, Luca de la Torre loan). 2) Scrivere sezioni Why it matters per target club A (Salzburg/St. Pauli). 3) Documentare export rapido (`pandoc` fallback) in `docs/runbooks/report-export.md`.  
  - **Deliverable serale**: `reports/report-2025-09-18.md` + PDF allegato, snippet bilingue preparato con template.

## Radar snapshot (docs/daily-2025-09-18.json)
- **Botafogo Sub-20 debut** – opportunità pipeline youth Brasile (score 98.6).  
- **Sudamericano Sub-20 kickoff** – calendario e scouting centralizzato CONMEBOL (score 95.7).  
- **Luca de la Torre → San Diego FC loan** – ponte MLS/Europa utile per Parma/St. Pauli (score 32.3 ma impatto commerciale).

## Next moves
1. Avviare audit gate regione su dataset storico (`data/` + daily odierno).  
2. Bloccare slot export report e validare tool PDF entro le 15:00 CET.  
3. Preparare bozza DM per target lista A basata su highlight n.1.
