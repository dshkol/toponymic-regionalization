"""Export one city's cells, partitions and scores for the static viewer.

    python pipeline/export_viewer.py --city sf

Writes viewer/data/<city>.json: H3 cell ids, the ground-truth label per cell, token counts,
SCHC Ward labels for names (ring 1 and unsmoothed) and coordinates-only at each k, lifted
tokens per region, the ARI table from the dated note's CSV, and the simplified ground-truth
polygons. Same pipeline as run_city.py, so the labels are the ones the notes score.
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from shapely.geometry import mapping
from sklearn.preprocessing import StandardScaler

import toponymic as tp
from fetch_places import verify
from run_city import CITIES, KS, ROOT


def name_postings(raw_counts: dict, cl: list[str], min_df: int = 3) -> dict:
    """Per token found in at least min_df cells: a flat [cell index, count, cell index, count, ...]
    list, so the viewer can draw where any name holds (its field) without a server."""
    from collections import defaultdict
    post = defaultdict(list)
    for i, c in enumerate(cl):
        for t, k in sorted(raw_counts.get(c, {}).items()):
            post[t].extend((i, int(k)))
    return {t: v for t, v in post.items() if len(v) >= 2 * min_df}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--city', choices=CITIES, required=True)
    ap.add_argument('--res', type=int, default=9)
    args = ap.parse_args()
    city = CITIES[args.city]
    name_col = city['name']

    extract = ROOT / city['extract']
    manifest = verify(extract)
    gt = gpd.read_file(ROOT / city['truth'])
    places = tp.load_places(extract)
    ks = KS + ((len(gt),) if len(gt) not in KS else ())

    cells = tp.city_cells(gt, args.res)
    cl = list(cells['cell'])
    w = tp.bridge_components(tp.h3_weights(cells['cell']), cells)
    truth_names = tp.label_cells_by_centroid(cells, gt, name_col).values
    gt_names = list(gt[name_col])
    truth = np.array([gt_names.index(n) for n in truth_names])
    _, raw_counts = tp.cell_token_counts(places, args.res)
    raw_tokens = [int(sum(raw_counts.get(c, {}).values())) for c in cl]

    proj = cells.to_crs(cells.estimate_utm_crs())
    XY = StandardScaler().fit_transform(np.c_[proj.centroid.x, proj.centroid.y])
    f1 = tp.build_features(raw_counts, cl, ring=1)
    f0 = tp.build_features(raw_counts, cl, ring=0)

    layers = {'names1': {}, 'names0': {}, 'xy': {}}
    tokens = {'names1': {}, 'names0': {}}
    for k in ks:
        for key, X, f in (('names1', f1['X'], f1), ('names0', f0['X'], f0), ('xy', XY, None)):
            lab = tp.ward(cells, w, X, k)
            layers[key][str(k)] = lab.tolist()
            if f is not None:
                top = tp.region_top_tokens(f['M'], f['vocab'], lab, n=8)
                tokens[key][str(k)] = {str(r): ts for r, ts in top.items()}
        print(f'{args.city} k={k} done', flush=True)

    csv = ROOT / f'notes/2026-10-06-{args.city}-signal-check-r{args.res}.csv'
    table = pd.read_csv(csv).fillna('').to_dict('records') if csv.exists() else []

    gt_simple = gt.to_crs('EPSG:4326').copy()
    gt_simple['geometry'] = gt_simple.geometry.simplify(0.0002, preserve_topology=True)
    truth_geo = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'name': n, 'i': i}, 'geometry': mapping(g)}
        for i, (n, g) in enumerate(zip(gt_names, gt_simple.geometry))]}

    names = name_postings(raw_counts, cl)
    bounds = [[[round(lng, 5), round(lat, 5)] for lat, lng in h3.cell_to_boundary(c)] for c in cl]
    nbrs = [[int(j) for j in w.neighbors[i]] for i in range(len(cl))]
    out = {'city': args.city, 'res': args.res, 'bounds': bounds, 'neighbors': nbrs, 'release': manifest['release'],
           'places': int(manifest['rows']), 'truth_label': city['truth_label'],
           'ks': list(ks), 'cells': cl, 'truth': truth.tolist(), 'truth_names': gt_names,
           'tokens_per_cell': raw_tokens, 'layers': layers, 'region_tokens': tokens,
           'table': table, 'truth_geo': truth_geo, 'names': names}
    dest = ROOT / 'viewer' / 'data' / f'{args.city}.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, separators=(',', ':')))
    print(f'wrote {dest} ({dest.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
