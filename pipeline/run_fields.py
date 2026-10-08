"""Name fields as features: does replacing k-ring smoothing with per-toponym kernels help?

    python pipeline/run_fields.py --city sf

For each k: SCHC Ward on (a) ring-1 count features (the baseline), (b) name-field features
(adaptive bandwidth), (c) fixed one-cell bandwidth, (d) coordinates only; each with ARI
against the official areas and name recovery (share of regions whose top-3 lifted tokens
name the area holding most of their cells; share of areas so recovered). Permutation null
for (a) and (b). Plus the watershed ablation (fields win directly, no clustering) and max-p
with a places-per-region floor on the field features.
"""
import argparse
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

import fields as nf
import toponymic as tp
from fetch_places import verify
from run_city import CITIES, KS, ROOT

# second ground truth per city: vernacular / older official polygons (see fetch_reference.py)
VERNACULAR = {c: f'data/reference/{c}-clickthathood-2026-10-08.geojson' for c in CITIES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--city', choices=CITIES, default='sf')
    ap.add_argument('--res', type=int, default=9)
    ap.add_argument('--ks', default=None, help='comma list; default 5,10,20,40 + number of areas')
    ap.add_argument('--perms', type=int, default=3)
    ap.add_argument('--maxp', action='store_true', help='also run max-p (slow on big cities)')
    ap.add_argument('--truth', choices=('official', 'vernacular'), default='official',
                    help='score against the official areas (cells come from them either way) or the click_that_hood polygons')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    city = CITIES[args.city]
    tag = '' if args.truth == 'official' else '-vernacular'
    out = ROOT / (args.out or f'notes/2026-10-08-{args.city}-name-fields{tag}-r{args.res}')

    extract = ROOT / city['extract']
    verify(extract)
    gt = gpd.read_file(ROOT / city['truth'])
    gt_names = list(gt[city['name']])
    places = tp.load_places(extract)
    ks = [int(k) for k in args.ks.split(',')] if args.ks else list(KS) + ([len(gt)] if len(gt) not in KS else [])

    cells = tp.city_cells(gt, args.res)
    cl = list(cells['cell'])
    w = tp.bridge_components(tp.h3_weights(cells['cell']), cells)
    if args.truth == 'vernacular':
        from shapely import make_valid
        alt = gpd.read_file(ROOT / VERNACULAR[args.city]).to_crs('EPSG:4326')
        alt['geometry'] = alt.geometry.apply(make_valid)
        alt = alt[alt.geometry.geom_type.isin(('Polygon', 'MultiPolygon'))].reset_index(drop=True)
        gt, gt_names = alt, list(alt['name'])
        city = dict(city, name='name')
        print(f'scoring against {len(gt)} vernacular polygons', flush=True)
    truth_names = tp.label_cells_by_centroid(cells, gt, city['name']).values
    truth = np.array([gt_names.index(n) if n in gt_names else len(gt_names) for n in truth_names])
    covered = truth < len(gt_names)
    print(f'{covered.sum()} of {len(cl)} cells inside the scoring polygons', flush=True)
    gt_names = gt_names + ['(outside)']
    _, raw_counts = tp.cell_token_counts(places, args.res)
    xy = nf.cell_xy(cells)
    cell_width = float(np.median(cKDTree_nn(xy)))
    XY = StandardScaler().fit_transform(xy)
    rng = np.random.default_rng(0)

    t0 = time.time()
    base = tp.build_features(raw_counts, cl, ring=1)
    base0 = tp.build_features(raw_counts, cl, ring=0)
    fa = nf.field_features(raw_counts, cells, xy, cell_width, mode='adaptive')
    f1 = nf.field_features(raw_counts, cells, xy, cell_width, mode='fixed', fixed_cells=1.0)
    print(f'{args.city}: {len(cl)} cells, cell width {cell_width:.0f} m, vocab {len(fa["vocab"])}, '
          f'bandwidth median {np.median(fa["h"])/cell_width:.1f} cells, features in {time.time()-t0:.0f}s', flush=True)
    M0, vocab0 = fa['M'], fa['vocab']  # unsmoothed counts for naming every partition

    rows, parts = [], {}

    def record(method, k, labels, note=''):
        sc = tp.score(labels, truth, mask=covered)
        nr = nf.name_recovery(M0, vocab0, labels, truth, gt_names)
        largest = np.bincount(labels).max() / len(labels)
        rows.append(dict(method=method, k=k, k_actual=nr['k'], ari=sc['ari'], nmi=sc['nmi'],
                         regions_named=nr['regions_named'], areas_recovered=nr['areas_recovered'],
                         largest=largest, note=note))
        print(f'  {method:34s} k={k:>4} ari={sc["ari"]:.2f} named={nr["regions_named"]:.2f} '
              f'recovered={nr["areas_recovered"]:.2f} largest={largest:.2f}', flush=True)
        return nr

    for k in ks:
        print(f'k={k}', flush=True)
        record('names ring 1 (baseline)', k, tp.ward(cells, w, base['X'], k))
        record('names unsmoothed', k, tp.ward(cells, w, base0['X'], k))
        lab = tp.ward(cells, w, fa['X'], k); parts[('fields adaptive', k)] = lab
        nr = record('fields adaptive', k, lab)
        record('fields fixed 1 cell', k, tp.ward(cells, w, f1['X'], k))
        record('coordinates only', k, tp.ward(cells, w, XY, k))
        for p in range(args.perms):
            pc = tp.permute_counts(raw_counts, cl, rng)
            record('null: ring 1, names permuted', k, tp.ward(cells, w, tp.build_features(pc, cl, ring=1)['X'], k), f'perm {p}')
            pf = nf.field_features(pc, cells, xy, cell_width, mode='adaptive')
            record('null: fields adaptive, names permuted', k, tp.ward(cells, w, pf['X'], k), f'perm {p}')
        for s in range(5):
            record('floor: random contiguous', k, tp.random_contiguous(w, k, rng), f'seed {s}')
        if k == ks[-1]:
            parts['top_tokens'] = nr['rows']

    ws = nf.watershed(fa['F'], fa['df'], fa['vocab'], w)
    record('watershed: fields win directly', len(np.unique(ws)), ws)
    parts[('watershed', len(np.unique(ws)))] = ws

    if args.maxp:
        from spopt.region import MaxPHeuristic
        tokens = np.array([sum(raw_counts.get(c, {}).values()) for c in cl], dtype=float)
        for k in (20, ks[-1]):
            thr = tokens.sum() / k
            cols = [f'f{i}' for i in range(fa['X'].shape[1])]
            g = gpd.GeoDataFrame(pd.DataFrame(fa['X'], columns=cols, index=cells.index), geometry=cells.geometry, crs=cells.crs)
            g['tokens'] = tokens
            t1 = time.time()
            m = MaxPHeuristic(g, w, cols, 'tokens', thr, top_n=2, max_iterations_construction=99, max_iterations_sa=10)
            m.solve()
            lab = np.asarray(m.labels_).astype(int)
            _, lab = np.unique(lab, return_inverse=True)
            record('max-p on fields, floor tokens/k', k, lab, f'{time.time()-t1:.0f}s')
            parts[('maxp', k)] = lab

    df = pd.DataFrame(rows)
    df.to_csv(out.with_suffix('.csv'), index=False)
    summary = (df[~df.method.str.startswith(('null', 'floor'))]
               .groupby(['method', 'k'], sort=False)[['ari', 'regions_named', 'areas_recovered', 'largest']].mean())
    nulls = (df[df.method.str.startswith(('null', 'floor'))]
             .groupby(['method', 'k'], sort=False)[['ari', 'regions_named', 'areas_recovered']].mean())
    print('\n', summary.round(2).to_string(), '\n\n', nulls.round(2).to_string())
    np.save(out.with_name(out.name + '-partitions.npy'), {str(k): v for k, v in parts.items()}, allow_pickle=True)
    print('wrote', out.with_suffix('.csv'))


def cKDTree_nn(xy):
    from scipy.spatial import cKDTree
    d, _ = cKDTree(xy).query(xy, k=2)
    return d[:, 1]


if __name__ == '__main__':
    main()
