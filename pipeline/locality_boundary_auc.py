"""Boundary AUC (see boundary_auc.py) with the vocabulary cut to the typed lexicon's locality
classes (area, division, mixed): do the toponyms themselves change where the boundaries are?

    python pipeline/locality_boundary_auc.py --city sf --lexicon data/lexicon/sf-2026-08-19.0.jsonl
"""
import sys, json

import numpy as np, geopandas as gpd
from collections import Counter
from scipy.sparse import coo_matrix, diags
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.metrics import roc_auc_score
from shapely import make_valid
import fields as nf, toponymic as tp
from run_city import CITIES, ROOT
from run_fields import VERNACULAR
import argparse
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--city', choices=CITIES, default='sf')
ap.add_argument('--lexicon', required=True, help='typed lexicon jsonl from the shared-layer branch, e.g. git show origin/claude/project-thread-x4tws5:data/lexicon/sf-2026-08-19.0.jsonl > data/lexicon/sf-2026-08-19.0.jsonl')
args = ap.parse_args()
cityname = args.city
lex = [json.loads(l) for l in open(args.lexicon)]
loc = {r['phrase'] for r in lex if r['class'] in ('area', 'division', 'mixed') and ' ' not in r['phrase']}
city = CITIES[cityname]; gt = gpd.read_file(ROOT / city['truth']); places = tp.load_places(ROOT / city['extract'])
cells = tp.city_cells(gt, 9); cl = list(cells['cell']); n = len(cl); w = tp.h3_weights(cells['cell']); wb = tp.bridge_components(w, cells)
_, raw = tp.cell_token_counts(places, 9)
truth = tp.label_cells_by_centroid(cells, gt, city['name']).values
alt = gpd.read_file(ROOT / VERNACULAR[cityname]).to_crs('EPSG:4326'); alt['geometry'] = alt.geometry.apply(make_valid)
alt = alt[alt.geometry.geom_type.isin(('Polygon', 'MultiPolygon'))].reset_index(drop=True)
vern = tp.label_cells_by_centroid(cells, alt, 'name').values
A = w.sparse.tocoo(); edges = np.array([(i, j) for i, j in zip(A.row, A.col) if i < j])
tokens = np.array([sum(raw.get(c, {}).values()) for c in cl]); ok = (tokens[edges[:, 0]] >= 3) & (tokens[edges[:, 1]] >= 3)
rb = tp.random_contiguous(wb, len(gt), np.random.default_rng(1))

def feats(counts, ring, vocab_filter, dims=30):
    df = Counter()
    for c in cl:
        for t in counts.get(c, {}): df[t] += 1
    vocab = sorted(t for t in df if 3 <= df[t] <= 0.2 * n and t in vocab_filter)
    vidx = {t: i for i, t in enumerate(vocab)}
    sm = tp.smooth_counts(counts, cl, ring)
    r_, c_, v_ = [], [], []
    for i, c in enumerate(cl):
        for t, k in sm.get(c, {}).items():
            if t in vidx: r_.append(i); c_.append(vidx[t]); v_.append(k)
    M = coo_matrix((v_, (r_, c_)), shape=(n, len(vocab))).tocsr().astype(float)
    X = normalize(M.sqrt() @ diags(np.log(n / np.array([df[t] for t in vocab]))))
    return TruncatedSVD(min(dims, len(vocab) - 1), random_state=0).fit_transform(X), len(vocab), np.asarray(M.sum(1)).ravel()

rng = np.random.default_rng(0); pc = tp.permute_counts(raw, cl, rng)
print(f'{cityname}: {len(loc)} single-word locality phrases in the lexicon')
print(f'{"feature":34s} vocab  cover  official vernac random ownWard | null-official')
for ring in (0, 1, 2):
    X, nv, cov = feats(raw, ring, loc); Xn, _, _ = feats(pc, ring, loc)
    both = ok & (cov[edges[:, 0]] > 0) & (cov[edges[:, 1]] > 0)
    lab = tp.ward(cells, wb, X, len(gt))
    d = np.linalg.norm(X[edges[:, 0]] - X[edges[:, 1]], axis=1); dn = np.linalg.norm(Xn[edges[:, 0]] - Xn[edges[:, 1]], axis=1)
    for mask, label in ((ok, 'all edges'), (both, 'edges w/ locality both sides')):
        ys = [truth[edges[:, 0]] != truth[edges[:, 1]], vern[edges[:, 0]] != vern[edges[:, 1]], rb[edges[:, 0]] != rb[edges[:, 1]], lab[edges[:, 0]] != lab[edges[:, 1]]]
        aucs = [roc_auc_score(y[mask], d[mask]) for y in ys]; nl = roc_auc_score(ys[0][mask], dn[mask])
        print(f'locality ring {ring}, {label:30s} {nv:5d}  {mask.mean():.2f}   ' + '   '.join(f'{a:.2f}' for a in aucs) + f'   | {nl:.2f}', flush=True)
