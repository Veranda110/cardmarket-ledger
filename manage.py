"""Add, remove, and inspect cards in the Binder Ledger. Deterministic, no AI.

  py -3.13 manage.py list
  py -3.13 manage.py add "Charizard ex" sv3 125 --page "Fire" [--reverse] [--lang EN] [--cm-id 123456]
  py -3.13 manage.py remove 57
  py -3.13 manage.py finish 12 reverse        (or: normal)
  py -3.13 manage.py qty 19 2                 (own two copies of card 19)
  py -3.13 manage.py verify 18                (mark a 'verify' tagged row as checked)

How `add` finds the Cardmarket product (the one-time match, same method as the original 56):
  1. Set list: cards/en/<setid>.json from github.com/PokemonTCG/pokemon-tcg-data, cached in
     set_names.json. The card's number must resolve to the name you typed, else it stops.
  2. Expansion: cm_expansions.json if the set is already labelled. Otherwise every Cardmarket
     expansion is scored by how many of the set's card names it contains; if one wins clearly
     it is used, if two are close (English set vs Japanese twin) you are shown both and must
     pass --cm-exp.
  3. Product: all products in that expansion with the card's name are listed with today's
     Cardmarket trend. One candidate: taken. Several: you must pass --cm-id from the list
     (compare with the Cardmarket page; the ⌕ search link is printed for that).
  4. validate.py runs; on FAIL the add is rolled back.
Then run refresh.py (or wait for the nightly task) and republish the page.
"""
import json, csv, sys, os, re, argparse, urllib.request, urllib.parse, shutil, subprocess, collections

CODE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('LEDGER_DATA', os.path.join(CODE, 'data'))
os.chdir(DATA)
PRODUCTS = 'products_singles_6.json'
PRICES = 'price_guide_6.json'
GH = "https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/{}.json"
CM_PRODUCTS_URL = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"


def norm(n): return re.sub(r'[^a-z0-9]', '', n.lower())
def cmbase(n): return n.split(' [')[0].split(' (')[0].strip()
def norm_number(s): return re.sub(r'^0+', '', str(s).upper().replace('_A', ''))
def load(p, default=None):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default
def save(p, d, indent=0): json.dump(d, open(p, 'w', encoding='utf-8'), indent=indent)
def fetch_json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120))


def write_cards_csv(binder):
    rows = [dict(n=c['n'], name=c['name'], setid=c['setid'], number=c['num_src']) for c in binder]
    with open('cards.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['n', 'name', 'setid', 'number']); w.writeheader(); w.writerows(rows)


def ensure_setlist(setid, setnames):
    if setid not in setnames:
        print(f"fetching set list {setid} from GitHub ...")
        d = fetch_json(GH.format(setid))
        setnames[setid] = [(c['name'], c['number'], c.get('rarity', ''),
                            [x['name'] for x in c.get('attacks', [])] + [x['name'] for x in c.get('abilities', [])]) for c in d]
        save('set_names.json', setnames)
    return setnames[setid]


def products():
    if not os.path.exists(PRODUCTS):
        print("downloading Cardmarket product list ...")
        save(PRODUCTS, fetch_json(CM_PRODUCTS_URL))
    return load(PRODUCTS)['products']


def label_expansion(setid, setlist, prods, forced=None):
    exps = load('cm_expansions.json', {'labels': {}, 'why': {}})
    # cm_expansion_labels.json (expansion id -> set code) covers every English set, made once by fingerprinting
    for e_str, sid_ in (load('cm_expansion_labels.json', {}) or {}).items():
        exps['labels'].setdefault(sid_, int(e_str))
    if forced:
        exps['labels'][setid] = forced; exps['why'][setid] = 'passed with --cm-exp'; save('cm_expansions.json', exps, 1); return forced
    if setid in exps['labels']:
        return exps['labels'][setid]
    gh = {norm(x[0]) for x in setlist}
    byexp = collections.defaultdict(set)
    for p in prods: byexp[p['idExpansion']].add(norm(cmbase(p['name'])))
    rec = sorted(((len(gh & en) / len(gh), e, len(en)) for e, en in byexp.items()), reverse=True)[:4]
    print("expansion candidates (coverage of the set's names, expansion id, products):")
    for r in rec: print(f"  {r[0]:.0%}  exp {r[1]}  ({r[2]} products)")
    top = [r for r in rec if r[0] >= rec[0][0] - 0.05 and r[0] >= 0.8]
    if len(top) != 1:
        sys.exit("ambiguous (English set vs its Japanese twin, usually). Check one card of the set on Cardmarket and re-run with --cm-exp <id>. The English one is the id whose product prices match the Cardmarket page.")
    e = top[0][1]
    exps['labels'][setid] = e; exps['why'][setid] = f"only expansion containing {top[0][0]:.0%} of the set's card names"
    save('cm_expansions.json', exps, 1)
    return e


def cmd_add(a):
    binder = load('binder.json'); setnames = load('set_names.json', {})
    setlist = ensure_setlist(a.setid, setnames)
    hit = [x for x in setlist if norm_number(x[1]) == norm_number(a.number)]
    if not hit: sys.exit(f"number {a.number} not in set {a.setid}")
    ghname, _, rarity = hit[0][0], hit[0][1], hit[0][2]
    gh_attacks = {norm(x) for x in (hit[0][3] if len(hit[0]) > 3 else [])}
    if norm(ghname) != norm(a.name):
        sys.exit(f"set {a.setid} number {a.number} is '{ghname}', not '{a.name}'. Wrong set code or number.")
    prods = products(); guide = {g['idProduct']: g for g in load(PRICES)['priceGuides']}
    # Fast path: products_map.json (built by build_product_map.py) already ties product ids to set + number.
    pm = load('products_map.json', {})
    hits_pm = [int(pid) for pid, m in pm.items() if m['setid'] == a.setid and norm_number(m['number']) == norm_number(a.number)]
    if len(hits_pm) == 1 and not a.cm_id:
        m = pm[str(hits_pm[0])]
        print(f"product map: {a.setid} {a.number} -> Cardmarket product {hits_pm[0]} ({m['conf']} confidence, {m.get('method','')})")
        a.cm_id = hits_pm[0]
    exp = label_expansion(a.setid, setlist, prods, a.cm_exp)
    cands = [p for p in prods if p['idExpansion'] == exp and norm(cmbase(p['name'])) == norm(ghname)]
    if a.cm_id and not any(p['idProduct'] == a.cm_id for p in cands):
        cands += [p for p in prods if p['idProduct'] == a.cm_id]
    search = f"https://www.cardmarket.com/en/Pokemon/Products/Search?idExpansion={exp}&searchString={urllib.parse.quote_plus(ghname)}"
    if not cands: sys.exit(f"no product named '{ghname}' in expansion {exp}. Search: {search}")
    # Same name, different card: Cardmarket's "[Ability | Attack]" bracket must agree with the set list's attacks and abilities.
    def cm_attacks(name):
        m = re.search(r'\[(.*?)\]', name); return {norm(x) for x in m.group(1).split('|')} if m else set()
    if gh_attacks:
        same = [p for p in cands if not cm_attacks(p['name']) or cm_attacks(p['name']) <= gh_attacks]
        dropped = len(cands) - len(same)
        if dropped: print(f"{dropped} same-name product(s) dropped: their attacks/abilities differ from {sorted(gh_attacks)}")
        cands = same
        if not cands: sys.exit(f"no product in expansion {exp} named '{ghname}' with attacks/abilities {sorted(gh_attacks)}. The set list may be behind for a new card; check {search} and pass --cm-id.")
    if a.cm_id:
        pick = next((p for p in cands if p['idProduct'] == a.cm_id), None)
        if not pick: sys.exit(f"--cm-id {a.cm_id} is not one of the candidates")
    elif len(cands) == 1:
        pick = cands[0]
    else:
        print(f"{len(cands)} products share this name in expansion {exp} (rarity per set list: {rarity}). Compare with {search}")
        for p in cands:
            g = guide.get(p['idProduct'], {})
            print(f"  --cm-id {p['idProduct']}   trend {g.get('trend')}   7d {g.get('avg7')}   reverse-holo trend {g.get('trend-holo')}   added {p['dateAdded'][:10]}")
        sys.exit("re-run with --cm-id <id>")
    g = guide.get(pick['idProduct'], {})
    finish = 'reverse' if a.reverse else 'normal'
    key = '-holo' if a.reverse else ''
    n = max(c['n'] for c in binder) + 1
    card = dict(n=n, name=a.name, set=a.set_name or a.setid, num=norm_number(a.number), num_src=a.number, setid=a.setid,
                page=a.page, lang=a.lang, finish=finish, qty=1, cm_id=pick['idProduct'], cm_exp=exp, cm_name=pick['name'],
                trend=g.get('trend' + key), avg30=g.get('avg30' + key), avg7=g.get('avg7' + key), avg1=g.get('avg1' + key), low=g.get('low' + key),
                cmd=load(PRICES)['createdAt'][:10], hist={}, verify=len(cands) > 1, verified=False,
                cm=search, cm_search=search)
    shutil.copy('binder.json', 'binder.last_good.json'); shutil.copy('cards.csv', 'cards.last_good.csv')
    binder.append(card); save('binder.json', binder); write_cards_csv(binder)
    if subprocess.run([sys.executable, os.path.join(CODE, 'validate.py')]).returncode != 0:
        shutil.copy('binder.last_good.json', 'binder.json'); shutil.copy('cards.last_good.csv', 'cards.csv')
        sys.exit("validation failed, add rolled back")
    print(f"added #{n} {a.name} -> Cardmarket product {pick['idProduct']} ({finish}), trend {card['trend']}. Now run refresh.py and republish.")


def cmd_remove(a):
    binder = load('binder.json')
    keep = [c for c in binder if c['n'] != a.n]
    if len(keep) == len(binder): sys.exit(f"no card #{a.n}")
    gone = next(c for c in binder if c['n'] == a.n)
    print(f"removing #{a.n} {gone['name']} ({gone['set']} {gone['num']}, Cardmarket {gone['cm_id']})")
    shutil.copy('binder.json', 'binder.last_good.json'); shutil.copy('cards.csv', 'cards.last_good.csv')
    save('binder.json', keep); write_cards_csv(keep)
    subprocess.run([sys.executable, os.path.join(CODE, 'validate.py')])
    print(f"removed #{a.n} {gone['name']}. Undo: copy binder.last_good.json over binder.json. Now run refresh.py and republish.")


def cmd_finish(a):
    binder = load('binder.json')
    c = next((c for c in binder if c['n'] == a.n), None)
    if not c: sys.exit(f"no card #{a.n}")
    c['finish'] = a.finish; save('binder.json', binder)
    print(f"#{a.n} {c['name']} finish = {a.finish}. Prices switch on the next refresh.py run.")


def cmd_qty(a):
    binder = load('binder.json')
    c = next((c for c in binder if c['n'] == a.n), None)
    if not c: sys.exit(f"no card #{a.n}")
    if a.qty < 1: sys.exit("qty must be at least 1; use remove to drop the card")
    c['qty'] = a.qty; save('binder.json', binder)
    print(f"#{a.n} {c['name']} qty = {a.qty}. Rebuild with refresh.py or build_page.py.")


def cmd_verify(a):
    binder = load('binder.json')
    c = next((c for c in binder if c['n'] == a.n), None)
    if not c: sys.exit(f"no card #{a.n}")
    c['verified'] = True; save('binder.json', binder); print(f"#{a.n} {c['name']} marked verified")


def cmd_list(a):
    for c in load('binder.json'):
        print(f"{c['n']:>3} {c['name'][:32]:32} {c['set'][:28]:28} {c['num']:>6} {c.get('lang','EN')} {c.get('finish','normal'):7} x{c.get('qty',1)} cm {c['cm_id']:>6}  €{c.get('trend')}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('add'); s.add_argument('name'); s.add_argument('setid'); s.add_argument('number')
    s.add_argument('--page', default='New'); s.add_argument('--lang', default='EN'); s.add_argument('--set-name', default=None)
    s.add_argument('--reverse', action='store_true', help='reverse holo copy'); s.add_argument('--cm-id', type=int); s.add_argument('--cm-exp', type=int)
    s.set_defaults(f=cmd_add)
    s = sub.add_parser('remove'); s.add_argument('n', type=int); s.set_defaults(f=cmd_remove)
    s = sub.add_parser('finish'); s.add_argument('n', type=int); s.add_argument('finish', choices=['normal', 'reverse']); s.set_defaults(f=cmd_finish)
    s = sub.add_parser('qty'); s.add_argument('n', type=int); s.add_argument('qty', type=int); s.set_defaults(f=cmd_qty)
    s = sub.add_parser('verify'); s.add_argument('n', type=int); s.set_defaults(f=cmd_verify)
    s = sub.add_parser('list'); s.set_defaults(f=cmd_list)
    a = ap.parse_args(); a.f(a)
