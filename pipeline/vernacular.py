"""Area terms the lexicon finds that no official or Overture polygon names.

Cadmus's design notes say a small vernacular gazetteer is unavoidable. This is
the list to curate it from: per city, the `area` and `point` phrases with the
most support whose tokens appear in no ground-truth or division name, with the
cell where they peak so a reviewer can look at the map. It is a candidate list,
not a gazetteer; institutions, malls and large employers will be in it.

    python3 pipeline/vernacular.py --all   # writes notes/vernacular/<city>.md
"""
import argparse
import json
import math
from pathlib import Path

import h3

import boundaries
from fetch_overture import CITIES, RELEASE
from lexicon import name_parts

ROOT = Path(__file__).resolve().parents[1]


def run(city, top=60):
    stem = str(ROOT / 'data' / 'lexicon' / f'{city}-{RELEASE}')
    rows = [json.loads(l) for l in open(stem + '.jsonl')]
    units = {json.loads(l)['phrase']: json.loads(l)['cells'] for l in open(stem + '.cells.jsonl')}
    gdf, _ = boundaries.load(city)
    official_tokens = set()
    for n in gdf['name']:
        for part in name_parts(n):
            official_tokens |= set(part.split())
    cand = [r for r in rows if r['class'] in ('area',) and not (set(r['phrase'].split()) & official_tokens)]
    # The lexicon's own ranking (locality x log1p(support)), not raw support: by
    # support alone, downtown business words with locality around 2 (law, hotel,
    # apartments) lead the SF list; by score the place terms do.
    cand.sort(key=lambda r: -r['locality'] * math.log1p(r['support']))
    out = ROOT / 'notes' / 'vernacular' / f'{city}-{RELEASE}.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'# {city}: area terms with no official or Overture polygon name — {RELEASE}', '',
             'Candidates for a vernacular gazetteer, by locality x log1p(support). `peak` is the H3-9 cell with the most units '
             '(lat, lng). Institutions and malls are expected in this list; mark them when curating.', '',
             '| phrase | support | cells | locality | sd km | peak | examples |', '|---|---|---|---|---|---|---|']
    for r in cand[:top]:
        peak = max(units[r['phrase']].items(), key=lambda kv: kv[1])[0]
        lat, lng = h3.cell_to_latlng(peak)
        ex = '; '.join(r['examples'][:2]).replace('|', '/')
        lines.append(f"| {r['phrase']} | {r['support']} | {r['cells']} | {r['locality']:.1f} | {r['sd_km']:.1f} | {lat:.4f}, {lng:.4f} | {ex} |")
    out.write_text('\n'.join(lines) + '\n')
    print(json.dumps({'city': city, 'candidates': len(cand), 'written': top}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city', choices=CITIES)
    p.add_argument('--all', action='store_true')
    a = p.parse_args()
    for city in (CITIES if a.all else [a.city]):
        run(city)
