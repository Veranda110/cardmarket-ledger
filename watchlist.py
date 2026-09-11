"""Two outputs that turn the daily export into something you can act on fast.

1. data/wants.txt and data/wants/*.txt - Cardmarket want-list imports: the cards that pass the buy screen,
   one per line in Cardmarket's "Name Attack Attack" format, split into files of MAX_PER_LIST grouped by
   value. Cardmarket then watches the market itself and mails you when a matching copy is listed. That is
   the fast path; a once-a-day export can never be, see below.

2. data/checklist.md - THE ONE TO READ EVERY MORNING. Cards whose cheapest listed copy sits between
   FLOOR_MIN_NOW and WANT_DISCOUNT of the 30-day average (low enough to be a discount, high enough to be a
   near-mint copy), that are not falling on every horizon, ranked by euros saved. Links carry CM_FILTER.

3. data/floor_alerts.md - cards whose cheapest listed offer dropped well below THEIR OWN usual floor.
   The absolute floor is useless (median card lists its cheapest copy at 30% of the 30-day average,
   because that copy is damaged or foreign). The floor as a fraction of the 30-day average is stable per
   card though (median spread 0.16 across snapshots), so a drop below a card's own baseline is a real
   new listing rather than the usual beaten copy.

Screen (same rules as the ledger's analysis): high-confidence English cards, set older than MIN_AGE_MONTHS,
30-day average in BAND, rising in both measured periods. No timing filter: the wanted price does that job.
"""
import collections, json, glob, os, re, datetime

CODE = os.path.dirname(os.path.abspath(__file__))
BAND = (5.0, 100.0)
WANT_DISCOUNT = 0.75      # buy at or under this fraction of the 30-day average. Cardmarket enforces it, so no timing filter is needed
# The import line carries the card name only: Cardmarket matches the whole line against a product name and
# rejects it when a price is appended. The wanted price is set after import, per list or per row; the
# percentage each card needs is in wants_prices.md.
MIN_AGE_MONTHS = 9
FLOOR_DROP = 0.6          # today's floor at most this fraction of the card's own usual floor
FLOOR_MIN_BASE = 0.45     # and that usual floor must itself be near market, else the card always has junk copies
FLOOR_MIN_NOW = 0.50      # and the new floor must still be a plausible near-mint price; below this it is a beaten copy
FLOOR_MAX_NOW = 1.20      # and not above the 30-day average: when the floor sits above it, the card barely sells and the average is stale
MODERN_YEAR = 2017        # older cards carry condition risk that the export cannot see
MAX_PER_LIST = 150        # Cardmarket's cap: 150 entries per want list, 100 lists per game
CHECK_TOP = 15            # rows on the daily check list: what a human can verify in about 90 seconds
# Your own Cardmarket filter, copied from the address bar after setting language and seller countries by
# hand. It travels with every link below, so a click lands on the filtered offer list, not the raw page.
CM_FILTER = 'sellerCountry=2,7,23&language=1'


def wants_line(product_name):
    """Cardmarket product name -> want-list line. Only the LAST bracket group holds the attacks and
    abilities; earlier ones are part of the name (owner and form tags: 'Nidoran [M]', 'Staraptor [FB] LV.X',
    'Unown [A]'), so they stay as written.
    'Tinkaton ex [Tandem Unit | Gigaton Hammer]' -> 'Tinkaton ex Tandem Unit Gigaton Hammer'
    'Nidoran [M] [Horn Hazard]'                  -> 'Nidoran [M] Horn Hazard'"""
    m = re.match(r'^(.*)\[([^\[\]]*)\]\s*$', product_name)
    if not m:
        return product_name.strip()
    return (m.group(1).strip() + ' ' + ' '.join(a.strip() for a in m.group(2).split('|'))).strip()


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

    picks, alerts, checks = [], [], []
    for pid, m in pm.items():
        if m['conf'] != 'high':
            continue
        p = int(pid)
        a, b, c = snaps[first].get(p), snaps[mid].get(p), now.get(p)
        if not (a and b and c and a.get('avg30') and b.get('avg30') and c.get('avg30') and c.get('trend')):
            continue
        rel = datetime.date.fromisoformat(meta[m['setid']]['release'].replace('/', '-'))
        a0, a1, a2, tr = a['avg30'], b['avg30'], c['avg30'], c['trend']
        if rel <= cut and BAND[0] <= a2 <= BAND[1] and a1 > a0 and a2 > a1:
            want = a2 * WANT_DISCOUNT
            pct = max(1, min(100, int(want / tr * 100)))          # int(): rounds down, so the code never asks for more
            picks.append(dict(p=p, m=m, a2=a2, tr=tr, want=want, pct=pct, pay=tr * pct / 100,
                              modern=rel.year >= MODERN_YEAR, g1=a1 / a0 - 1, g2=a2 / a1 - 1))
        # floor against the card's own history
        hist = [snaps[d][p]['low'] / snaps[d][p]['avg30'] for d in days[:-1]
                if snaps[d].get(p) and snaps[d][p].get('low') and snaps[d][p].get('avg30')]
        if hist and c.get('low') and a2 >= BAND[0]:
            base = sorted(hist)[len(hist) // 2]
            ratio = c['low'] / a2
            if base >= FLOOR_MIN_BASE and FLOOR_MIN_NOW <= ratio <= FLOOR_MAX_NOW and ratio / base <= FLOOR_DROP:
                alerts.append(dict(p=p, m=m, a2=a2, tr=tr, low=c['low'], base=base * a2, drop=ratio / base))
        # --- daily check list: which cards are worth opening today, ranked by euros saved, not by percent
        lo_now, a1d, a7d = c.get('low'), c.get('avg1'), c.get('avg7')
        if not (lo_now and a1d and a7d and BAND[0] <= a2 <= BAND[1]):
            continue
        falling = a1d < a7d < a2          # every horizon lower than the last: today's discount is tomorrow's price
        target = a2 * WANT_DISCOUNT
        # The floor must be low enough to be a discount and high enough to be a near-mint copy. Without the
        # lower bound, ranking by euros saved just finds whichever expensive card has the most beaten copy
        # listed: a EUR 97 card with a EUR 5 floor is damage, not a EUR 92 saving.
        if not (a2 * FLOOR_MIN_NOW <= lo_now <= target) or falling:
            continue
        prev = snaps[days[-2]].get(p, {}) if len(days) > 1 else {}
        # The cheapest copy is usually damaged. When the floor RISES while the 30-day average holds, that
        # damaged copy sold and the new floor is a better copy: the opposite of an alert, and a real signal.
        cleared = bool(prev.get('low') and prev.get('avg30') and lo_now > prev['low'] * 1.05
                       and abs(a2 / prev['avg30'] - 1) < 0.05)
        base = sorted(hist)[len(hist) // 2] if hist else None
        checks.append(dict(p=p, m=m, a2=a2, tr=tr, low=lo_now, a7=a7d, a1=a1d, target=target,
                           save=a2 - lo_now, ratio=lo_now / a2, cleared=cleared,
                           own=(lo_now / a2) / base if base else None,
                           moves=sum(1 for x, y in zip(days, days[1:])
                                     if snaps[x].get(p, {}).get('trend') != snaps[y].get(p, {}).get('trend'))))

    picks.sort(key=lambda x: x['tr'] / x['a2'])
    alerts.sort(key=lambda x: x['drop'])

    def link(p, name):
        import urllib.parse
        q = urllib.parse.urlencode({'idExpansion': ps[p]['idExpansion'], 'searchString': name})
        return f"https://www.cardmarket.com/en/Pokemon/Products/Search?{q}&{CM_FILTER}"

    picks.sort(key=lambda x: -x['a2'])
    # Plain names only. Cardmarket's importer matches the name and rejects the whole line when a price
    # code is appended to it, so the wanted price is set after import, not here.
    with open('wants.txt', 'w', encoding='utf-8') as f:
        for x in picks:
            f.write(f"{wants_line(ps[x['p']]['name'])}\n")
    # split by value so each group can be its own want list with its own e-mail alert: a EUR 6 card is not
    # worth an instant mail, a EUR 80 one is.
    GROUPS = [('cheap', 5, 20), ('mid', 20, 50), ('high', 50, 100)]
    os.makedirs('wants', exist_ok=True)
    for stale in glob.glob('wants/*.txt'):
        os.remove(stale)
    made = []
    for name, lo, hi in GROUPS:
        rows = sorted((x for x in picks if lo <= x['a2'] < hi), key=lambda r: -r['a2'])
        # A want list holds at most MAX_PER_LIST entries, so each group is split into parts and every part
        # becomes its own list. Most valuable first, so part 1 is the one worth arming carefully.
        for i in range(0, len(rows), MAX_PER_LIST):
            part = rows[i:i + MAX_PER_LIST]
            fn = f'wants/{name}_{lo:g}_{hi:g}_eur_part{i // MAX_PER_LIST + 1}.txt'
            with open(fn, 'w', encoding='utf-8') as f:
                for x in part:
                    f.write(f"{wants_line(ps[x['p']]['name'])}\n")
            made.append((fn, len(part)))
    with open('wants_prices.md', 'w', encoding='utf-8') as f:
        f.write(f"# Want list, {today}\n\n{len(picks)} English cards that rose in both measured periods, set older than "
                f"{MIN_AGE_MONTHS} months, 30-day average €{BAND[0]:.0f} to €{BAND[1]:.0f}.\n\n"
                f"Cardmarket allows {MAX_PER_LIST} entries per want list, so the cards are split into files of that "
                f"size, grouped by value. Import each file as its own want list, then set for the whole list: "
                f"condition **Near Mint or better**, language **English**, and switch the e-mail alarm on. The wanted "
                f"price per card is the **Alerts at** column below, about {WANT_DISCOUNT:.0%} of its 30-day average.\n\n"
                + ''.join(f"- `{fn}`: {n} cards\n" for fn, n in made) + "\n"
                f"| Card | Set · nr | 30d avg | Trend | Code | Alerts at | Cardmarket |\n|---|---|---|---|---|---|---|\n")
        for x in picks:
            m = x['m']
            f.write(f"| {m['name']} | {meta[m['setid']]['name']} {m['number']} | {x['a2']:.2f} | {x['tr']:.2f} | "
                    f"{x['pct']}% | €{x['pay']:.2f} | [open]({link(x['p'], m['name'])}) |\n")
    with open('floor_alerts.md', 'w', encoding='utf-8') as f:
        f.write(f"# Floor alerts, {today}\n\nCards whose cheapest listed copy dropped to {FLOOR_DROP:.0%} or less of that card's own "
                f"usual floor, where the usual floor is at least {FLOOR_MIN_BASE:.0%} of the 30-day average.\n"
                f"A card that always has a beaten copy listed cheap never appears here; a fresh cheap listing does.\n\n"
                f"| Card | Set · nr | 30d avg | Trend | Cheapest now | Usual floor | Cardmarket |\n|---|---|---|---|---|---|---|\n")
        for x in alerts:
            m = x['m']
            f.write(f"| {m['name']} | {meta[m['setid']]['name']} {m['number']} | {x['a2']:.2f} | {x['tr']:.2f} | "
                    f"{x['low']:.2f} | {x['base']:.2f} | [open]({link(x['p'], m['name'])}) |\n")
    # --- the daily check list: the only output that is meant to be read every morning
    checks.sort(key=lambda x: -x['save'])
    top = checks[:CHECK_TOP]
    with open('checklist.md', 'w', encoding='utf-8') as f:
        f.write(f"# Cards to open today, {today}\n\n"
                f"Cards whose cheapest listed copy is at or under {WANT_DISCOUNT:.0%} of the 30-day average, that are not "
                f"falling on every horizon (1-day under 7-day under 30-day), ranked by **euros saved**, not by percentage: "
                f"a quarter off a €6 card is noise.\n\n"
                f"The export carries no condition, language or seller country, so the cheapest copy is often damaged or "
                f"foreign. Every link is pre-filtered to your languages and seller countries; the copy itself still needs "
                f"your eyes. {len(checks)} cards qualified, the {len(top)} biggest are below.\n\n"
                f"| Card | Set · nr | 30d avg | Cheapest | Saving | Buy under | Note | Cardmarket |\n"
                f"|---|---|---|---|---|---|---|---|\n")
        for x in top:
            m = x['m']
            note = []
            if x['cleared']:
                note.append('floor rose, the damaged copy sold')
            if x['own'] and x['own'] < 0.7:
                note.append("well under this card's own usual floor")
            if x['moves'] <= 1:
                note.append('barely trades, no rush')
            f.write(f"| {m['name']} | {meta[m['setid']]['name']} {m['number']} | {x['a2']:.2f} | {x['low']:.2f} | "
                    f"**€{x['save']:.2f}** | €{x['target']:.2f} | {'; '.join(note) or '—'} | "
                    f"[open]({link(x['p'], m['name'])}) |\n")
    print(f"wants.txt: {len(picks)} cards ({sum(x['modern'] for x in picks)} modern) | "
          f"floor_alerts.md: {len(alerts)} | checklist.md: {len(top)} of {len(checks)} candidates")


if __name__ == '__main__':
    main()
