"""Does the lexicon name the official polygons? A closure test for both projects.

For each ground-truth polygon, rank the city's lexicon phrases by cadmus's rule
on the places inside it (smoothed inside-vs-rest log rate ratio times
log1p(support), support capped, floor of 3), and ask whether the top phrase is
part of the polygon's official name. This is cadmus's naming task run on
polygons we know the answer for, with no boundary overlap and no model: a
lexical-only ceiling, and a direct check of the class column.

Two term sets are scored: every non-generic, non-brand phrase, and the area
channel only (area, division, mixed). If the area channel scores as well as the
full set, keeping streets and landmarks out of the regionalization features
loses no naming power.

    python3 pipeline/name_recovery.py --city sf
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from shapely.strtree import STRtree
from shapely.geometry import Point

import boundaries
from cells import load_places
from fetch_overture import CITIES, RELEASE
from lexicon import name_parts
from names import MIN_SUPPORT, Support, log_ratio, phrases

ROOT = Path(__file__).resolve().parents[1]
AREA = ('area', 'division', 'mixed')
NOT_GENERIC = ('area', 'division', 'mixed', 'landmark', 'institution', 'street', 'point')


def rank_inside(places_in, places_all_sites, vocabulary, citywide):
    support = defaultdict(Support)
    sites = set()
    for p in places_in:
        sites.add(f'{p.record.x:.5f},{p.record.y:.5f}')
        for ph in phrases(p.record.name):
            if ph in vocabulary:
                support[ph].add(p.record)
    out = []
    for ph, s in support.items():
        if s.units < MIN_SUPPORT:
            continue
        m = citywide[ph] - s.units
        ratio = log_ratio(s.units, len(sites), max(m, 0), places_all_sites - len(sites))
        if ratio > 0:
            out.append((ratio * math.log1p(s.units), ph, s.units))
    out.sort(reverse=True)
    return out


def run(city, tag=''):
    # tag='-r8' reads the resolution-8 lexicon from build_lexicon.py --resolution 8
    lex = [json.loads(l) for l in open(ROOT / 'data' / 'lexicon' / f'{city}-{RELEASE}{tag}.jsonl')]
    cls = {r['phrase']: r['class'] for r in lex}
    citywide = {r['phrase']: r['support'] for r in lex}
    gdf, _ = boundaries.load(city)
    places = load_places(ROOT / 'data' / city / f'overture-place-{RELEASE}.parquet')
    tree = STRtree([Point(p.record.x, p.record.y) for p in places])
    n_sites = len({f'{p.record.x:.5f},{p.record.y:.5f}' for p in places})
    results = []
    for _, row in gdf.iterrows():
        inside = [places[i] for i in tree.query(row.geometry, predicate='contains')]
        targets = name_parts(row['name'])
        # The joined form counts as exact ('pleasantview' for Pleasant View), as in division_names.
        targets |= {t.replace(' ', '') for t in targets if ' ' in t}
        rec = {'name': row['name'], 'places': len(inside)}
        for label, classes in (('all', NOT_GENERIC), ('area', AREA)):
            vocab = {p for p, c in cls.items() if c in classes}
            ranked = rank_inside(inside, n_sites, vocab, citywide)
            top = [ph for _, ph, _ in ranked[:3]]
            name_tokens = set(' '.join(targets).split())
            rec[label] = {'top3': top,
                          # exact: the phrase is a part of the official name ('noe valley')
                          'hit1': bool(top) and top[0] in targets,
                          'hit3': any(t in targets for t in top),
                          # partial: every token of the phrase is in the name ('richmond' for Outer Richmond)
                          'partial1': bool(top) and set(top[0].split()) <= name_tokens,
                          'class': cls.get(top[0]) if top else None}
        results.append(rec)
    n = len(results)

    def rate(label, key):
        return round(sum(r[label][key] for r in results) / n, 3)
    summary = {'city': city, 'polygons': n,
               'all': {k: rate('all', k) for k in ('hit1', 'partial1', 'hit3')},
               'area': {k: rate('area', k) for k in ('hit1', 'partial1', 'hit3')},
               'no_top_term': sum(not r['area']['top3'] for r in results)}
    out = ROOT / 'notes' / 'name-recovery' / f'{city}-{RELEASE}{tag}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'summary': summary, 'polygons': results}, indent=1, ensure_ascii=False))
    print(json.dumps(summary))
    return summary, results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city', choices=CITIES)
    p.add_argument('--all', action='store_true')
    p.add_argument('--lexicon-tag', default='', help="e.g. -r8 for the resolution-8 lexicon")
    a = p.parse_args()
    for city in (CITIES if a.all else [a.city]):
        run(city, a.lexicon_tag)
