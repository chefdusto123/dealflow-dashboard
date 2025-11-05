# Dealflow Dashboard (Automated Daily)

A lightweight, code-first pipeline that **collects, scores, and displays** small-business listings (pubs/hotels, caravan parks, car washes, bottleshops, etc.) with a single-file HTML dashboard.

## What's inside
- `pipeline.py` — daily fetch via Google **SerpAPI** queries (no fragile scraping), normalization + scoring, writes `data/deals.json` and `data/latest.csv`
- `sites.yaml` — sources & queries (AU focused)
- `scoring_config.json` — weights for the scoring model
- `dashboard.html` — interactive table + KPIs (open in any browser)
- `.github/workflows/dealflow.yml` — **GitHub Actions** cron job to run the pipeline daily and publish to GitHub Pages

## Quick start (local)
1. Create a virtual env and install deps:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install serpapi python-dateutil pydantic pyyaml pandas
   ```
2. Set your SerpAPI key:
   ```bash
   export SERPAPI_API_KEY=YOUR_KEY
   ```
3. Run the pipeline:
   ```bash
   python pipeline.py
   ```
4. Open the dashboard:
   - Double-click `dashboard.html` (it reads `data/deals.json` from the local folder)

## Make it automatic (GitHub Actions + Pages)
1. Create a new GitHub repo and push this folder.
2. In the repo **Settings → Secrets → Actions**, add `SERPAPI_API_KEY`.
3. Enable **Pages** (deploy from `gh-pages` branch).
4. The workflow below runs **daily at 6am AEST**, commits fresh data, and publishes the dashboard at your Pages URL.

## Enriching data
- Swap/add sources in `sites.yaml` (ResortBrokers, HTL Property, CRE Brokers, Seek Business, BusinessesForSale, AnyBusiness, CommercialRealEstate, CBRE/JLL Hotels, Gumtree, etc.).
- For structured pages (e.g., CRE Brokers listing pages), use **Apify actors** and drop JSON outputs into `data/` before scoring.

## Next steps
- Push to **Airtable/Notion** for collaboration.
- Add **email/Slack** alerts for new >0.75 score.
- Add **geocoding** for distances (Google Maps API or Pelias).
- Extend scoring with cap rates, lease terms, EGMs, DA potential, seasonal occupancy, etc.
- Plug in your own **investment mandate filters** (price range, freehold bias, EBITDA floor, within 3hrs drive, etc.).

---
*(Generated 2025-11-05 05:36)*
