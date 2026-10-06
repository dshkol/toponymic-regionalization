"""Lexical name candidates for one polygon, in a form cadmus can consume.

Cadmus's contained-evidence packet carries raw repeated words as diagnostics
("not eligible name proposals") because repetition alone ranks 'San Francisco'
above local names. This gives the alternative its ranking trial asked for:
lexicon hits only, each with its class, support inside the polygon under the
cap, the inside-vs-rest log ratio and the score. No boundary overlap, no model.

    python3 pipeline/name_polygon.py --city sf geometry.json
    python3 pipeline/name_polygon.py --city sf geometry.json --vocabulary all

Output: {"area_km2", "places_inside", "candidates": [{phrase, class, units,
log_ratio, score}], "vocabulary", "source"}. `naming` (default) is the area
channel; `all` adds streets, landmarks and points. Streets rank well inside
corridors, so a corridor caller may want `all`.
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from pyproj import Geod
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from cells import load_places
from fetch_overture import CITIES, RELEASE
from name_recovery import AREA, NOT_GENERIC
from names import MIN_SUPPORT, Support, log_ratio, phrases

ROOT = Path(__file__).resolve().parents[1]
GEOD = Geod(ellps='WGS84')


class Namer:
    def __init__(self, city, release=RELEASE):
        stem = str(ROOT / 'data' / 'lexicon' / f'{city}-{release}')
        self.lexicon_file = Path(stem + '.jsonl').name
        self.lexicon = {r['phrase']: r for r in (json.loads(l) for l in open(stem + '.jsonl'))}
        self.places = load_places(ROOT / 'data' / city / f'overture-place-{release}.parquet')
        self.tree = STRtree([Point(p.record.x, p.record.y) for p in self.places])
        self.n_sites = len({f'{p.record.x:.5f},{p.record.y:.5f}' for p in self.places})
        self.manifest = json.loads((ROOT / 'data' / city / f'overture-place-{release}.manifest.json').read_text())

    def name(self, geometry, vocabulary='naming', top=8):
        region = shape(geometry.get('geometry', geometry))
        classes = AREA if vocabulary == 'naming' else NOT_GENERIC
        inside = [self.places[i] for i in self.tree.query(region, predicate='contains')]
        support = defaultdict(Support)
        sites = set()
        for p in inside:
            sites.add(f'{p.record.x:.5f},{p.record.y:.5f}')
            for ph in phrases(p.record.name):
                r = self.lexicon.get(ph)
                if r and r['class'] in classes:
                    support[ph].add(p.record)
        ranked = []
        for ph, s in support.items():
            if s.units < MIN_SUPPORT:
                continue
            m = max(self.lexicon[ph]['support'] - s.units, 0)
            ratio = log_ratio(s.units, len(sites), m, self.n_sites - len(sites))
            if ratio > 0:
                ranked.append({'phrase': ph, 'class': self.lexicon[ph]['class'], 'units': s.units,
                               'log_ratio': round(ratio, 3), 'score': round(ratio * math.log1p(s.units), 3),
                               'examples': s.examples[:3]})
        ranked.sort(key=lambda r: (-r['score'], r['phrase']))
        # Drop a phrase contained in a higher-ranked one ('noe' under 'noe valley'), as cadmus does.
        chosen = []
        for r in ranked:
            if any(f" {r['phrase']} " in f" {c['phrase']} " or f" {c['phrase']} " in f" {r['phrase']} " for c in chosen):
                continue
            chosen.append(r)
            if len(chosen) == top:
                break
        area = abs(GEOD.geometry_area_perimeter(region)[0]) / 1e6
        return {'area_km2': round(area, 4), 'places_inside': len(inside), 'sites_inside': len(sites),
                'vocabulary': vocabulary, 'candidates': chosen,
                'source': {'lexicon': self.lexicon_file, 'places': self.manifest},
                'note': 'Lexical candidates only: no area extent, no boundary overlap, no model.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('geometry', type=Path, nargs='+')
    p.add_argument('--city', choices=CITIES, required=True)
    p.add_argument('--vocabulary', choices=('naming', 'all'), default='naming')
    a = p.parse_args()
    namer = Namer(a.city)
    for g in a.geometry:
        out = namer.name(json.loads(g.read_text()), a.vocabulary)
        print(json.dumps({'geometry': g.name, 'area_km2': out['area_km2'], 'places': out['places_inside'],
                          'top': [(c['phrase'], c['class'], c['units'], c['score']) for c in out['candidates']]}))
