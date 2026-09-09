"""Refresh the Binder Ledger from Cardmarket's daily price guide.

Usage:  py -3.13 refresh.py
All state (binder.json, history/, the HTML) lives in ./data next to the scripts, or in $LEDGER_DATA.

What it does
1. Downloads Cardmarket's official daily price export (price_guide_6.json, game 6 = Pokemon).
   This is the same file offered on cardmarket.com/en/Pokemon/Data/Price-Guide.
2. For every card in binder.json, looks up its saved Cardmarket product ID (cm_id) and
   copies trend, avg1, avg7, avg30 and low (the "-holo" variants when finish is "reverse").
   Sets the CM date to the export's creation date.
3. Keeps a dated copy of the export in history/ (this builds our own Cardmarket price history),
   asks the Wayback Machine to archive the same file publicly, and records today's trend
   per card in binder.json under "hist". Also refreshes products_singles_6.json (the
   Cardmarket product list) so manage.py can add cards from newly released sets.
4. Runs validate.py; on any FAIL it restores binder.json from binder.last_good.json and stops.
5. Rebuilds binder_ledger.html via build_page.py.

Nothing else is contacted. The product IDs were matched once (see cm_expansions.json and
cm_match.json for how) and never need re-matching.

Adding/removing cards: use manage.py (see its docstring).
"""
import json, urllib.request, subprocess, sys, os, datetime

CODE = os.path.dirname(os.path.abspath(__file__))                     # where the scripts live
DATA = os.environ.get("LEDGER_DATA", os.path.join(CODE, "data"))     # where all state lives
os.chdir(DATA)
URL = "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"

print("downloading Cardmarket price guide ...")
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
pg = json.load(urllib.request.urlopen(req, timeout=120))
guide = {g["idProduct"]: g for g in pg["priceGuides"]}
date = pg["createdAt"][:10]
print("price guide created", pg["createdAt"], "-", len(guide), "products")
json.dump(pg, open("price_guide_6.json", "w", encoding="utf-8"))
os.makedirs("history", exist_ok=True)
json.dump(pg, open(f"history/price_guide_6_{date.replace('-', '')}.json", "w", encoding="utf-8"))  # own archive, one file per day

# also ask the Wayback Machine to keep a public copy (off-machine backup of the history)
try:
    urllib.request.urlopen(urllib.request.Request("https://web.archive.org/save/" + URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120)
    print("Wayback Machine snapshot requested")
except Exception as e:
    print("Wayback save skipped:", e)

# product list (idProduct -> name, expansion). Not needed for the refresh itself, but manage.py
# needs a current one to add cards from new sets, so keep it fresh daily. Failure is not fatal.
PRODUCTS_URL = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"
try:
    pl = json.load(urllib.request.urlopen(urllib.request.Request(PRODUCTS_URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120))
    json.dump(pl, open("products_singles_6.json", "w", encoding="utf-8"))
    print("product list created", pl["createdAt"], "-", len(pl["products"]), "products")
except Exception as e:
    print("product list download skipped, keeping the existing file:", e)

import shutil
shutil.copy("binder.json", "binder.last_good.json")  # rollback point
b = json.load(open("binder.json", encoding="utf-8"))
missing = []
for c in b:
    g = guide.get(c.get("cm_id"))
    if not g or g.get("trend") is None:
        missing.append(c["n"]); continue
    k = "-holo" if c.get("finish") == "reverse" else ""   # Cardmarket's "-holo" fields are the reverse-holo prices
    c.update(trend=g["trend" + k], avg30=g["avg30" + k], avg7=g["avg7" + k], avg1=g["avg1" + k], low=g["low" + k],
             cmd=date, upd=date, est=False)
    c.setdefault("hist", {})[date] = g["trend" + k]
json.dump(b, open("binder.json", "w", encoding="utf-8"), indent=0)

total = sum((c["trend"] or 0) * c.get("qty", 1) for c in b)
print(f"{len(b) - len(missing)} cards updated, total Cardmarket trend EUR {total:.2f}")
if missing:
    print("NOT updated (no cm_id or no price):", missing)

v = subprocess.run([sys.executable, os.path.join(CODE, "validate.py")])
if v.returncode != 0:
    shutil.copy("binder.last_good.json", "binder.json")
    print("VALIDATION FAILED: binder.json rolled back, page NOT rebuilt. Fix the FAIL lines above.")
    sys.exit(1)
subprocess.run([sys.executable, os.path.join(CODE, "build_page.py")], check=True)
print("binder_ledger.html rebuilt. Publish it with the same artifact URL to update the page.")
