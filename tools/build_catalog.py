"""Build Scoop's generated catalog (GEN) from brand Shopify feeds + Open Food Facts.

Output: gen_catalog.js containing `const GEN=[...]` — one object per product:
{id,cat,brand,name,size,serv,price,was,store,n,img,fit,site,tags}
Prices on Shopify items come from the brand's own list price; the "deal" markdown and all
Open Food Facts prices are prototype placeholders.
"""
import json, glob, re, os, hashlib, html

S = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(S, 'cat')

def h(s, mod):
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % mod

def load(pattern):
    out, seen = [], set()
    for f in sorted(glob.glob(os.path.join(S, 'feeds', os.path.basename(pattern)))):  # saved store feeds
        try:
            for p in json.load(open(f, encoding='utf-8'))['products']:
                if p['id'] not in seen:
                    seen.add(p['id']); out.append(p)
        except Exception:
            pass
    return out

EXCLUDE = re.compile(r"\b(shirt|tee|t-shirt|hoodie|hat|cap\b|beanie|sock|gift ?card|sample|bundle|stack|merch|sticker|refurb|certification|subscription|e-?book|tank|shorts?\b|jogger|legging|bra\b|jacket|crew\b|pullover|sweat|towel|backpack|duffel|bag\b|mystery|shipping|warranty|protection plan|kit\b|pack of samples|trial|variety box|gift|decal|poster|mat\b|apparel|scratch|dent|replacement|spare|part\b|parts\b|cable|charger|case\b|attachment head|pin\b|keychain|lanyard|flag|visor|glasses|collar|lock\b|j-hooks?|spotter|pulley|carabiner|insert|pad\b|pads\b|cover\b|sleeve for|charging|stand\b|applicator|attachment|mount|safet|funnel|adapter|hardware|bracket|j-cup|combo|box \d|holder|storage|wall\b|hanger|clip\b|strap for|refill pack|freedom leather|3-fc|thermal|knit|crewneck|run gloves|climbskin|spare|connector|marker|backing|dock\b|adapter|clips?\b|collars?\b|cloth|expansion|extension kit|converter|seat\b|assembly|guard|open box|legacy|shelf|shelves|long sleeve|short sleeve|polo|waffle project|compression|seamless|pump cover|top\b|romper|onesie)", re.I)

RULES = [
    ('Shakers & bottles', r'shaker|blender ?bottle|bottle|tumbler|jug\b|pillbox|protein funnel'),
    ('Recovery tools', r'theragun|massage|hypervolt|normatec|vibrat|foam roll|percussion|venom|recovery ?air|wave ?(roller|solo|duo)|vyper|mini\b.*gun|x-?ray|thermal'),
    ('Mass gainers', r'mass gainer|weight gainer|gainer|serious mass'),
    ('Pre-workout', r'pre-?workout|\bpump\b|\bstim\b|\bpre\b|nitric|n\.?o\.? boost|preworkout|pre-lit|pre lit'),
    ('Creatine', r'creatine'),
    ('Protein shakes', r'ready[- ]to[- ]drink|\brtd\b|protein shake|protein drink|core power|nutrition shake|shake\b(?!r)'),
    ('Protein', r'\bwhey\b|isolate|casein|protein powder'),
    ('Bars', r'protein bar|\bbars?\b|crisp bar|cookie|wafer'),
    ('Snacks', r'chips|crackers|puffs|pretzel|crisps|popcorn|jerky|cereal\b|peanut butter|pb\b|pancake|oatmeal|brownie|candy|gummies bites'),
    ('Energy drinks', r'energy drink|energy\b|\bcans?\b|sparkling|zero sugar.*energy'),
    ('Hydration', r'hydration|electrolyte|hydrate|sticks\b.*hydra|hydro\b|sports drink|lmnt|liquid i\.?v'),
    ('Aminos & recovery', r'\beaa|\bbcaa|amino|glutamine|recovery|intra|citrulline'),
    ('Protein', r'protein|whey|isolate|casein|\biso\b|plant based|vegan protein|pea protein|beef protein|egg white'),
    ('Vitamins & health', r'collagen|greens|superfood|vitamin|multi|fish oil|omega|magnesium|ashwagandha|probiotic|sleep|zinc|d3|fiber|turmeric|elderberry|melatonin|test(osterone)? booster|testosterone|burner|shred|nootropic|focus|keto|mct|capsule|tablet|softgel|gummies|gummy|beet|l-carnitine|carnitine|berberine|cla\b|tongkat|shilajit|biotin|fish|krill|caffeine pills|immune|joint|glucosamine|cortisol|nad\b|coq10|b12|iron\b|potassium|apple cider|colostrum|hair|beauty'),
    ('Straps & grips', r'strap|grips?\b|hook|glove'),
    ('Belts', r'\bbelt'),
    ('Sleeves & wraps', r'sleeve|wrap'),
    ('Chalk', r'chalk'),
    ('Equipment', r'\brack\b|\bplates?\b|dumbbell|kettlebell|barbell|bench|suspension trainer|trx|landmine|cable machine|power tower|pull[- ]?up|dip station|squat|trap bar|bar\b|smith|leg press|functional trainer|rower|bike|treadmill|med(icine)? ball|slam ball|jump rope|resistance band|bands\b|gloves'),
]
RULES = [(c, re.compile(r, re.I)) for c, r in RULES]

def classify(text, force=None):
    if force:
        return force
    for c, rx in RULES:
        if rx.search(text):
            return c
    return None

def tcase(t):
    return ' '.join(w[:1].upper() + w[1:] for w in t.split(' '))

def clean_name(t, brand):
    orig = t
    t = clean_name_inner(t, brand)
    if len(t) < 4 or t.lower() in brand.lower():
        t = clean_name_inner(orig, '~')  # don't strip the brand when that leaves nothing useful
    return t

def clean_name_inner(t, brand):
    t = html.unescape(t)
    t = re.sub(r'[^\x00-ɏ–—’\s]', '', t)  # emoji & symbols
    t = re.sub(r'\b(CLEARANCE|NEW!?|SALE|LIMITED( EDITION)?|BEST SELLER)\b[:!\- ]*', '', t)
    t = re.sub(r'\s*\+\s*free .*$', '', t, flags=re.I)
    t = t.replace(' | ', ', ')
    t = re.sub(r'[\u2122\u00ae\u00a9\ufffd]', '', t)
    first = brand.split()[0]
    for b in {brand, brand.upper()} | ({first, first.upper()} if len(first) >= 5 else set()):
        t = re.sub(r'^\s*' + re.escape(b) + r'[\s:\-–|]+', '', t)
    t = re.sub(r'^\s*(Nutrition|Supplement Science|Sports)\s+', '', t)
    t = re.sub(r'\s*\((pro program|testing)\)\s*', ' ', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip(' -|–')
    if t.isupper() or sum(ch.isupper() for ch in t) > 0.7 * sum(ch.isalpha() for ch in t):
        t = tcase(t.lower())
        t = re.sub(r'\b(Eaa|Bcaa|Rtd|Mct|Cla|Nad|Hmb|Xl|Xxl|V\d|Iso|Pb|Usa|Ipf|Uk|Us|Id)\b', lambda m: m.group(0).upper(), t)
    if t == t.lower():
        t = tcase(t)
    return t[:58]

STORE_POOLS = {
    'grocery': ['Walmart', 'Target', 'Costco', 'Amazon'],
    'supp': ['Amazon', 'GNC', 'Vitamin Shoppe', 'iHerb', 'Bodybuilding.com', 'Walmart', 'Brand direct'],
    'gear': ['Amazon', 'Brand direct', 'Walmart', 'Bodybuilding.com'],
}
def pool_of(cat):
    if cat in ('Energy drinks', 'Hydration', 'Protein shakes', 'Snacks', 'Bars'):
        return 'grocery'
    if cat in ('Equipment', 'Straps & grips', 'Belts', 'Sleeves & wraps', 'Chalk', 'Recovery tools', 'Shakers & bottles'):
        return 'gear'
    return 'supp'

def deal_prices(key, list_price, compare):
    list_price = float(list_price)
    if compare and float(compare) > list_price * 1.03:
        return round(list_price, 2), round(float(compare), 2)
    disc = 0.08 + h(key + 'd', 23) / 100  # 8%..30%
    p = list_price * (1 - disc)
    p = (int(p) + (0.49 if p - int(p) < 0.5 else 0.99)) if p > 3 else round(p, 2)
    return round(p, 2), round(list_price, 2)

# ---------------- packshot detection ----------------
# A packshot has a plain background: the outer frame of the photo is one uniform colour (or transparent).
# Lifestyle shots (people, hands, gyms, tables) have busy borders. Scores are cached in img_scores.json.
import io, urllib.request
from concurrent.futures import ThreadPoolExecutor
SCORE_FILE = os.path.join(S, 'img_scores.json')
SCORES = json.load(open(SCORE_FILE)) if os.path.exists(SCORE_FILE) else {}

def thumb_url(u):
    return u + ('&' if '?' in u else '?') + 'width=160'

def border_score(u):
    if u in SCORES:
        return SCORES[u]
    try:
        from PIL import Image
        import numpy as np
        raw = urllib.request.urlopen(urllib.request.Request(thumb_url(u), headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
        im = Image.open(io.BytesIO(raw)).convert('RGBA').resize((120, 120))
        a = np.asarray(im).astype(int)
        m = np.zeros((120, 120), bool); b = 8
        m[:b, :] = m[-b:, :] = m[:, :b] = m[:, -b:] = True
        px = a[m]
        transparent = (px[:, 3] < 20).mean()
        rgb = px[px[:, 3] >= 20][:, :3]
        if len(rgb) == 0:
            sc = 1.0
        else:
            med = np.median(rgb, axis=0)
            close = (np.abs(rgb - med).max(axis=1) <= 22).mean()
            sc = float(transparent + (1 - transparent) * close)
    except Exception:
        sc = -1.0
    SCORES[u] = sc
    return sc

def prefetch(urls):
    todo = [u for u in dict.fromkeys(urls) if u not in SCORES]
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(border_score, todo))
    json.dump(SCORES, open(SCORE_FILE, 'w'))

PACKSHOT = 0.80

# photos rejected on visual review (nutrition-facts labels, action shots)
BAD_IMG = set(json.load(open(os.path.join(S, 'bad_imgs.json')))) if os.path.exists(os.path.join(S, 'bad_imgs.json')) else set()

def pick_packshot(p):
    for im in (p.get('images') or [])[:5]:
        if im['src'].split('?')[0] in BAD_IMG or re.search(r'ingredient|nutrition|facts|label|panel|sfp|lifestyle|model', im['src'].split('?')[0].rsplit('/', 1)[-1], re.I):
            continue
        u = im['src'].split('?')[0] + '?v=1'
        if border_score(u) >= PACKSHOT:
            return im['src'].split('?')[0] + '?width=600'
    return None

GEN, NAMES = [], set()
ids = set()
def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40]

def add(brand, site, name, cat, size, price, was, img, fit, key, tags, store_hint=None, serv=0):
    base = re.split(r'\s[-–]\s|,\s', name)[0].lower()
    for w in re.findall(r'[a-z0-9]+', brand.lower()):
        base = re.sub(r'\b' + re.escape(w) + r'\b', '', base)
    nk = (brand.lower(), re.sub(r'[^a-z0-9]', '', base)[:28])
    if nk in NAMES or not img or price <= 0:
        return False
    NAMES.add(nk)
    pid = slug(brand)[:10] + '-' + slug(name)[:28]
    while pid in ids:
        pid += 'x'
    ids.add(pid)
    pool = STORE_POOLS[pool_of(cat)]
    store = store_hint or pool[h(key + 's', len(pool))]
    GEN.append(dict(id=pid, cat=cat, brand=brand, name=name, size=size, serv=serv, price=price, was=was,
                    store=store, n=2 + h(key + 'n', 6), img=img, fit=fit, site=site, tags=tags))
    return True

# ---------------- Shopify brands ----------------
SHOP = [
    # pattern, brand, site, cap, force-category, only product_types (None=any)
    ('cat/1stphorm.com.json', '1st Phorm', '1stphorm.com', 14, None, {'Products'}),
    ('cat/bloomnu.com.json', 'Bloom Nutrition', 'bloomnu.com', 8, None, {'Vitamins & Supplements', 'Drinks', ''}),
    ('cat/drinkprime.com.json', 'Prime', 'drinkprime.com', 12, None, None),
    ('cat/getrawnutrition.com.json', 'Raw Nutrition', 'getrawnutrition.com', 12, None, {'Supplements', 'Energy Drink', ''}),
    ('cat/jockofuel.com.json', 'Jocko Fuel', 'jockofuel.com', 8, None, {'Supplement', 'Protein Powder', 'Pro Series Supplements'}),
    ('cat/redcon1.com.json', 'Redcon1', 'redcon1.com', 10, None, {'Supplement', ''}),
    ('cat/www.bellsofsteel.us*.json', 'Bells of Steel', 'bellsofsteel.us', 10, 'Equipment', None),
    ('cat/www.blenderbottle.com.json', 'BlenderBottle', 'blenderbottle.com', 8, 'Shakers & bottles', None),
    ('cat/www.bpisports.com.json', 'BPI Sports', 'bpisports.com', 8, None, None),
    ('cat/www.cellucor.com.json', 'Cellucor', 'cellucor.com', 14, None, {'Energy Drink', 'Pre-Workout', 'Amino & EAA', 'Creatine', 'Protein', 'Fat Burner', 'Hydration'}),
    ('cat/www.evlnutrition.com.json', 'EVL Nutrition', 'evlnutrition.com', 10, None, {'Health & Wellness', 'Recovery', 'Pre-Workout', 'Protein', 'Creatine', ''}),
    ('cat/www.ghostlifestyle.com.json', 'Ghost', 'ghostlifestyle.com', 16, None, {'HYDRATION', 'PRE-WORKOUT', 'PROTEIN', 'ENERGY', 'AMINO', 'CREATINE', 'GREENS', 'ENERGY DRINK', 'VITAMINS', 'BURN', 'SIZE', 'PUMP', ''}),
    ('ghostlifestyle-*.json', 'Ghost', 'ghostlifestyle.com', 0, None, None),
    ('cat/www.gorillamind.com.json', 'Gorilla Mind', 'gorillamind.com', 10, None, {'Supplement', 'Health Supplement', 'Nootropic', 'Pre-Workout', 'Energy Drink', ''}),
    ('cat/www.harbingerfitness.com.json', 'Harbinger', 'harbingerfitness.com', 10, None, None),
    ('cat/www.hyperice.com.json', 'Hyperice', 'hyperice.com', 7, 'Recovery tools', {'Recovery Device'}),
    ('cat/www.jymsupplementscience.com.json', 'JYM', 'jymsupplementscience.com', 7, None, {'Vitamins & Supplements', 'Supplements'}),
    ('cat/www.kagedmuscle.com.json', 'Kaged', 'kagedmuscle.com', 10, None, {'Supplement', ''}),
    ('cat/www.mutantnation.com.json', 'Mutant', 'mutantnation.com', 5, None, {'Pre-Workout', 'Protein', 'Shakers & Bottles', ''}),
    ('cat/www.nakednutrition.com.json', 'Naked Nutrition', 'nakednutrition.com', 10, None, {'Protein Powder', 'Chocolate Protein', 'Weight Gainer', ''}),
    ('cat/www.nutricost.com.json', 'Nutricost', 'nutricost.com', 16, None, None),
    ('cat/www.onnit.com.json', 'Onnit', 'onnit.com', 6, None, None),
    ('cat/www.orgain.com.json', 'Orgain', 'orgain.com', 10, None, {'Powders', 'Drinks', 'Bars'}),
    ('cat/www.rysesupps.com.json', 'Ryse', 'rysesupps.com', 12, None, None),
    ('cat/www.therabody.com.json', 'Therabody', 'therabody.com', 7, 'Recovery tools', {'Theragun', 'RecoveryAir', 'Wave'}),
    ('cat/www.titan.fitness*.json', 'Titan Fitness', 'titan.fitness', 14, 'Equipment', None),
    ('cat/www.trxtraining.com.json', 'TRX', 'trxtraining.com', 5, 'Equipment', {'Suspension Trainers', 'Free Weights'}),
    ('cat/www.vitalproteins.com.json', 'Vital Proteins', 'vitalproteins.com', 8, 'Vitamins & health', None),
    ('alaninu-*.json', 'Alani Nu', 'alaninu.com', 14, None, None),
    ('transparentlabs-*.json', 'Transparent Labs', 'transparentlabs.com', 12, None, None),
    ('questnutrition-*.json', 'Quest', 'questnutrition.com', 12, None, None),
    ('optimumnutrition-*.json', 'Optimum Nutrition', 'optimumnutrition.com', 12, None, None),
    ('repfitness-*.json', 'REP Fitness', 'repfitness.com', 12, 'Equipment', None),
    ('bowflex-*.json', 'Bowflex', 'bowflex.com', 5, 'Equipment', None),
    ('g-gymreapers.com.json', 'Gymreapers', 'gymreapers.com', 10, None, None),
    ('g-ekkovision.com.json', 'Ekkovision', 'ekkovision.com', 6, None, None),
    ('g-frictionlabs.com.json', 'Friction Labs', 'frictionlabs.com', 4, 'Chalk', None),
    ('g-versagripps.com.json', 'Versa Gripps', 'versagripps.com', 4, None, None),
    ('g-us.sbdapparel.com.json', 'SBD', 'sbdapparel.com', 0, None, None),  # all SBD photos are on-model
    ('g-harbingerfitness.com.json', 'Harbinger', 'harbingerfitness.com', 0, None, None),
    # mainstream brands' own stores (official packshots)
    ('cat/x-3denergydrinks.com.json', '3D Energy', '3denergydrinks.com', 6, 'Energy drinks', None),
    ('cat/x-gfuel.com.json', 'G Fuel', 'gfuel.com', 10, 'Energy drinks', {'Tub', 'Pack'}),
    ('cat/x-zoaenergy.com.json', 'ZOA', 'zoaenergy.com', 8, 'Energy drinks', None),
    ('cat/x-www.rockstarenergy.com.json', 'Rockstar', 'rockstarenergy.com', 12, 'Energy drinks', None),
    ('cat/x-liquid-iv.com.json', 'Liquid I.V.', 'liquid-iv.com', 10, 'Hydration', {'Hydration Multiplier', 'Hydration Multiplier Sugar-Free', 'Sugar-Free Energy Multiplier', 'Hydration Multiplier +'}),
    ('cat/x-www.drinklmnt.com.json', 'LMNT', 'drinklmnt.com', 6, 'Hydration', {'Product'}),
    ('cat/x-shop.barebells.com.json', 'Barebells', 'barebells.com', 10, 'Bars', {'Protein Bars'}),
    ('cat/x-www.built.com.json', 'Built', 'built.com', 8, 'Bars', {'BUILT Puff', 'Puffs', 'Bar', 'Sour Puff'}),
    ('cat/x-shop.fairlife.com.json', 'Fairlife', 'fairlife.com', 6, 'Protein shakes', None),
    ('cat/x-www.muscletech.com.json', 'MuscleTech', 'muscletech.com', 8, None, None),
    ('cat/x-www.pureprotein.com.json', 'Pure Protein', 'pureprotein.com', 8, None, {'Food', ''}),
    ('cat/x-theisopurecompany.com.json', 'Isopure', 'theisopurecompany.com', 8, None, None),
]

# parallel pre-pass: score photos (1st, then 2nd, ... for products still lacking a packshot)
_cands = []
for pattern, brand, site, cap, force, types in SHOP:
    if cap == 0:
        continue
    for p in load(pattern):
        if (types is None or (p.get('product_type', '') or '') in types) and not EXCLUDE.search(p.get('title', '')) and p.get('images'):
            _cands.append(p)
_key = lambda im: im['src'].split('?')[0] + '?v=1'
for k in range(5):
    urls = [_key(p['images'][k]) for p in _cands if len(p['images']) > k and not any(SCORES.get(_key(im), 0) >= PACKSHOT for im in p['images'][:k])]
    prefetch(urls)
    print('scored round', k + 1, len(urls), 'photos', flush=True)

brand_count = {}
for pattern, brand, site, cap, force, types in SHOP:
    if cap == 0:
        continue
    prods = load(pattern)
    if force == 'Equipment':  # core gear first so racks/dumbbells/kettlebells win the brand's slots (max 2 per type)
        PRI = [r'power rack|half rack|squat rack', r'dumbbell', r'kettlebell', r'barbell|trap bar', r'bench', r'bumper plate|plates?\b',
               r'pull-?up bar', r'slam ball|medicine ball', r'bike|rower', r'landmine|cable|suspension|ybell|home gym|pulldown']
        def pri(p):
            for i, rx in enumerate(PRI):
                if re.search(rx, p.get('title', ''), re.I):
                    return i
            return 99
        picked, per = [], {}
        for p in sorted(prods, key=pri):
            k = pri(p)
            if k < 99 and per.get(k, 0) < 2 and not EXCLUDE.search(p.get('title', '')):
                per[k] = per.get(k, 0) + 1
                picked.append(p)
        prods = picked
    for p in prods:
        if brand_count.get(brand, 0) >= cap:
            break
        title = p.get('title', '')
        ptype = p.get('product_type', '') or ''
        if types is not None and ptype not in types:
            continue
        text = title + ' ' + ptype + ' ' + ' '.join(p.get('tags', [])[:12] if isinstance(p.get('tags'), list) else [])
        if EXCLUDE.search(title) or (EXCLUDE.search(ptype) and brand != 'Fairlife'):  # Fairlife files shakes under "Merchandise"
            continue
        if not p.get('images'):
            continue
        # sold out at the brand store is fine — Scoop compares other retailers
        vs = [v for v in p.get('variants', []) if v.get('available', True)] or p.get('variants', [])
        if not vs:
            continue
        v = vs[0]
        cat = classify(title + ' ' + ptype, None) or (force if force else None)
        if force and cat not in ('Straps & grips', 'Belts', 'Sleeves & wraps', 'Chalk', 'Shakers & bottles', 'Recovery tools', 'Equipment', 'Vitamins & health'):
            cat = force
        if force in ('Recovery tools', 'Shakers & bottles', 'Vitamins & health', 'Chalk', 'Equipment', 'Energy drinks', 'Hydration', 'Bars', 'Protein shakes'):
            cat = force
        if not cat:
            continue
        try:
            lp = float(v['price'])
        except Exception:
            continue
        if lp < 3 or lp > 3000:
            continue
        if brand == 'Rockstar' and ptype and ptype.lower() not in title.lower():
            title = ptype + ' ' + title  # "Punched" + "Lime Freeze"
        name = clean_name(title, brand)
        if len(name) < 3:
            continue
        size = v.get('title', '')
        size = '' if size in ('Default Title', 'Default', 'US', 'Other') else re.sub(r'[™®©]', '', html.unescape(size)).replace(' / ', ' · ')
        m = re.search(r'(\d+)\s*(servings|serv)', (title + ' ' + size).lower())
        serv = int(m.group(1)) if m else 0
        price, was = deal_prices(str(p['id']), lp, v.get('compare_at_price'))
        img = pick_packshot(p)
        if not img:
            continue  # no clean product-only photo — leave it out
        tags = ' '.join(sorted({ptype.lower(), *[t.lower() for t in (p.get('tags') or [])[:8] if isinstance(t, str) and len(t) < 24]}))
        if add(brand, site, name, cat, size[:40], price, was, img, 'contain', str(p['id']), tags, serv=serv):
            brand_count[brand] = brand_count.get(brand, 0) + 1

# ---------------- Open Food Facts (mainstream drinks & snacks) ----------------
OFF = [
    # query-file, brand label, brand match regex, site, category, base price range (single), cap
    ('monster_energy', 'Monster Energy', r'monster', 'monsterenergy.com', 'Energy drinks', 14),
    ('red_bull', 'Red Bull', r'red ?bull', 'redbull.com', 'Energy drinks', 8),
    ('bang_energy', 'Bang', r'\bbang\b', 'bangenergy.com', 'Energy drinks', 6),
    ('reign_energy', 'Reign', r'reign', 'reignbodyfuel.com', 'Energy drinks', 6),
    ('rockstar_energy', 'Rockstar', r'rockstar', 'rockstarenergy.com', 'Energy drinks', 6),
    ('celsius_energy', 'Celsius', r'celsius', 'celsius.com', 'Energy drinks', 8),
    ('c4_energy', 'Cellucor', r'c4|cellucor|nutrabolt', 'cellucor.com', 'Energy drinks', 4),
    ('ghost_energy', 'Ghost', r'ghost', 'ghostlifestyle.com', 'Energy drinks', 4),
    ('3d_energy', '3D Energy', r'3d', '3denergydrinks.com', 'Energy drinks', 4),
    ('zoa_energy', 'ZOA', r'zoa', 'zoaenergy.com', 'Energy drinks', 4),
    ('nocco', 'NOCCO', r'nocco', 'nocco.com', 'Energy drinks', 4),
    ('alani_nu_energy', 'Alani Nu', r'alani', 'alaninu.com', 'Energy drinks', 6),
    ('g_fuel', 'G Fuel', r'g ?fuel|gamma', 'gfuel.com', 'Energy drinks', 5),
    ('prime_hydration', 'Prime', r'prime', 'drinkprime.com', 'Hydration', 6),
    ('gatorade', 'Gatorade', r'gatorade', 'gatorade.com', 'Hydration', 8),
    ('bodyarmor', 'BodyArmor', r'body ?armor', 'drinkbodyarmor.com', 'Hydration', 6),
    ('liquid_iv', 'Liquid I.V.', r'liquid', 'liquid-iv.com', 'Hydration', 6),
    ('lmnt', 'LMNT', r'lmnt', 'drinklmnt.com', 'Hydration', 4),
    ('premier_protein', 'Premier Protein', r'premier', 'premierprotein.com', 'Protein shakes', 8),
    ('fairlife_core_power', 'Fairlife', r'fairlife|core power', 'fairlife.com', 'Protein shakes', 6),
    ('muscle_milk', 'Muscle Milk', r'muscle ?milk', 'musclemilk.com', 'Protein shakes', 6),
    ('barebells', 'Barebells', r'barebells', 'barebells.com', 'Bars', 8),
    ('one_protein_bar', 'ONE', r'\bone\b', 'onebrands.com', 'Bars', 6),
    ('rxbar', 'RXBAR', r'rx ?bar', 'rxbar.com', 'Bars', 6),
    ('quest_protein_chips', 'Quest', r'quest', 'questnutrition.com', 'Snacks', 6),
    ('pure_protein', 'Pure Protein', r'pure protein', 'pureprotein.com', 'Bars', 5),
    ('built_bar', 'Built', r'built', 'built.com', 'Bars', 5),
    ('optimum_nutrition', 'Optimum Nutrition', r'optimum', 'optimumnutrition.com', None, 6),
    ('isopure', 'Isopure', r'isopure', 'theisopurecompany.com', 'Protein', 5),
    ('muscletech', 'MuscleTech', r'muscletech', 'muscletech.com', None, 6),
]
PRICE = {  # (single unit, multipack) placeholder shelf prices
    'Energy drinks': (2.99, 27.99), 'Hydration': (2.49, 24.99), 'Protein shakes': (3.49, 29.99),
    'Bars': (2.79, 26.99), 'Snacks': (2.99, 24.99), 'Protein': (39.99, 39.99),
    'Mass gainers': (59.99, 59.99), 'Vitamins & health': (24.99, 24.99), 'Aminos & recovery': (29.99, 29.99),
    'Creatine': (27.99, 27.99),
}
for fname, brand, rx, site, cat0, cap in []:  # Open Food Facts disabled — its photos are shopper-taken, not packshots
    fp = os.path.join(CAT, 'off', fname + '.json')
    if not os.path.exists(fp):
        continue
    prods = json.load(open(fp, encoding='utf-8')).get('products', [])
    prods.sort(key=lambda p: (('en:united-states' not in (p.get('countries_tags') or [])), -(p.get('unique_scans_n') or 0)))
    c = 0
    for p in prods:
        if c >= cap:
            break
        nm, br, img = p.get('product_name') or '', p.get('brands') or '', p.get('image_front_url')
        if not img or not nm or not re.search(rx, br + ' ' + nm, re.I):
            continue
        if re.search(r'[^\x00-\x7f]', nm) and not re.search(r'[éèü]', nm):
            continue
        if re.search(r'sekonda|chest|watch|t-shirt|mug\b|keychain|poster|cup\b', nm, re.I):
            continue
        if re.search(r'bebida|boisson|getr|energetica|energ.tica|sans sucre|zéro|sucre|sabor|gout|goût|mûre|givr', nm, re.I):
            continue
        name = clean_name(nm, brand)
        name = re.sub(r'^(energy drink|energy|bar|piece)\s+[-:]?\s*', '', name, flags=re.I) or nm
        if name[:1].islower():
            name = tcase(name)
        # skip names that say nothing beyond brand/generic words ("Energy Drink", "Protein bar", "350ml")
        GENERIC = {'energy', 'drink', 'drinks', 'protein', 'bar', 'bars', 'powder', 'shake', 'supplement', 'the', 'original',
                   'caffeine', 'drinkmix', 'mix', 'sports', 'ml', 'oz', 'fl', 'cl', 'can', 'protien', 'energydrink', 'classic', 'iv'}
        bw = set(re.findall(r'[a-z0-9]+', brand.lower()))
        words = [w for w in re.findall(r'[a-z]+', name.lower()) if w not in GENERIC and w not in bw]
        if not words:
            continue
        c2 = classify(nm)
        if c2 in ('Bars', 'Mass gainers') or (c2 == 'Vitamins & health' and cat0 is None) or (c2 == 'Protein' and re.search(r'powder', nm, re.I)):
            cat = c2
        else:
            cat = cat0 or c2 or 'Protein'
        q = (p.get('quantity') or '').strip()
        if re.fullmatch(r'[\d.\s]+', q) or re.search(r'\d{4,}', q):
            q = ''
        multi = bool(re.search(r'\b\d{1,2}\s*[x×]\s*\d|\d+\s*-?\s*(pack|pk|ct|count)\b|\bpack\b|\bcase\b', q + ' ' + nm, re.I))
        base = PRICE.get(cat, (29.99, 29.99))[1 if multi else 0]
        base = round(base * (0.85 + h(p['code'], 30) / 100), 2)
        price, was = deal_prices(p['code'], base, None)
        if add(brand, site, name[:58], cat, q[:40] or ('Multipack' if multi else 'Single'), price, was, img, 'contain', p['code'],
               (br + ' ' + cat).lower()):
            c += 1

# ---------------- official brand-site packshots (collected from each brand's product pages) ----------------
OFFICIAL = [
    # file, brand, site, default category, strip-prefix
    ('monster.txt', 'Monster Energy', 'monsterenergy.com', 'Energy drinks', ''),
    ('redbull.txt', 'Red Bull', 'redbull.com', 'Energy drinks', 'Red Bull '),
    ('celsius.txt', 'Celsius', 'celsius.com', 'Energy drinks', 'Celsius '),
    ('bang.txt', 'Bang', 'bangenergy.com', 'Energy drinks', 'Bang '),
    ('reign.txt', 'Reign', 'reignbodyfuel.com', 'Energy drinks', 'Reign '),
    ('premier.raw', 'Premier Protein', 'premierprotein.com', 'Protein shakes', ''),
    ('gatorade.txt', 'Gatorade', 'gatorade.com', 'Hydration', ''),
    ('bodyarmor.txt', 'BodyArmor', 'drinkbodyarmor.com', 'Hydration', ''),
]
for fname, brand, site, cat0, strip in OFFICIAL:
    fp = os.path.join(S, 'official', fname)
    if not os.path.exists(fp):
        continue
    for line in open(fp, encoding='utf-8'):
        if '|' not in line:
            continue
        img, nm = line.strip().split('|', 1)
        name = nm[len(strip):] if strip and nm.startswith(strip) else nm
        name = re.sub(r'^(MONSTER ENERGY|MONSTER ULTRA)\s+', lambda m: 'Ultra ' if 'ULTRA' in m.group(1) else '', name)
        name = re.sub(r'^(JAVA|JUICE|REHAB) MONSTER\s+', lambda m: m.group(1).title() + ' ', name)
        name = re.sub(r'^KILLER BREW\s+', 'Killer Brew ', name).replace('Ultra Zero Ultra', 'Zero Ultra')
        name = name.replace('“', '"').replace('”', '"')
        cat = cat0
        if re.search(r'powder', name, re.I):
            cat = 'Protein'
        elif re.search(r'cereal', name, re.I):
            cat = 'Snacks'
        elif re.search(r'soda', name, re.I):
            cat = 'Protein shakes'
        key = brand + name
        base = PRICE.get(cat, (29.99, 29.99))[0]
        base = round(base * (0.9 + h(key, 25) / 100), 2)
        price, was = deal_prices(key, base, None)
        size = {'Energy drinks': '16 fl oz can', 'Hydration': 'Single', 'Protein shakes': '11 fl oz', 'Protein': '17 servings', 'Snacks': 'Box'}.get(cat, '')
        if brand in ('Red Bull', 'Celsius'):
            size = '12 fl oz can' if brand == 'Celsius' else '8.4 fl oz can'
        add(brand, site, name, cat, size, price, was, img, 'contain', key, (brand + ' ' + cat).lower())

js = 'const GEN=' + json.dumps(GEN, ensure_ascii=False, separators=(',', ':')) + ';'
open(os.path.join(S, 'gen_catalog.js'), 'w', encoding='utf-8').write(js)
from collections import Counter
print(len(GEN), 'products')
print(Counter(g['cat'] for g in GEN).most_common())
print(Counter(g['brand'] for g in GEN).most_common())
