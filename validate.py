"""Validate binder.json before it is trusted or published.

Run:  py -3.13 validate.py            exit code 0 = all hard checks passed
Test: py -3.13 -m unittest test_validate -v
refresh.py runs this automatically and aborts the rebuild on any FAIL.

Hard checks (FAIL, blocks the build)
  A. Cardmarket product name equals the ledger card name (catches wrong product).
  B. The card's set code + number resolve, in the GitHub set list, to that same name
     (catches a wrong set code like sm5 vs sm2, which is how Wailord became Alolan Vulpix).
  C. All cards of one set code share one Cardmarket expansion id.
  C2. A sub-set (Shiny Vault, Galarian Gallery, Trainer Gallery, Classic Collection) shares its
     parent set's expansion, because Cardmarket folds them together (Sudowoodo HIF SV20 case).
  D. Every card has a trend price today.
  E. No two rows share a cm_id: multiple copies of one card are one row with qty > 1.
  E2. qty is a whole number of at least 1.
  F. Card count equals cards.csv.
Soft checks (WARN, reported but not blocking)
  G. Trend moved more than 3x up or down against a snapshot at most 45 days earlier.
  H. Card is tagged verify (a sibling product within 2x exists) and has not been confirmed.
"""
import json, csv, re, sys, os, collections, datetime

PARENT = {'sma': 'sm115', 'swsh45sv': 'swsh45', 'swsh12pt5gg': 'swsh12pt5',
          'cel25c': 'cel25', 'swsh9tg': 'swsh9'}
JUMP_FACTOR = 3
JUMP_MAX_GAP_DAYS = 45


def base(n):
    """Normalise a card name for comparison: drop version suffixes, punctuation, case."""
    n = re.sub(r'\s*\(.*?\)|\s+(IR|TG|FA|SIR)$| #\d+$| promo$', '', n).strip().lower()
    return re.sub(r'[^a-z0-9]', '', n)


def norm_number(s):
    return re.sub(r'^0+', '', str(s).upper().replace('_A', ''))


def validate(binder, cards, setnames, products=None):
    """Pure function. Returns (fails, warns) as lists of strings.

    binder:   list of card dicts (binder.json)
    cards:    {n(str): {'setid','number',...}} (cards.csv rows)
    setnames: {setid: [[name, number, rarity], ...]} (set_names.json)
    products: optional {idProduct: {'name': ...}} to fill a missing cm_name
    """
    products = products or {}
    fails, warns = [], []

    def fail(c, msg): fails.append(f"#{c['n']:>2} {c['name']}: {msg}")
    def warn(c, msg): warns.append(f"#{c['n']:>2} {c['name']}: {msg}")

    # F. count
    if len(binder) != len(cards):
        fails.append(f"card count: binder has {len(binder)}, cards.csv has {len(cards)}")

    exp_by_set = collections.defaultdict(set)
    ids = collections.defaultdict(list)
    for c in binder:
        row = cards.get(str(c['n']))
        # A. product name
        cmname = c.get('cm_name') or products.get(c.get('cm_id'), {}).get('name', '')
        if not cmname:
            fail(c, 'no Cardmarket product name to compare')
        elif base(cmname.split(' [')[0].split(' (')[0]) != base(c['name']):
            fail(c, f"Cardmarket product is '{cmname}', not this card")
        # B. set code + number -> name
        if row:
            want = norm_number(row['number'])
            hits = [x for x in setnames.get(row['setid'], []) if norm_number(x[1]) == want]
            if not hits:
                fail(c, f"number {row['number']} not found in set list for code {row['setid']}")
            elif base(hits[0][0]) != base(c['name']):
                fail(c, f"set code {row['setid']} number {row['number']} is '{hits[0][0]}' in the set list, not this card: wrong set code?")
            exp_by_set[row['setid']].add(c.get('cm_exp'))
        else:
            fail(c, 'not present in cards.csv')
        # D. price today
        if c.get('trend') is None:
            fail(c, 'no trend price')
        # E2. quantity
        q = c.get('qty', 1)
        if not isinstance(q, int) or isinstance(q, bool) or q < 1:
            fail(c, f'qty must be a whole number >= 1, got {q!r}')
        ids[c.get('cm_id')].append(c)
        # G. jumps within a short gap
        h = {d: v for d, v in (c.get('hist') or {}).items() if v}
        days = sorted(h)
        for a, z in zip(days, days[1:]):
            gap = (datetime.date.fromisoformat(z) - datetime.date.fromisoformat(a)).days
            if gap <= JUMP_MAX_GAP_DAYS and (h[z] / h[a] > JUMP_FACTOR or h[a] / h[z] > JUMP_FACTOR):
                warn(c, f"trend {h[a]} ({a}) -> {h[z]} ({z}) within {gap} days, more than {JUMP_FACTOR}x: check the product")
        # H. verify tag
        if c.get('verify') and not c.get('verified'):
            warn(c, 'tagged verify: sibling product within 2x, not yet confirmed against the Cardmarket page')

    # C2. sub-set shares parent's expansion
    for sub, par in PARENT.items():
        if sub in exp_by_set and par in exp_by_set and exp_by_set[sub] != exp_by_set[par]:
            fails.append(f"sub-set {sub} uses expansion {sorted(exp_by_set[sub])} but parent {par} uses {sorted(exp_by_set[par])}")

    # C. one expansion per set code
    for sid, exps in exp_by_set.items():
        if len(exps) > 1:
            fails.append(f"set code {sid} maps to several Cardmarket expansions: {sorted(exps)}")

    # E. one row per product; copies go in qty
    for cid, cs in ids.items():
        if len(cs) > 1:
            fails.append(f"cm_id {cid} appears in rows {[c['n'] for c in cs]}: merge them into one row with qty {len(cs)}")

    return fails, warns


def main():
    code = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.environ.get('LEDGER_DATA', os.path.join(code, 'data')))
    binder = json.load(open('binder.json', encoding='utf-8'))
    cards = {r['n']: r for r in csv.DictReader(open('cards.csv', encoding='utf-8'))}
    setnames = json.load(open('set_names.json', encoding='utf-8'))
    products = {}
    prods_path = 'products_singles_6.json'
    if os.path.exists(prods_path):
        products = {p['idProduct']: p for p in json.load(open(prods_path, encoding='utf-8'))['products']}
    fails, warns = validate(binder, cards, setnames, products)
    print(f"validate: {len(binder)} cards, {len(fails)} FAIL, {len(warns)} WARN")
    for f in fails: print('  FAIL', f)
    for w in warns: print('  WARN', w)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
