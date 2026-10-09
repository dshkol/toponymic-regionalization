"""Do names change where the boundaries are? An evaluation that does not depend on k or
on how compact a partition is.

    python pipeline/boundary_auc.py --city sf

Every pair of adjacent H3 cells is an edge; an edge is a boundary edge when the two cells'
centroids fall in different areas. Each feature set (the same matrices Ward clusters on)
gives every edge a divergence: the distance between the two cells' feature vectors, and,
at a wider scale, between the mean vectors of the two sides (each cell's ring-2 or ring-3
disk minus the other's). The score is the AUC of that divergence for predicting boundary
edges. Three comparisons say what a number means: the official and the vernacular areas
(fetch_reference.py); random contiguous partitions with the same number of regions (what
any boundary set gets); and, as a positive control, the boundaries of the Ward partition
built on the same features (what the measure gives when the boundaries are where the
features change). The permutation null (names dealt to random cells) is reported too.
Edges need at least `min_tokens` tokens on both cells.
"""
import argparse

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from shapely import make_valid
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

import fields as nf
import toponymic as tp
from fetch_places import verify
from run_city import CITIES, ROOT
from run_fields import VERNACULAR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--city', choices=CITIES, default='sf')
    ap.add_argument('--res', type=int, default=9)
    ap.add_argument('--perms', type=int, default=2)
    ap.add_argument('--min_tokens', type=int, default=3)
    args = ap.parse_args()
    city = CITIES[args.city]
    verify(ROOT / city['extract'])
    gt = gpd.read_file(ROOT / city['truth'])
    places = tp.load_places(ROOT / city['extract'])
    cells = tp.city_cells(gt, args.res)
    cl = list(cells['cell'])
    n = len(cl)
    w = tp.h3_weights(cells['cell'])
    wb = tp.bridge_components(w, cells)
    _, raw = tp.cell_token_counts(places, args.res)
    xy = nf.cell_xy(cells)
    cell_width = float(np.median(nf.cKDTree(xy).query(xy, k=2)[0][:, 1]))
    A = w.sparse.tocoo()
    edges = np.array([(i, j) for i, j in zip(A.row, A.col) if i < j])
    tokens = np.array([sum(raw.get(c, {}).values()) for c in cl])
    ok = (tokens[edges[:, 0]] >= args.min_tokens) & (tokens[edges[:, 1]] >= args.min_tokens)

    truths = {'official': tp.label_cells_by_centroid(cells, gt, city['name']).values}
    alt = gpd.read_file(ROOT / VERNACULAR[args.city]).to_crs('EPSG:4326')
    alt['geometry'] = alt.geometry.apply(make_valid)
    alt = alt[alt.geometry.geom_type.isin(('Polygon', 'MultiPolygon'))].reset_index(drop=True)
    truths[f'vernacular ({len(alt)})'] = tp.label_cells_by_centroid(cells, alt, 'name').values
    rng0 = np.random.default_rng(1)
    for sd in range(3):
        truths[f'random contiguous, k={len(gt)}, seed {sd}'] = tp.random_contiguous(wb, len(gt), rng0)

    index = {c: i for i, c in enumerate(cl)}
    D = {}
    for r in (2, 3):
        rows_, cols_ = [], []
        for i, c in enumerate(cl):
            for d in h3.grid_disk(c, r):
                if d in index:
                    rows_.append(i); cols_.append(index[d])
        D[r] = csr_matrix((np.ones(len(rows_)), (rows_, cols_)), shape=(n, n))

    def measures(X):
        out = {'adjacent cells': np.linalg.norm(X[edges[:, 0]] - X[edges[:, 1]], axis=1)}
        for r in (2, 3):
            Si = D[r][edges[:, 0]] - D[r][edges[:, 0]].multiply(D[r][edges[:, 1]])
            Sj = D[r][edges[:, 1]] - D[r][edges[:, 1]].multiply(D[r][edges[:, 0]])
            mi = (Si @ X) / np.maximum(np.asarray(Si.sum(1)), 1)
            mj = (Sj @ X) / np.maximum(np.asarray(Sj.sum(1)), 1)
            out[f'two sides, ring {r}'] = np.linalg.norm(mi - mj, axis=1)
        return out

    def feature_sets(counts):
        return {'names ring 0': tp.build_features(counts, cl, ring=0)['X'],
                'names ring 1': tp.build_features(counts, cl, ring=1)['X'],
                'fields adaptive': nf.field_features(counts, cells, xy, cell_width)['X'],
                'fields fixed 1 cell': nf.field_features(counts, cells, xy, cell_width, mode='fixed')['X']}

    rng = np.random.default_rng(0)
    feats = feature_sets(raw)
    feats['coordinates only'] = StandardScaler().fit_transform(xy)
    nulls = [feature_sets(tp.permute_counts(raw, cl, rng)) for _ in range(args.perms)]
    rows = []
    for fname, X in feats.items():
        lab = tp.ward(cells, wb, X, len(gt))
        truths_f = dict(truths, **{f'own Ward partition, k={len(gt)} (positive control)': lab})
        ms = measures(X)
        for tname, truth in truths_f.items():
            y = truth[edges[:, 0]] != truth[edges[:, 1]]
            for mname, d in ms.items():
                rows.append(dict(city=args.city, feature=fname, measure=mname, truth=tname,
                                 auc=roc_auc_score(y[ok], d[ok]), edges=int(ok.sum()), boundary_share=float(y[ok].mean())))
            if fname in nulls[0] and tname.startswith(('official', 'vernacular')):
                for p, nl in enumerate(nulls):
                    for mname, d in measures(nl[fname]).items():
                        rows.append(dict(city=args.city, feature=f'null: {fname}, names permuted', measure=mname, truth=tname,
                                         auc=roc_auc_score(y[ok], d[ok]), edges=int(ok.sum()), boundary_share=float(y[ok].mean()), perm=p))
        print(f'{fname} done', flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / f'notes/2026-10-08-{args.city}-boundary-auc-r{args.res}.csv'
    df.to_csv(out, index=False)
    df['truth_group'] = df.truth.str.replace(r', seed \d', '', regex=True)
    piv = df.pivot_table(index=['feature', 'measure'], columns='truth_group', values='auc', aggfunc='mean', sort=False)
    print(f'\n{args.city}: {ok.sum()} edges with evidence on both sides\n', piv.round(3).to_string())
    print('wrote', out)


if __name__ == '__main__':
    main()
