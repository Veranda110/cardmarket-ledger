"""Build products_map.json: every English Cardmarket Pokémon product id -> set code, number, name, rarity.

Run:  py -3.13 build_product_map.py          (reads/writes in ./data)

Why: Cardmarket's export has product ids, names like "Eevee [Call for Family | Gnaw]" and expansion ids,
but no set names and no card numbers. This map is what turns the price history into card-level data.

Inputs (all in data/):
  products_singles_6.json   Cardmarket product list
  price_guide_6.json        today's Cardmarket prices; history/*.json older exports (more fingerprint dates)
  set_names.json            per set code: [name, number, rarity, [attacks+abilities]]  (pokemon-tcg-data)
  set_meta.json             set code -> name, series, release, total
  cm_expansion_labels.json  expansion id -> set code (fingerprinted earlier; extended here for old sets)
  ptcgio_cardmarket.json    per set code: pokemontcg.io's Cardmarket price snapshot per card number (the fingerprint)

Method, per labelled expansion:
  1. Normalise names on both sides (drop "Lv.43", unify "-EX"/"EX", "-GX"/"GX", "δ Delta Species", "M "/"Mega ").
  2. Group Cardmarket products and set-list entries by normalised name.
  3. Split groups by attacks/abilities, matched with tolerance (prefix or edit distance <= 2).
  4. One product : one entry -> match, confidence "high".
     Several : several -> price FINGERPRINT: pokemontcg.io's Cardmarket (trend, avg30) for each card number
     against each product's (trend, avg30) in every export we have; nearest in log space wins.
     "high" if the runner-up is more than 2x further away, else "medium".
     No fingerprint available -> price rank vs rarity rank, "low".
Output: products_map.json, plus a report of unmatched products and entries.
"""
import json, re, os, glob, math, collections, difflib

CODE = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.environ.get('LEDGER_DATA', os.path.join(CODE, 'data')))

def load(p): return json.load(open(p, encoding='utf-8'))
P = load('products_singles_6.json')['products']
sn = load('set_names.json'); meta = load('set_meta.json')
lab = {int(k): v for k, v in load('cm_expansion_labels.json').items()}
fp = load('ptcgio_cardmarket.json') if os.path.exists('ptcgio_cardmarket.json') else {}

snaps = {}
for f in sorted(glob.glob('history/*.json')) + ['price_guide_6.json']:
    d = load(f); snaps[d['createdAt'][:10]] = {g['idProduct']: g for g in d['priceGuides']}
today = max(snaps)

def norm(s): return re.sub(r'[^a-z0-9★♀♂δ]', '', s.lower())
def norm_name(s):
    s = re.sub(r'\s*\[[^\]]*\]$', '', s)                          # trailing "[attacks]" bracket
    # Platinum owner tags: Cardmarket "Gallade [4] LV.X" = pokemon-tcg-data "Gallade E4 LV.X"; [G] Galactic, [GL] Gym Leader, [FB] Frontier Brain, [C] Champion
    s = re.sub(r'\s*\[4\]', ' E4', s)
    s = re.sub(r'\s*\[(G|GL|E4|FB|C)\]', r' \1', s)
    s = s.replace('[M]', '♂').replace('[F]', '♀')                    # "Nidoran [M]" = "Nidoran ♂"
    s = s.split(' (')[0]
    s = re.sub(r'\s+-\s+.*$', '', s)                                # trainer subtitles: "Professor's Research - Professor Juniper"
    s = re.sub(r'\s+Lv\.?\s*\d+\s*$', '', s, flags=re.I)            # "Wailord Lv.43"
    s = re.sub(r'\s+LV\.X$', ' LV.X', s, flags=re.I)
    s = s.replace('-EX', ' EX').replace('-GX', ' GX').replace('δ Delta Species', 'δ').replace('Gold Star', '★')
    s = s.replace('&female;', '♀').replace('&male;', '♂')
    s = re.sub(r'^M\s*(?=[A-Z])', 'Mega ', s) if re.match(r'^M[A-Z]', s) else s
    s = re.sub(r'^M\s+', 'Mega ', s)
    return norm(s)
def is_card(name):
    """Cardmarket lists code cards as singles; they are not cards."""
    return not re.match(r'^(Online|Live) Code Card', name)
def cm_atts(name):
    m = re.search(r'\[(.*?)\]', name); return [norm(x) for x in m.group(1).split('|')] if m else []
def att_ok(cm_list, entry_list):
    """every Cardmarket bracket item must resemble one entry attack/ability"""
    if not cm_list or not entry_list: return True
    ent = [norm(x) for x in entry_list]
    for a in cm_list:
        if not any(a == b or a.startswith(b) or b.startswith(a) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.85 for b in ent):
            return False
    return True

RANK = ['Common', 'Uncommon', 'Rare', 'Promo', 'Rare Holo', 'Rare Holo EX', 'Rare Holo LV.X', 'Rare Holo GX', 'Rare Holo V',
        'Rare Holo VMAX', 'Rare Holo VSTAR', 'Double Rare', 'Trainer Gallery Rare Holo', 'Rare Ultra', 'Ultra Rare', 'Rare Shiny',
        'Shiny Rare', 'Illustration Rare', 'Rare Shiny GX', 'Shiny Ultra Rare', 'Special Illustration Rare', 'Rare Rainbow',
        'Hyper Rare', 'Rare Secret']
def rrank(r): return RANK.index(r) if r in RANK else 4

def price_vec(pid):
    """(trend, avg30) pairs for this product across all exports we hold"""
    out = []
    for d, s in snaps.items():
        g = s.get(pid)
        if g and g.get('trend') and g.get('avg30'): out.append((g['trend'], g['avg30']))
    return out
def dist(fpv, vecs):
    t, a = fpv
    if not vecs or not t or not a: return None
    return min(abs(math.log(t / v[0])) + abs(math.log(a / v[1])) for v in vecs if v[0] > 0 and v[1] > 0)

# --- expansions per set code (a set may span several Cardmarket ids, a Cardmarket id may hold sub-sets)
exps_of = collections.defaultdict(list)
for e, s in lab.items(): exps_of[s].append(e)
byexp = collections.defaultdict(list)
for p in P: byexp[p['idExpansion']].append(p)

PARENT = {'sma': 'sm115', 'swsh45sv': 'swsh45', 'swsh12pt5gg': 'swsh12pt5', 'cel25c': 'cel25', 'swsh9tg': 'swsh9',
          'swsh10tg': 'swsh10', 'swsh11tg': 'swsh11', 'swsh12tg': 'swsh12', 'sv3pt5': 'sv3pt5'}
# which set codes live inside each expansion id: the labelled one plus any sub-set whose parent is labelled there
sets_in_exp = collections.defaultdict(set)
for e, s in lab.items():
    sets_in_exp[e].add(s)
    for sub, par in PARENT.items():
        if par == s and sub in sn: sets_in_exp[e].add(sub)      # expansion labelled with the parent: add its sub-sets
        if sub == s and par in sn: sets_in_exp[e].add(par)      # expansion labelled with a sub-set: add the parent too

def uniques(e, sets):
    """products in expansion e whose normalised name occurs once among products and once among the sets' entries"""
    prods = [p for p in byexp[e] if p['idProduct'] in snaps[today] and is_card(p['name'])]
    gp = collections.defaultdict(list); ge = collections.defaultdict(list)
    for p in prods: gp[norm_name(p['name'])].append(p)
    for s in sorted(sets):
        for x in sn.get(s, []): ge[norm_name(x[0])].append((s, x))
    for name, ps in gp.items():
        if len(ps) == 1 and len(ge.get(name, [])) == 1: yield ps[0], ge[name][0]

# --- fingerprint reliability per set. pokemontcg.io's Cardmarket prices are only a usable tiebreaker when, for the cards
# that need no tiebreak (unique name), they agree with the prices in our exports. Where they do not (old sets whose
# mirror prices point at another printing, 151 in 2026), ties fall back to price rank vs rarity rank.
FP_AGREE = math.log(1.5); FP_MIN_RATE = 0.5; FP_MIN_N = 5
fp_stat = collections.defaultdict(lambda: [0, 0])
for e, sets in sets_in_exp.items():
    for p, (s, x) in uniques(e, sets):
        rec = next((c for c in fp.get(s, []) if c['number'] == x[1]), None)
        if not (rec and rec.get('trend') and rec.get('avg30')): continue
        d = dist((rec['trend'], rec['avg30']), price_vec(p['idProduct']))
        if d is None: continue
        fp_stat[s][0] += 1; fp_stat[s][1] += d < FP_AGREE
fp_ok = {s: (n < FP_MIN_N or hits / n >= FP_MIN_RATE) for s, (n, hits) in fp_stat.items()}
fp_unreliable = sorted(s for s, ok in fp_ok.items() if not ok)
print(f"fingerprint unreliable for {len(fp_unreliable)} sets (falls back to rarity rank): {fp_unreliable}")

mapping = {}; report = collections.Counter(); unmatched_products = []; unmatched_entries = []
for e, sets in sets_in_exp.items():
    prods = [p for p in byexp[e] if p['idProduct'] in snaps[today] and is_card(p['name'])]
    entries = [(s, x) for s in sorted(sets) for x in sn.get(s, [])]   # sorted: deterministic tie-breaks
    gp = collections.defaultdict(list); ge = collections.defaultdict(list)
    for p in prods: gp[norm_name(p['name'])].append(p)
    for s, x in entries: ge[norm_name(x[0])].append((s, x))
    for name, ps in gp.items():
        es = ge.get(name, [])
        if not es:
            for p in ps: unmatched_products.append((p['idProduct'], p['name'], e)); report['product without entry'] += 1
            continue
        # split by attacks: for each product, the entries whose attacks fit
        used = set()
        # first pass: products whose attack-compatible entries are exactly one -> high
        pending = []
        for p in ps:
            fits = [(s, x) for s, x in es if att_ok(cm_atts(p['name']), x[3] if len(x) > 3 else [])]
            if not fits: fits = es
            pending.append((p, fits))
        # group products sharing the same fit-set, resolve each group
        groups = collections.defaultdict(list)
        for p, fits in pending: groups[tuple(sorted((s, x[1]) for s, x in fits))].append(p)
        for key, group in groups.items():
            cands = [(s, x) for s, x in es if (s, x[1]) in set(key)]
            if len(group) == 1 and len(cands) == 1:
                s, x = cands[0]; p = group[0]
                mapping[p['idProduct']] = dict(setid=s, set=meta[s]['name'], number=x[1], name=x[0], rarity=x[2], lang='EN', conf='high', method='name+attacks unique')
                report['high'] += 1; continue
            # fingerprint each candidate entry
            fpd = {}
            for s, x in cands:
                rec = next((c for c in fp.get(s, []) if c['number'] == x[1]), None)
                if rec and rec.get('trend') and rec.get('avg30') and fp_ok.get(s, True): fpd[(s, x[1])] = (rec['trend'], rec['avg30'])
            assigned = {}
            if fpd:
                pairs = []
                for p in group:
                    vecs = price_vec(p['idProduct'])
                    for k, v in fpd.items():
                        d = dist(v, vecs)
                        if d is not None: pairs.append((d, p['idProduct'], k))
                pairs.sort()
                usedp, usede = set(), set()
                for d, pid, k in pairs:
                    if pid in usedp or k in usede: continue
                    others = [dd for dd, pp, kk in pairs if pp == pid and kk != k]
                    conf = 'high' if (not others or min(others) > d + math.log(2)) else 'medium'
                    assigned[pid] = (k, conf, f'price fingerprint d={d:.2f}'); usedp.add(pid); usede.add(k)
            # fall back for anything left: price rank vs rarity rank
            left_p = [p for p in group if p['idProduct'] not in assigned]
            left_e = [(s, x) for s, x in cands if (s, x[1]) not in {v[0] for v in assigned.values()}]
            if left_p and left_e:
                left_p.sort(key=lambda p: snaps[today][p['idProduct']].get('trend') or 0)
                # same rarity in main set and sub-set (Zamazenta V 98 vs GG54, both 'Rare Holo V'): the sub-set print is the pricier one
                left_e.sort(key=lambda se: (rrank(se[1][2]), se[0] in PARENT and PARENT[se[0]] != se[0], se[1][1]))
                for i, p in enumerate(left_p):
                    s, x = left_e[min(i, len(left_e) - 1)]
                    assigned[p['idProduct']] = ((s, x[1]), 'low' if len(left_p) != len(left_e) else 'medium', 'price rank vs rarity')
            left_p = [p for p in group if p['idProduct'] not in assigned]
            if left_p and assigned:
                for p in left_p:
                    t = snaps[today][p['idProduct']].get('trend') or 0.01
                    near = min(assigned, key=lambda q: abs(math.log(t / ((snaps[today][q].get('trend') or 0.01)))))
                    assigned[p['idProduct']] = (assigned[near][0], 'low', f'variant of product {near} (same name and attacks; oversized, stamped or duplicate listing)')
            for p in group:
                if p['idProduct'] in assigned:
                    (s, num), conf, how = assigned[p['idProduct']]
                    x = next(x for ss, x in cands if ss == s and x[1] == num)
                    mapping[p['idProduct']] = dict(setid=s, set=meta[s]['name'], number=num, name=x[0], rarity=x[2], lang='EN', conf=conf, method=how)
                    report[conf] += 1
                else:
                    unmatched_products.append((p['idProduct'], p['name'], e)); report['product unresolved'] += 1
    matched_entries = {(m['setid'], m['number']) for m in mapping.values()}
    for s, x in entries:
        if (s, x[1]) not in matched_entries and x[2] not in ('',) : unmatched_entries.append((s, x[1], x[0]))

# --- twin screen: does each labelled expansion's price level agree with pokemontcg.io's Cardmarket prices for that set?
# A Japanese twin (same names, other product ids, other prices) scores near 0 hits. Only possible where the fingerprint is cached.
twin = {}
for e, sets in sets_in_exp.items():
    n = hits = 0
    for p in byexp[e]:
        m = mapping.get(p['idProduct'])
        if not m: continue
        rec = next((c for c in fp.get(m['setid'], []) if c['number'] == m['number']), None)
        if not (rec and rec.get('trend') and rec.get('avg30')): continue
        d = dist((rec['trend'], rec['avg30']), price_vec(p['idProduct']))
        if d is None: continue
        n += 1; hits += d < math.log(1.5)
    if n >= 5:
        twin[e] = dict(sets=sorted(sets), compared=n, hits=hits, rate=round(hits / n, 2))
        if hits / n < 0.3:
            print(f"WARN expansion {e} labelled {sorted(sets)}: only {hits}/{n} products match the set's price fingerprint. Japanese twin or wrong label?")
            report['expansion suspect'] += 1

json.dump(mapping, open('products_map.json', 'w', encoding='utf-8'), indent=0)
json.dump({'unmatched_products': unmatched_products, 'unmatched_entries': unmatched_entries, 'expansion_fingerprint_agreement': twin,
           'fingerprint_unreliable_sets': fp_unreliable, 'fingerprint_agreement_per_set': {s: dict(compared=n, hits=h) for s, (n, h) in fp_stat.items()}},
          open('products_map_report.json', 'w', encoding='utf-8'), indent=0)
labelled = sum(len(byexp[e]) for e in sets_in_exp)
print(f"products in labelled English expansions: {labelled}; mapped: {len(mapping)}")
print("confidence:", dict(report))
print(f"unmatched products: {len(unmatched_products)}, set-list entries without a product: {len(unmatched_entries)}")
