# OB1 • Ouroboros Radar — Mobile MVP

Radar di anomalie calcistiche. Ogni giorno genera `daily.json` e lo pubblica su GitHub Pages con una UI mobile-first.

**Live (esempio):** `https://<tuo-utente>.github.io/OB1-Radar/`  
_Publishing: branch `main`, cartella `/docs`._

---

## Struttura

├─ .github/workflows/daily.yml # CI: esegue il motore, copia, commit & push
├─ engine/run.py # motore: genera output/daily.json
└─ docs/
├─ index.html # UI (vanilla JS, mobile-first)
└─ daily.json # file generato dalla CI


---

## Quick start (3 mosse)

1) **GitHub Pages** → `Settings → Pages` → Source: `main` + Folder: `/docs`.  
2) **Permessi CI** → `Settings → Actions → General` → Workflow permissions: **Read and write** (salva).  
3) **Secrets** (repo) → `Settings → Secrets and variables → Actions` → `New repository secret`:
   - `ANYCRAWL_API_URL` → es. `https://api.anycrawl.dev`
   - `ANYCRAWL_API_KEY` → **la tua key AnyCrawl**
   - _(opzionale)_ `SHEET_CSV_URL` → URL CSV di una Google Sheet pubblicata

Poi vai su **Actions → Daily Anomaly Radar → Run workflow**. La CI creerà/aggiornerà `docs/daily.json` e la pagina si aggiornerà.

---

## Impostare la **AnyCrawl API key**

**A. Nel repository (CI):**
1. Repo → **Settings → Secrets and variables → Actions** → **New repository secret**  
2. Crea:
   - **Name:** `ANYCRAWL_API_URL` • **Value:** `https://api.anycrawl.dev` (o la tua istanza)
   - **Name:** `ANYCRAWL_API_KEY` • **Value:** _incolla qui la tua API key_
3. Salva. La CI userà automaticamente questi valori in `daily.yml`.

**B. In locale (sviluppo):**
```bash
pip install requests
export ANYCRAWL_API_URL="https://api.anycrawl.dev"
export ANYCRAWL_API_KEY="<LA-TUA-KEY>"
# opzionale:
# export SHEET_CSV_URL="https://docs.google.com/.../pub?output=csv"
python engine/run.py
# → genera output/daily.json

C. Test veloce della key con cURL (scrape):
curl -X POST "https://api.anycrawl.dev/v1/scrape" \
  -H "Authorization: Bearer <LA-TUA-KEY>" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","engine":"cheerio"}'

Se la key è valida, ricevi un JSON con data.markdown/data.text.

Come funziona il motore
engine/run.py segue questa priorità:

Google Sheet CSV (SHEET_CSV_URL) → parsing in Top-10

AnyCrawl API (/v1/scrape + semplice scoring testuale)

Fallback → 10 elementi demo (così la CI non fallisce mai)

Scrive output/daily.json (con generated_at_utc) → la CI lo copia in docs/daily.json.

CI/CD
daily.yml fa: install deps → python engine/run.py → copia output/daily.json in docs/ → commit & push (serve contents: write).

Trigger: manuale (workflow_dispatch) e giornaliero 07:00 UTC (≈ 09:00 CEST in estate). Ritardi di qualche minuto sono normali.

Accettazione (checklist)
Pages: https://<tuo-utente>.github.io/OB1-Radar/ mostra la lista (Top-10).

docs/daily.json è valido (campo generated_at_utc presente).

In Actions vedi il commit “update daily.json” ad ogni run.

Filtri UI (search / entity / type) rispondono da mobile.

Troubleshooting
404 su Pages → controlla Source main / folder /docs e che esista docs/index.html.

Commit/push fallisce → abilita “Read and write permissions” e verifica permissions: contents: write nel workflow.

API key non accettata → ritesta con cURL; verifica di non avere spazi extra o virgolette sbagliate; ripeti il run Actions.

Note
AnyCrawl è una RESTful API: endpoint chiave /v1/scrape (engines: cheerio, playwright, puppeteer), output JSON con data.markdown/data.text.

GitHub Pages può pubblicare da main//docs.

I workflow schedule girano in UTC; il token GITHUB_TOKEN usa permessi configurabili (principio del minimo privilegio).

## Mini-repo pipeline oriundi

Il codice sperimentale per l'identificazione degli oriundi ora vive in `oriundi-radar/`.
Consulta `oriundi-radar/README.md` per setup e dettagli architetturali.

