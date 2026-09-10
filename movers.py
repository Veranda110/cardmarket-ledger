"""Daily movers post: the biggest climbers and droppers among English cards, from our own archive of
Cardmarket's daily exports. Written by refresh.py after every refresh; also runnable by hand.

Output (in the data folder): movers.md (the post, paste-ready), movers.json (the same rows as data).

Rules (all deterministic, no external calls):
  universe   high-confidence rows of products_map.json (card identity verified by name + attacks + fingerprint)
  band       reference trend between BAND_LOW and BAND_HIGH euro
  change     Cardmarket Price Trend today vs the export WINDOW days earlier; if the archive is younger than
             that, the oldest export within the window is used and the post says so
  guard      today's trend within GUARD of today's 7-day average (a single graded or odd sale pushes the trend
             far from the 7-day average; those are not moves)
  liquidity  once 7 exports exist: the trend must have changed on at least LIQ_DAYS of the last 7 day pairs
             (Cardmarket recalculates the trend from sales, a card that never moves is not trading)
"""
import json, glob, os, sys, datetime, urllib.parse

CODE = os.path.dirname(os.path.abspath(__file__))
BAND_LOW, BAND_HIGH = 5.0, 20.0
WINDOW = 7
GUARD = 0.30
LIQ_DAYS = 3
TOP = 3


def pick(series, today, ref, band=(BAND_LOW, BAND_HIGH), guard=GUARD, liq_days=LIQ_DAYS, top=TOP):
    """Pure function. series: {pid: {date: {'trend', 'avg7'}}} for the candidate universe; dates ISO strings.
    Returns (climbers, droppers, n_considered); each row is a dict with pid, ref, now, chg, pct."""
    rows = []
    for pid, s in series.items():
        a, b = s.get(ref), s.get(today)
        if not a or not b or not a.get('trend') or not b.get('trend'):
            continue
        if not (band[0] <= a['trend'] <= band[1]):
            continue
        if b.get('avg7') and abs(b['trend'] / b['avg7'] - 1) > guard:
            continue
        days = sorted(d for d in s if d <= today)[-8:]          # last 7 day pairs
        if len(days) >= 8:
            moves = sum(1 for x, y in zip(days, days[1:]) if s[x].get('trend') != s[y].get('trend'))
            if moves < liq_days:
                continue
        rows.append(dict(pid=pid, ref=a['trend'], now=b['trend'], chg=round(b['trend'] - a['trend'], 2),
                         pct=round((b['trend'] / a['trend'] - 1) * 100, 1)))
    rows.sort(key=lambda r: r['pct'])
    climbers = [r for r in rows[::-1] if r['pct'] > 0][:top]
    droppers = [r for r in rows if r['pct'] < 0][:top]
    return climbers, droppers, len(rows)


def main():
    os.chdir(os.environ.get('LEDGER_DATA', os.path.join(CODE, 'data')))
    load = lambda p: json.load(open(p, encoding='utf-8'))
    pm = {int(k): v for k, v in load('products_map.json').items() if v['conf'] == 'high'}
    meta = load('set_meta.json')
    exp_of = {p['idProduct']: p['idExpansion'] for p in load('products_singles_6.json')['products']}
    snaps = {}
    for f in sorted(glob.glob('history/*.json')):
        d = load(f)
        snaps[d['createdAt'][:10]] = {g['idProduct']: g for g in d['priceGuides']}
    days = sorted(snaps)
    today = days[-1]
    want = (datetime.date.fromisoformat(today) - datetime.timedelta(days=WINDOW)).isoformat()
    within = [d for d in days if want <= d < today]
    if not within:
        sys.exit(f"movers: no export within {WINDOW} days before {today}, nothing to compare")
    ref = within[0]
    series = {pid: {d: {'trend': snaps[d][pid].get('trend'), 'avg7': snaps[d][pid].get('avg7')}
                    for d in days if pid in snaps[d]} for pid in pm}
    climbers, droppers, n = pick(series, today, ref)
    span = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(ref)).days

    def row(i, r):
        m = pm[r['pid']]
        q = urllib.parse.urlencode({'idExpansion': exp_of.get(r['pid'], ''), 'searchString': m['name']})
        return (f"| {i} | [{m['name']}](https://www.cardmarket.com/en/Pokemon/Products/Search?{q}) | "
                f"{meta[m['setid']]['name']} {m['number']} | €{r['ref']:.2f} | €{r['now']:.2f} | {r['chg']:+.2f} ({r['pct']:+.0f}%) |")

    def table(title, rows):
        head = f"**{title}**\n\n| # | Card | Set | {span}d ago | Now | Change |\n|---|---|---|---|---|---|\n"
        return head + ("\n".join(row(i, r) for i, r in enumerate(rows, 1)) or "| – | no card passed the filters | | | | |") + "\n"

    # first day of the unbroken daily run (older Wayback snapshots sit in the archive too, they do not count)
    daily_start = today
    while (datetime.date.fromisoformat(daily_start) - datetime.timedelta(days=1)).isoformat() in snaps:
        daily_start = (datetime.date.fromisoformat(daily_start) - datetime.timedelta(days=1)).isoformat()
    note = (f"{span}-day window." if span >= WINDOW else
            f"{span}-day change: the daily archive started on {daily_start}, the window grows to {WINDOW} days on "
            f"{(datetime.date.fromisoformat(daily_start) + datetime.timedelta(days=WINDOW)).isoformat()}.")
    post = f"""# Cardmarket Pokémon movers, {today}

Cardmarket's own daily price export, Price Trend in EUR. English cards, identity verified against the set list, trend €{BAND_LOW:.0f} to €{BAND_HIGH:.0f} at the start of the window, today's trend within {GUARD:.0%} of the 7-day average so one odd sale does not count as a move. {n:,} cards qualified. {note}

{table('Biggest climbers', climbers)}
{table('Biggest droppers', droppers)}
Data and method: https://github.com/Veranda110/cardmarket-ledger
"""
    open('movers.md', 'w', encoding='utf-8').write(post)
    json.dump(dict(date=today, ref=ref, considered=n, climbers=climbers, droppers=droppers),
              open('movers.json', 'w', encoding='utf-8'), indent=1)
    print(post)


if __name__ == '__main__':
    main()
