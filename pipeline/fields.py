"""Name fields: each toponym as a kernel density over the cells that carry it.

A token's field at cell c is sum over cells c' of count(c', t) * exp(-d(c, c')^2 / 2h_t^2),
where h_t is the token's own bandwidth: the median nearest-neighbour distance between the
cells that carry it, clipped to [1, max_cells] cell widths (a token whose cells are spread
out but clustered gets a bandwidth that bridges its gaps; a token found in one cell stays
one cell wide). The fields replace k-ring smoothing, which used one radius for every name.

Fields then go through the same sqrt * idf, L2, SVD as the count features, so Ward and
max-p see them as features, and the permutation null applies unchanged (deal the bags of
names to random cells, then build the fields).
"""
from collections import Counter

import numpy as np
from scipy.sparse import csr_matrix, coo_matrix, diags
from scipy.spatial import cKDTree
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

import toponymic as tp


def cell_xy(cells) -> np.ndarray:
    """Cell centroids in metres (local UTM)."""
    proj = cells.to_crs(cells.estimate_utm_crs())
    return np.c_[proj.centroid.x, proj.centroid.y]


def count_matrix(raw_counts: dict, cells: list[str], min_df=5, max_df_frac=0.2):
    """Unsmoothed cell x token counts over the same vocabulary rule as build_features."""
    n = len(cells)
    df = Counter()
    for c in cells:
        for t in raw_counts.get(c, {}):
            df[t] += 1
    vocab = sorted(t for t in df if min_df <= df[t] <= max_df_frac * n)
    vidx = {t: i for i, t in enumerate(vocab)}
    rows, cols, vals = [], [], []
    for i, c in enumerate(cells):
        for t, k in raw_counts.get(c, {}).items():
            if t in vidx:
                rows.append(i); cols.append(vidx[t]); vals.append(k)
    M = coo_matrix((vals, (rows, cols)), shape=(n, len(vocab))).tocsr().astype(float)
    return vocab, df, M


def token_bandwidths(M, xy: np.ndarray, cell_width: float, max_cells: float = 4.0,
                     mode: str = 'adaptive', fixed_cells: float = 1.0) -> np.ndarray:
    """Bandwidth per token in metres."""
    if mode == 'fixed':
        return np.full(M.shape[1], fixed_cells * cell_width)
    Mc = M.tocsc()
    h = np.empty(M.shape[1])
    for j in range(M.shape[1]):
        idx = Mc.indices[Mc.indptr[j]:Mc.indptr[j + 1]]
        if len(idx) < 2:
            h[j] = cell_width; continue
        d, _ = cKDTree(xy[idx]).query(xy[idx], k=2)
        h[j] = np.clip(np.median(d[:, 1]), cell_width, max_cells * cell_width)
    return h


def build_fields(M, xy: np.ndarray, h: np.ndarray, cutoff: float = 3.0, bins: int = 6):
    """Cell x token field matrix. Tokens are binned by bandwidth so each bin is one sparse
    kernel matrix (truncated at `cutoff` bandwidths) times the count columns of that bin."""
    n = M.shape[0]
    tree = cKDTree(xy)
    F = np.zeros(M.shape)
    edges = np.quantile(h, np.linspace(0, 1, bins + 1))
    edges[-1] += 1
    Mc = M.tocsc()
    for b in range(bins):
        cols = np.where((h >= edges[b]) & (h < edges[b + 1]))[0]
        if not len(cols):
            continue
        hb = float(np.median(h[cols]))
        D = tree.sparse_distance_matrix(tree, cutoff * hb, output_type='coo_matrix')
        K = csr_matrix((np.exp(-D.data ** 2 / (2 * hb ** 2)), (D.row, D.col)), shape=(n, n))
        K = K + diags(np.ones(n))  # sparse_distance_matrix drops the zero self-distance
        F[:, cols] = (K @ Mc[:, cols]).toarray()
    return F


def reduce_fields(F: np.ndarray, df: Counter, vocab: list[str], n: int, svd_dims: int = 30) -> np.ndarray:
    idf = np.log(n / np.array([df[t] for t in vocab]))
    X = normalize(np.sqrt(F) * idf)
    return TruncatedSVD(svd_dims, random_state=0).fit_transform(X)


def field_features(raw_counts: dict, cells, xy: np.ndarray, cell_width: float, mode='adaptive',
                   fixed_cells=1.0, max_cells=4.0, svd_dims=30) -> dict:
    cl = list(cells['cell'])
    vocab, df, M = count_matrix(raw_counts, cl)
    h = token_bandwidths(M, xy, cell_width, max_cells=max_cells, mode=mode, fixed_cells=fixed_cells)
    F = build_fields(M, xy, h)
    return {'vocab': vocab, 'df': df, 'M': M, 'F': F, 'h': h,
            'X': reduce_fields(F, df, vocab, len(cl), svd_dims)}


def watershed(F: np.ndarray, df: Counter, vocab: list[str], w, min_cells: int = 3) -> np.ndarray:
    """Ablation: no clustering. Each cell takes the token whose idf-weighted field is strongest,
    regions are the contiguous runs of one token; runs smaller than min_cells are absorbed
    by the neighbouring region they touch most."""
    from scipy.sparse.csgraph import connected_components
    n = F.shape[0]
    idf = np.log(n / np.array([df[t] for t in vocab]))
    S = F * idf
    best = S.argmax(1)
    best[S.max(1) <= 0] = -1
    A = w.sparse.tocoo()
    same = best[A.row] == best[A.col]
    G = csr_matrix((np.ones(same.sum()), (A.row[same], A.col[same])), shape=(n, n))
    _, comp = connected_components(G, directed=False)
    sizes = np.bincount(comp)
    labels = comp.copy()
    for _ in range(10):
        small = np.where(sizes[labels] < min_cells)[0]
        if not len(small):
            break
        for i in small:
            nb = [labels[j] for j in w.neighbors[i] if sizes[labels[j]] >= min_cells]
            if nb:
                labels[i] = Counter(nb).most_common(1)[0][0]
        sizes = np.bincount(labels, minlength=len(sizes))
    _, labels = np.unique(labels, return_inverse=True)
    return labels


def name_recovery(M, vocab: list[str], labels: np.ndarray, truth: np.ndarray, truth_names: list[str],
                  n_top: int = 3) -> dict:
    """Score a partition by its names, not its boundaries. A region is 'named' when one of its
    n_top lifted tokens (from the unsmoothed counts) is a token of the official area that holds
    the plurality of its cells; an area is 'recovered' when some region whose plurality area it
    is names it. Returns both shares and the list of (region, plurality area, named?)."""
    top = tp.region_top_tokens(M, vocab, labels, n=n_top)
    area_tokens = {i: set(tp.tokenize(nm)) for i, nm in enumerate(truth_names)}
    named, recovered, rows = 0, set(), []
    for r in np.unique(labels):
        a = int(np.bincount(truth[labels == r]).argmax())
        hit = bool(area_tokens[a] & set(top.get(int(r), [])))
        named += hit
        if hit:
            recovered.add(a)
        rows.append((int(r), truth_names[a], hit, top.get(int(r), [])))
    k = len(np.unique(labels))
    return {'regions_named': named / k, 'areas_recovered': len(recovered) / len(truth_names),
            'k': k, 'rows': rows}
