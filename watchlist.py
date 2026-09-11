"""Two outputs that turn the daily export into something you can act on fast.

1. data/wants.txt  - a Cardmarket want-list import: the cards that pass the buy screen, one per line in
   Cardmarket's "Name Attack Attack" format, with the max price to set written next to it as a comment.
   Cardmarket then watches the market in real time and tells you when a copy is listed under your price.
   That is the fast path; a once-a-day export can never be, see below.

2. data/floor_alerts.md - cards whose cheapest listed offer dropped well below THEIR OWN usual floor.
   The absolute floor is useless (median card lists its cheapest copy at 30% of the 30-day average,
   because that copy is damaged or foreign). The floor as a fraction of the 30-day average is stable per
   card though (median spread 0.16 across snapshots), so a drop below a card's own baseline is a real
   new listing rather than the usual beaten copy.

Screen (same rules as the ledger's analysis): high-confidence English cards, set older than 9 months,
30-day average in BAND, rising in both measured periods, trend under MAX_RATIO of the 30-day average.
"""
import json, glob, os, re, datetime

CODE = os.path.dirname(os.path.abspath(__file__))
BAND = (5.0, 100.0)
MAX_RATIO = 0.85          # trend must sit this far under the 30-day average to count as a buy window
MIN_AGE_MONTHS = 9
FLOOR_DROP = 0.6          # today's floor at most this fraction of the card's own usual floor
FLOOR_MIN_BASE = 0.45     # and that usual floor must itself be near market, else the card always has junk copies
FLOOR_MIN_NOW = 0.50      # and the new floor must still be a plausible near-mint price; below this it is a beaten copy
FLOOR_MAX_NOW = 1.20      # and not above the 30-day average: when the floor sits above it, the card barely sells and the average is stale
MODERN_YEAR = 2017        # older cards carry condition risk that the export cannot see


def wants_line(product_name):
    """Cardmarket product name -> want-list line. 'Tinkaton ex [Tandem Unit | Gigaton Hammer]'
    -> 'Tinkaton ex Tandem Unit Gigaton Hammer'. Cardmarket matches on name plus attacks."""
    m = re.match(r'^(.*?)\s*\[(.*?)\]\s*$', product_name)
    if not m:
        return product_name.strip()
    return (m.group(1) + ' ' + ' '.join(a.strip() for a in m.group(2).split('|'))).strip()


def main():
    os.chdir(os.environ.get('LEDGER_DATA', os.path.join(CODE, 'data')))
    load = lambda p: json.load(open(p, encoding='utf-8'))
    pm = load('products_map.json'); meta = load('set_meta.json')
    ps = {p['idProduct']: p for p in load('products_singles_6.json')['products']}
    snaps = {}
    for f in sorted(glob.glob('history/*.json')):
        d = load(f); snaps[d['createdAt'][:10]] = {g['idProduct']: g for g in d['priceGuides']}
    days = sorted(snaps); today = days[-1]; now = snaps[today]
    first, mid = days[0], days[len(days) // 2]
    cut = datetime.date.fromisoformat(today) - datetime.timedelta(days=MIN_AGE_MONTHS * 30)

    picks, alerts = [], []
    for pid, m in pm.items():
        if m['conf'] != 'high':
            continue
        p = int(pid)
        a, b, c = snaps[first].get(p), snaps[mid].get(p), now.get(p)
        if not (a and b and c and a.get('avg30') and b.get('avg30') and c.get('avg30') and c.get('trend')):
            continue
        rel = datetime.date.fromisoformat(meta[m['setid']]['release'].replace('/', '-'))
        a0, a1, a2, tr = a['avg30'], b['avg30'], c['avg30'], c['trend']
        if rel <= cut and BAND[0] <= a2 <= BAND[1] and a1 > a0 and a2 > a1 and tr / a2 < MAX_RATIO:
            picks.append(dict(p=p, m=m, a2=a2, tr=tr, modern=rel.year >= MODERN_YEAR,
                              g1=a1 / a0 - 1, g2=a2 / a1 - 1))
        # floor against the card's own history
        hist = [snaps[d][p]['low'] / snaps[d][p]['avg30'] for d in days[:-1]
                if snaps[d].get(p) and snaps[d][p].get('low') and snaps[d][p].get('avg30')]
        if hist and c.get('low') and a2 >= BAND[0]:
            base = sorted(hist)[len(hist) // 2]
            ratio = c['low'] / a2
            if base >= FLOOR_MIN_BASE and FLOOR_MIN_NOW <= ratio <= FLOOR_MAX_NOW and ratio / base <= FLOOR_DROP:
                alerts.append(dict(p=p, m=m, a2=a2, tr=tr, low=c['low'], base=base * a2, drop=ratio / base))

    picks.sort(key=lambda x: x['tr'] / x['a2'])
    alerts.sort(key=lambda x: x['drop'])

    def link(p, name):
        import urllib.parse
        q = urllib.parse.urlencode({'idExpansion': ps[p]['idExpansion'], 'searchString': name})
        return f"https://www.cardmarket.com/en/Pokemon/Products/Search?{q}"

    with open('wants.txt', 'w', encoding='utf-8') as f:
        f.write(f"# Cardmarket want list, generated {today} from the buy screen.\n"
                f"# Import under Want Lists > add articles. Then set per row: English, Near Mint or better,\n"
                f"# and the max price in the comment after each line. Cardmarket watches the market for you.\n")
        for x in picks:
            f.write(f"{wants_line(ps[x['p']]['name'])}\n")
    with open('wants_prices.md', 'w', encoding='utf-8') as f:
        f.write(f"# Max price per want, {today}\n\n| Card | Set · nr | 30d avg | Trend | Max to pay | Cardmarket |\n|---|---|---|---|---|---|\n")
        for x in picks:
            m = x['m']
            f.write(f"| {m['name']} | {meta[m['setid']]['name']} {m['number']} | {x['a2']:.2f} | {x['tr']:.2f} | "
                    f"**{x['tr']:.2f}** | [open]({link(x['p'], m['name'])}) |\n")
    with open('floor_alerts.md', 'w', encoding='utf-8') as f:
        f.write(f"# Floor alerts, {today}\n\nCards whose cheapest listed copy dropped to {FLOOR_DROP:.0%} or less of that card's own "
                f"usual floor, where the usual floor is at least {FLOOR_MIN_BASE:.0%} of the 30-day average.\n"
                f"A card that always has a beaten copy listed cheap never appears here; a fresh cheap listing does.\n\n"
                f"| Card | Set · nr | 30d avg | Trend | Cheapest now | Usual floor | Cardmarket |\n|---|---|---|---|---|---|---|\n")
        for x in alerts:
            m = x['m']
            f.write(f"| {m['name']} | {meta[m['setid']]['name']} {m['number']} | {x['a2']:.2f} | {x['tr']:.2f} | "
                    f"{x['low']:.2f} | {x['base']:.2f} | [open]({link(x['p'], m['name'])}) |\n")
    print(f"wants.txt: {len(picks)} cards ({sum(x['modern'] for x in picks)} modern) | floor_alerts.md: {len(alerts)} alerts")


if __name__ == '__main__':
    main()
