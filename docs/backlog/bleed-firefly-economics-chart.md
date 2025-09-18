# [BLEED][FIREFLY] Economics chart + Investment Ratio nel PDF

## Goal
Integrare un grafico dei costi settimanali con Investment Ratio nel report PDF corrente.

## Why (impact)
- Rende immediata la lettura della redditività del tempo speso vs ritorno.
- Alimenta conversazioni con CFO/owner con un asset visivo pronto da condividere.

## Definition of Done
- [ ] Dataset aggregato in `data/bleed/weekly_costs.csv` con colonne validate.
- [ ] Grafico generato via notebook o script in `analytics/bleed/economics_chart.ipynb` con esportazione SVG.
- [ ] Report settimanale aggiornato con sezione dedicata e spiegazione del KPI Investment Ratio.
- [ ] Runbook aggiornato in `docs/runbooks/bleed-report.md` per replicare la generazione.

## Deliverable
`reports/bleed-weekly-<DATA>.pdf` contenente grafico e analisi Investment Ratio.

## Notes
Coordinarsi con team finance per definire soglie di alert automatici.

## Labels
BLEED, FIREFLY
