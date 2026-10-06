"""Build the typed toponym lexicon for one city and write it under data/lexicon/.

    python3 pipeline/build_lexicon.py --city sf
    python3 pipeline/build_lexicon.py --all

Writes data/lexicon/<city>-<release>.jsonl (one phrase per line, all fields) and
data/lexicon/<city>-<release>.summary.json (counts, parameters, top terms per
class), plus the per-cell units of every non-generic, non-brand phrase in
data/lexicon/<city>-<release>.cells.jsonl for the feature step.
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import boundaries
import given_names
import lexicon
from cells import RESOLUTION, boundary_area, load_places, study_cells
from fetch_overture import CITIES, RELEASE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'lexicon'
FEATURE_CLASSES = ('area', 'division', 'mixed', 'landmark', 'point', 'street')


def build_city(city, resolution=RESOLUTION):
    t0 = time.time()
    data = ROOT / 'data' / city
    places = load_places(data / f'overture-place-{RELEASE}.parquet', resolution)
    gdf, provenance = boundaries.load(city)
    cells = study_cells(boundary_area(gdf), resolution)
    streets = lexicon.street_names(data / f'overture-segment-{RELEASE}.parquet')
    divisions = lexicon.division_names(data / f'overture-division_area-{RELEASE}.parquet', gdf['name'])
    persons = given_names.load()
    rows, cell_units = lexicon.build(places, cells, streets, divisions, persons)
    OUT.mkdir(parents=True, exist_ok=True)
    # RELEASE ends in '.0'; with_suffix would eat it. Res 9 is the default and
    # keeps the plain name; other resolutions are a sensitivity check and get a tag.
    stem = str(OUT / f'{city}-{RELEASE}') + ('' if resolution == RESOLUTION else f'-r{resolution}')
    lexicon.write(rows, Path(stem + '.jsonl'))
    with open(stem + '.cells.jsonl', 'w') as f:
        for r in rows:
            if r['class'] in FEATURE_CLASSES:
                f.write(json.dumps({'phrase': r['phrase'], 'class': r['class'],
                                    'cells': cell_units[r['phrase']]}) + '\n')
    counts = Counter(r['class'] for r in rows)
    summary = {
        'city': city, 'release': RELEASE, 'resolution': resolution,
        'places': len(places), 'cells': len(cells),
        'cells_with_places': len({p.cell for p in places} & set(cells)),
        'ground_truth': provenance, 'street_names': len(streets), 'division_names': len(divisions),
        'given_names': len(persons),
        'phrases': len(rows), 'classes': dict(counts),
        'parameters': {'min_support': lexicon.MIN_SUPPORT, 'generic_locality': lexicon.GENERIC_LOCALITY,
                       'generic_sd_km': lexicon.GENERIC_SD_KM, 'brand_share': lexicon.BRAND_SHARE,
                       'chain_ratio': lexicon.CHAIN_RATIO, 'majority': lexicon.MAJORITY},
        'top': {cls: [r['phrase'] for r in rows if r['class'] == cls][:40] for cls in counts},
        'seconds': round(time.time() - t0, 1),
    }
    Path(stem + '.summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in ('city', 'places', 'cells', 'phrases', 'classes', 'seconds')}))
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city', choices=CITIES)
    p.add_argument('--all', action='store_true')
    p.add_argument('--resolution', type=int, default=RESOLUTION)
    a = p.parse_args()
    for city in (CITIES if a.all else [a.city]):
        build_city(city, a.resolution)
