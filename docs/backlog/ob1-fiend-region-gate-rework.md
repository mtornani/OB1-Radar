# [OB1][FIEND] Region Gate Rework (South America + Africa)

## Goal
Ridurre i falsi positivi del gate regionale per Sud America e Africa sotto il 10% con test di regressione automatici.

## Why (impact)
- Stabilizza il radar su due mercati chiave evitando alert inutili.
- Libera tempo analista da triage manuale e aumenta la fiducia nei segnali inviati ai club.

## Definition of Done
- [ ] Nuove regole documentate in `docs/anomaly_rules.md` con esempi per paese.
- [ ] Suite di test aggiornata in `engine/` con copertura per scenari Sud America e Africa.
- [ ] Report comparativo pre/post con tasso falsi positivi ≤10% allegato in `reports/`.
- [ ] 3 fonti dati validate per ciascun paese monitorato e citate nel report tecnico.

## Deliverable
`reports/region-gate-rework-sa-africa.md` con riepilogo dei risultati e link ai test.

## Notes
Coordinarsi con data ingestion per sincronizzare nuovi mapping paese prima del deploy.

## Labels
OB1, FIEND
