# OB1 Ouroboros Product Loop

## Cosa consegniamo
- Report executive giornaliero (HTML + PDF) con 3 schede prioritarie e fonti citate.
- Pacchetto go-to-market: post LinkedIn bilingue, email commerciale A/B, pricing test.
- Log operativo + metriche AARRR per iterare il ciclo build–measure–learn.

## Target e perché pagano
- **Direttori Sportivi / Head of Scouting**: riducono da giorni a ore il tempo per validare spike prestativi, evitando trasferte inutili.
- **Responsabili Academy**: riallocano budget sviluppo in base a convocazioni e picchi U20.
- **Analyst Lead**: ottengono clip list e checklist azionabili per comunicare con board e staff tecnico.

## Jobs To Be Done
1. Quando esplode un torneo giovanile internazionale, vogliono identificare in 48h gli U20 realmente in crescita per decidere se inviare un osservatore (target: shortlist <48h, >80% approvazione DT).
2. Quando emergono voci di trasferimento U23, vogliono validare affidabilità e costo prima dei competitor (target: verifica <24h, accuracy valutazioni >=85%).
3. Quando pianificano roster U20, vogliono sapere dove allocare budget sviluppo e minutaggio (target: aggiornamento <72h, riallocazione >=30%).

**Perché pagano**: il radar trasforma feed dispersivi in pacchetti decision-ready, con metriche che mostrano impatto su tempo di scouting, accuratezza economica e sviluppo talenti.

## MVP commerciale
- Trial 7 giorni.
- 3 report consegnati + 1 call di allineamento (30').
- Accesso dashboard AARRR e supporto Slack/email.

## KPI settimanali (AARRR)
- **Acquisition**: impression LinkedIn, visite landing.
- **Activation**: CTR post, reply rate email.
- **Revenue**: conversione trial→paid, ARPA.
- **Retention**: % clienti che richiedono secondo report entro 2 settimane.
- **Referral**: mention “referral” nelle risposte.

### Decisione Pivot/Persevere
- **Persevere** se: trial→paid >=25%, second_report_rate >=60%, referral mention >=2/mese.
- **Pivot** se: CTR <3% per due settimane, trial→paid <15%, board feedback richiede insight diversi (es. injury analytics).

## Come usare il pacchetto
1. Consumare `dist/report.html`/`report.pdf` per briefing quotidiano con staff tecnico.
   - Rigenerare il PDF con rendering fedele all'HTML eseguendo `python engine/render_report_pdf.py` (script standalone, nessuna dipendenza extra).
2. Pubblicare il post LinkedIn bilingue coordinato con invio email (varianti A/B) e monitorare metriche in `dist/metrics.json`.
3. Registrare ogni decisione o esclusione nel log `logs/run.log` per alimentare retrospettiva.
4. Aggiornare prezzi/CTA in `dist/gtm_assets.json` sulla base dei dati AARRR e feedback clienti.
