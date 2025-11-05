#!/usr/bin/env python3
"""
Dealflow pipeline
- Searches multiple AU/NZ/US small-business listing sources daily
- Normalizes results
- Scores and writes /data/deals.json and /data/latest.csv
Requires:
  pip install serpapi python-dateutil pydantic pyyaml pandas
Optional:
  Apify client for structured scrapers (pip install apify-client)
Set env:
  SERPAPI_API_KEY=...
"""
from __future__ import annotations
import os, json, time, math, re, yaml, pandas as pd
from datetime import datetime, timezone
from dateutil import parser
from typing import List, Dict, Any
from serpapi import GoogleSearch

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data")
CFG  = os.path.join(BASE, "scoring_config.json")
SITES= os.path.join(BASE, "sites.yaml")

def load_scoring():
    with open(CFG) as f:
        return json.load(f)

def km(a,b,c,d):
    # haversine
    R=6371
    p1=math.radians(a); p2=math.radians(c)
    dlat=math.radians(c-a); dlon=math.radians(d-b)
    h=math.sin(dlat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(h))

def norm_price(s:str)->float|None:
    if not s: return None
    s = s.replace(",", "").replace(" ", "")
    m = re.search(r'([0-9.]+)(m|k)?', s.lower())
    if not m: return None
    x = float(m.group(1))
    mul = {"m":1_000_000,"k":1_000}.get(m.group(2) or "",1)
    return x*mul

def search_serpapi(q, gl="au"):
    key = os.environ.get("SERPAPI_API_KEY")
    if not key:
        raise RuntimeError("SERPAPI_API_KEY not set")
    params = {"engine":"google","q":q,"gl":gl,"num":10}
    res = GoogleSearch(params, api_key=key).get_dict()
    return res.get("organic_results", [])

def parse_sites():
    with open(SITES) as f:
        return yaml.safe_load(f)

def normalize_hit(hit, source)->Dict[str,Any]:
    link = hit.get("link")
    title= hit.get("title","").strip()
    snippet = hit.get("snippet","")
    price = None
    # crude price parse from snippet/title
    m = re.search(r"AUD?\$?\s?([0-9,\.]+[mk]?)", snippet+ " " + title, re.I)
    if m:
        price = norm_price(m.group(1))
    return {
        "id": f"{source['name']}-{abs(hash(link))%10_000_000}",
        "title": title,
        "category": source.get("category","Unknown"),
        "source": source["name"],
        "url": link,
        "asking_price_aud": price,
        "revenue_aud": None,
        "ebitda_aud": None,
        "location": source.get("region","AU"),
        "lat": None,
        "lon": None,
        "ownership": source.get("ownership","Unknown"),
        "days_on_market": 0,
        "date_listed": datetime.now(timezone.utc).date().isoformat(),
        "notes": snippet,
        "contact": None
    }

def run():
    sites = parse_sites()
    deals = []
    for s in sites:
        for q in s["queries"]:
            results = search_serpapi(q)
            for hit in results:
                deals.append(normalize_hit(hit, s))
            time.sleep(1.5)  # politeness
    # de-dup by url
    uniq = {}
    for d in deals:
        uniq[d["url"]] = d
    deals = list(uniq.values())

    # score
    cfg = load_scoring()
    deals = score_deals(deals, cfg)

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA,"deals.json"),"w") as f:
        json.dump(deals, f, indent=2)
    pd.DataFrame(deals).to_csv(os.path.join(DATA,"latest.csv"), index=False)

def score_deals(deals, cfg):
    w = cfg["weights"]
    target = set(cfg["target_categories"])
    hq_lat = cfg["hq_lat"]; hq_lon = cfg["hq_lon"]
    maxd = cfg["max_distance_km_for_full_points"]

    out = []
    for d in deals:
        rev = (d.get("revenue_aud") or 0)
        ebitda = (d.get("ebitda_aud") or 0)
        price = (d.get("asking_price_aud") or 0)

        margin = ebitda/rev if rev>0 else 0
        pte = price/ebitda if ebitda>0 else 99

        # normalize features 0..1
        f_margin = min(max(margin/0.3, 0), 1)  # 30% margin caps
        f_pte = 1 - min(pte/5, 1)              # <=5x EBITDA best
        # recency (today best)
        try:
            days = (datetime.now().date() - datetime.fromisoformat(d["date_listed"]).date()).days
        except Exception:
            days = 30
        f_recent = max(0, 1 - days/30)

        # ownership
        f_freehold = 1 if (d.get("ownership","").lower()=="freehold") else 0.3

        # category
        f_cat = 1 if d.get("category") in target else 0.5

        # proximity
        if d.get("lat") is not None and d.get("lon") is not None:
            dist = km(hq_lat,hq_lon,d["lat"],d["lon"])
            f_dist = max(0, 1 - dist/maxd)
        else:
            f_dist = 0.5  # unknown

        score = (
            w["ebitda_margin"]*f_margin +
            w["price_to_ebitda"]*f_pte +
            w["recency"]*f_recent +
            w["ownership_freehold"]*f_freehold +
            w["category_match"]*f_cat +
            w["proximity_se_qld"]*f_dist
        )
        d2 = dict(d)
        d2["score"] = round(float(score), 3)
        d2["features"] = {
            "margin": round(f_margin,3),
            "price_to_ebitda": round(f_pte,3),
            "recency": round(f_recent,3),
            "freehold": f_freehold,
            "category": f_cat,
            "proximity": round(f_dist,3)
        }
        out.append(d2)
    out.sort(key=lambda x: x["score"], reverse=True)
    return out

if __name__ == "__main__":
    run()
