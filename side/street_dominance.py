"""Street dominance: how much of a city's storefront activity sits on a few named streets.

A side question, not part of the regionalization pipeline. Reads the pinned
Overture extracts written by pipeline/fetch_overture.py (places, segments,
division areas, release 2026-08-19.0) and writes one JSON of results.

Each place is put on the street named in its own address (Overture
addresses[0].freeform), not the nearest line, so a corner cafe at 2001 Mission
counts for Mission. Street names on both sides are normalized the same way and
directional prefixes and suffixes are dropped, so N Western Ave and S Western
Ave are one street, as are Queen St W and Queen St E. A place counts only if
its address street also names a road segment inside city limits.

The null is street length: if storefronts were spread evenly along every named
street, each street's share of storefronts would equal its share of named road
length. Dominance is measured against that.

    python3 side/street_dominance.py            # writes side/out/street-dominance.json
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from pyproj import Transformer
from shapely import from_wkb, intersection, prepare, contains_xy
from shapely.geometry import box
from shapely.ops import transform
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '2026-08-19.0'
OUT = ROOT / 'side' / 'out'

CITIES = {  # boundary polygon in Overture divisions, local metric CRS
    'sf': ('San Francisco', 'county', 'EPSG:26910'),
    'vancouver': ('Vancouver', 'locality', 'EPSG:26910'),
    'chicago': ('Chicago', 'locality', 'EPSG:26916'),
    'toronto': ('Toronto', 'county', 'EPSG:26917'),
}
BBOX = {
    'sf': [-122.55, 37.68, -122.33, 37.84], 'toronto': [-79.64, 43.58, -79.11, 43.86],
    'vancouver': [-123.23, 49.19, -123.02, 49.32], 'chicago': [-87.95, 41.64, -87.52, 42.03],
}
ROAD_CLASSES = {'trunk', 'primary', 'secondary', 'tertiary', 'residential',
                'unclassified', 'living_street', 'pedestrian'}
ARTERIAL = {'trunk', 'primary', 'secondary', 'tertiary'}

# Storefronts: the walk-in businesses that make a "main street". Overture basic_category.
STOREFRONT = re.compile(r'restaurant|eatery|bar$|^bar_|pub|coffee|cafe|bakery|dessert|'
                        r'store|shop|beauty|salon|barber|pharmacy|grocery|market|deli|'
                        r'brewery|winery|food_and_beverage|nightlife|bookstore')

ABBREV = {'street': 'st', 'avenue': 'ave', 'av': 'ave', 'boulevard': 'blvd', 'road': 'rd',
          'drive': 'dr', 'highway': 'hwy', 'place': 'pl', 'court': 'ct', 'crt': 'ct',
          'lane': 'ln', 'terrace': 'ter', 'parkway': 'pkwy', 'square': 'sq',
          'crescent': 'cres', 'circle': 'cir', 'gardens': 'gdns', 'trail': 'trl',
          'expressway': 'expy', 'saint': 'st', 'mount': 'mt'}
DIRS = {'n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw', 'north', 'south', 'east', 'west',
        'northeast', 'northwest', 'southeast', 'southwest'}
TYPES = {'st', 'ave', 'blvd', 'rd', 'dr', 'hwy', 'pl', 'ct', 'ln', 'ter', 'pkwy', 'sq',
         'cres', 'cir', 'gdns', 'trl', 'expy', 'way', 'row', 'mall', 'walk'}
UNIT = re.compile(r'\s(suite|ste|unit|apt|fl|floor|rm|room|bldg|#).*$', re.I)


def norm_street(name):
    if not name:
        return None
    words = re.sub(r"[^a-z0-9 ]", ' ', name.lower()).split()
    words = [ABBREV.get(w, w) for w in words]
    # Drop a directional only when a real name is left: W North Ave -> north ave, not ave.
    def named(ws):
        return any(w not in TYPES for w in ws)
    while len(words) > 1 and words[0] in DIRS and named(words[1:]):
        words = words[1:]
    while len(words) > 1 and words[-1] in DIRS and named(words[:-1]):
        words = words[:-1]
    return ' '.join(words) or None


def address_street(freeform):
    """'2128 Mission St Suite 4, San Francisco' -> 'mission st'. None when no house number."""
    if not freeform:
        return None
    first = UNIT.sub('', freeform.split(',')[0].strip())
    m = re.match(r'^[\w/-]*\d[\w/-]*\s+(.+)$', first)
    return norm_street(m.group(1)) if m else None


def boundary(city):
    name, subtype, crs = CITIES[city]
    t = pq.read_table(ROOT / f'data/{city}/overture-division_area-{RELEASE}.parquet',
                      columns=['subtype', 'class', 'names', 'geometry']).to_pylist()
    (geom,) = [from_wkb(r['geometry']) for r in t if r['subtype'] == subtype
               and r['class'] == 'land' and (r['names'] or {}).get('primary') == name]
    geom = intersection(geom, box(*BBOX[city]))
    proj = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
    return transform(proj.transform, geom), proj


def streets(city, area, proj):
    """Named road length per normalized name inside city limits, and the lines for drawing."""
    t = pq.read_table(ROOT / f'data/{city}/overture-segment-{RELEASE}.parquet',
                      columns=['subtype', 'class', 'names', 'geometry']).to_pylist()
    length, arterial, lines = Counter(), Counter(), defaultdict(list)
    prepare(area)
    for r in t:
        if r['subtype'] != 'road' or r['class'] not in ROAD_CLASSES:
            continue
        name = norm_street((r['names'] or {}).get('primary'))
        if not name:
            continue
        g = transform(proj.transform, from_wkb(r['geometry']))
        if not area.intersects(g):
            continue
        g = intersection(g, area)
        length[name] += g.length
        if r['class'] in ARTERIAL:
            arterial[name] += g.length
        lines[name].append(g)
    return length, arterial, lines


def places(city, area, proj):
    t = pq.read_table(ROOT / f'data/{city}/overture-place-{RELEASE}.parquet',
                      columns=['confidence', 'operating_status', 'basic_category',
                               'addresses', 'geometry']).to_pylist()
    rows = []
    for r in t:
        if (r['confidence'] or 0) < 0.5 or r['operating_status'] == 'permanently_closed':
            continue
        p = from_wkb(r['geometry'])
        x, y = proj.transform(p.x, p.y)
        addr = (r['addresses'] or [{}])[0].get('freeform')
        rows.append((x, y, address_street(addr), r['basic_category'] or ''))
    xy = np.array([(x, y) for x, y, _, _ in rows])
    inside = contains_xy(area, xy[:, 0], xy[:, 1])
    return [r for r, keep in zip(rows, inside) if keep]


def shares(counts, k):
    total = sum(counts.values())
    return sum(v for _, v in counts.most_common(k)) / total if total else float('nan')


def summarize(counts, length):
    """Top-k share of places, the same streets' share of length, and the
    street-length concentration curve's Gini (0 = places proportional to length)."""
    total_len = sum(length.values())
    out = {'places': sum(counts.values()), 'streets_with_places': len(counts)}
    for k in (1, 3, 5, 10):
        top = [n for n, _ in counts.most_common(k)]
        out[f'top{k}_share'] = shares(counts, k)
        out[f'top{k}_length_share'] = sum(length[n] for n in top) / total_len
        out[f'top{k}_streets'] = top
    # Streets needed to hold half the places.
    c = np.cumsum(sorted(counts.values(), reverse=True)) / out['places']
    out['streets_for_half'] = int(np.searchsorted(c, 0.5) + 1)
    # Concentration curve against length: rank streets by places per metre.
    names = [n for n in length if length[n] > 0]
    p = np.array([counts.get(n, 0) for n in names], float)
    L = np.array([length[n] for n in names], float)
    order = np.argsort(-(p / L))
    x = np.concatenate([[0], np.cumsum(L[order]) / L.sum()])
    y = np.concatenate([[0], np.cumsum(p[order]) / p.sum()])
    out['gini_vs_length'] = float(2 * np.trapezoid(y, x) - 1)
    out['length_share_for_half'] = float(np.interp(0.5, y, x))
    return out, (x, y)


def spans(lines):
    """Longest side of each street's bounding box, in metres: how far it reaches across the city."""
    out = {}
    for n, gs in lines.items():
        b = np.array([g.bounds for g in gs if not g.is_empty])
        if len(b):
            out[n] = float(max(b[:, 2].max() - b[:, 0].min(), b[:, 3].max() - b[:, 1].min()))
    return out


def windows(area, rows, lines, side=4000, step=2000, k=3, min_places=300):
    """Equal-size square windows, so a big city is not credited with more streets
    just for being big. Windows at least 90% inside the city with enough
    storefronts; in each, the top-k streets' share of the window's storefronts and
    of its named road length."""
    xy = np.array([(r[0], r[1]) for r in rows])
    names = [r[2] for r in rows]
    x0, y0, x1, y1 = area.bounds
    out = []
    for wx in np.arange(x0, x1 - side + 1, step):
        for wy in np.arange(y0, y1 - side + 1, step):
            w = box(wx, wy, wx + side, wy + side)
            if area.intersection(w).area < 0.9 * w.area:
                continue
            m = (xy[:, 0] >= wx) & (xy[:, 0] < wx + side) & (xy[:, 1] >= wy) & (xy[:, 1] < wy + side)
            counts = Counter(n for n, keep in zip(names, m) if keep)
            if sum(counts.values()) < min_places:
                continue
            top = [n for n, _ in counts.most_common(k)]
            length = {n: sum(intersection(g, w).length for g in lines[n]) for n in top}
            total_len = sum(intersection(g, w).length for gs in lines.values() for g in gs
                            if g.intersects(w))
            out.append({'x': float(wx), 'y': float(wy), 'places': sum(counts.values()),
                        'top_share': shares(counts, k),
                        'top_length_share': sum(length.values()) / total_len, 'top': top})
    return out


def run(city):
    area, proj = boundary(city)
    length, arterial, lines = streets(city, area, proj)
    rows = places(city, area, proj)
    known = set(length)
    result = {'area_km2': area.area / 1e6, 'named_road_km': sum(length.values()) / 1e3,
              'arterial_km': sum(arterial.values()) / 1e3}
    curves = {}
    for label, keep in (('all', lambda cat: True), ('storefront', lambda cat: bool(STOREFRONT.search(cat)))):
        sel = [r for r in rows if keep(r[3])]
        matched = [r for r in sel if r[2] in known]
        counts = Counter(r[2] for r in matched)
        summary, curve = summarize(counts, length)
        summary['candidates'] = len(sel)
        summary['matched_rate'] = len(matched) / len(sel)
        summary['on_arterial_share'] = sum(v for n, v in counts.items() if arterial[n] > 0) / len(matched)
        # Long streets: reaching at least half way across the city (half the side of
        # a square of the city's area), and their share of storefronts and of length.
        reach = spans(lines)
        half = 0.5 * np.sqrt(area.area)
        long_ = {n for n, v in reach.items() if v >= half}
        summary['long_streets'] = len(long_)
        summary['long_street_share'] = sum(counts[n] for n in long_) / len(matched)
        summary['long_street_length_share'] = sum(length[n] for n in long_) / sum(length.values())
        summary['top10_span_km'] = [reach.get(n, 0) / 1e3 for n in summary['top10_streets']]
        result[label] = summary
        curves[label] = curve
        if label == 'storefront':
            result['windows'] = windows(area, matched, lines)
    return result, curves, (area, length, arterial, lines, rows)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for city in CITIES:
        results[city], _, _ = run(city)
        s = results[city]['storefront']
        print(city, round(results[city]['area_km2']), 'km2', s['places'], 'storefronts',
              f"matched {s['matched_rate']:.2f}", f"top5 {s['top5_share']:.3f} vs len {s['top5_length_share']:.3f}",
              f"half on {s['streets_for_half']} streets / {s['length_share_for_half']:.3f} of length",
              f"gini {s['gini_vs_length']:.2f}", s['top10_streets'])
        print('   long streets', s['long_streets'], f"hold {s['long_street_share']:.3f} of storefronts, {s['long_street_length_share']:.3f} of length;",
              'top10 spans km', np.round(s['top10_span_km'], 1), 'all-places top5', round(results[city]['all']['top5_share'], 3))
        w = results[city]['windows']
        print('   windows', len(w), 'median top3 share', round(float(np.median([v['top_share'] for v in w])), 3),
              'iqr', np.round(np.percentile([v['top_share'] for v in w], [25, 75]), 3),
              'median len share', round(float(np.median([v['top_length_share'] for v in w])), 3))
    (OUT / 'street-dominance.json').write_text(json.dumps(results, indent=1))
