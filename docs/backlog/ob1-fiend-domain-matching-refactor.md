# [OB1][FIEND] Domain Matching Refactor + tests

## Goal
Rilasciare una mappa domini normalizzata con copertura test >90% e incremento KPI commit ≥ +20.

## Why (impact)
- Garantisce che i segnali siano attribuiti al club/lega corretta senza duplicati.
- Riduce il debito tecnico accumulato sulle pipeline di matching e migliora la scalabilità.

## Definition of Done
- [ ] Nuova struttura di mapping salvata in `engine/config/domain_map.json` con schema documentato.
- [ ] Test unitari e di integrazione in `engine/tests/` che coprono 20 casi reali.
- [ ] Script di migrazione per dati storici allegato in `scripts/normalize_domains.py`.
- [ ] Dashboard di monitoraggio commit ratio aggiornata in `docs/metrics/domain-matching.md`.

## Deliverable
`docs/metrics/domain-matching.md` con grafici pre/post e link ai test eseguiti.

## Notes
Coordinarsi con il team ingestion per congelare input durante la migrazione.

## Labels
OB1, FIEND
