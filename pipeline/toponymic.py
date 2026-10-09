"""Toponymic regionalization: cells, name-token features, regionalization, scoring.

Everything here is deliberately plain so each step can be inspected and argued with.
See HANDOFF.md for the hypotheses this is built to test.
"""
import re
import unicodedata
from collections import Counter, defaultdict

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from libpysal import weights
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from shapely import from_wkb
from shapely.geometry import Polygon
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize
from spopt.region import WardSpatial

# ---- places -------------------------------------------------------------------

def load_places(path) -> gpd.GeoDataFrame:
    """Overture Places extract -> points with primary name and category."""
    t = pq.read_table(path, columns=['id', 'geometry', 'names', 'categories', 'confidence',
                                     'brand', 'operating_status'])
    df = t.to_pandas()
    df['name'] = df['names'].map(lambda n: (n or {}).get('primary'))
    df['category'] = df['categories'].map(lambda c: (c or {}).get('primary'))
    df['brand'] = df['brand'].map(lambda b: ((b or {}).get('names') or {}).get('primary'))
    geom = from_wkb(df['geometry'].values)
    gdf = gpd.GeoDataFrame(df.drop(columns=['geometry', 'names', 'categories']),
                           geometry=geom, crs='EPSG:4326')
    return gdf[gdf['name'].notna()].reset_index(drop=True)


# ---- cells and contiguity -----------------------------------------------------

def city_cells(boundary: gpd.GeoDataFrame, res: int) -> gpd.GeoDataFrame:
    """H3 cells whose centroid falls inside the union of the ground-truth polygons."""
    union = boundary.to_crs('EPSG:4326').union_all()
    cells = sorted(h3.h3shape_to_cells(h3.geo_to_h3shape(union), res))
    polys = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in cells]
    return gpd.GeoDataFrame({'cell': cells}, geometry=polys, crs='EPSG:4326')


def h3_weights(cells: pd.Series) -> weights.W:
    """k-ring (ring 1) contiguity restricted to the cell set."""
    index = {c: i for i, c in enumerate(cells)}
    nbrs = {i: [index[n] for n in h3.grid_ring(c, 1) if n in index] for c, i in index.items()}
    return weights.W(nbrs, id_order=list(range(len(cells))), silence_warnings=True)


def bridge_components(w: weights.W, gdf: gpd.GeoDataFrame) -> weights.W:
    """Join disconnected components (water gaps) by nearest centroid pair to the main one.
    Copied from regionalization-lab/companion/regionalization_lab.py."""
    n_comp, comp = connected_components(w.sparse, directed=False)
    if n_comp == 1:
        return w
    main = np.bincount(comp).argmax()
    proj = gdf.to_crs(gdf.estimate_utm_crs())
    xy = np.c_[proj.centroid.x, proj.centroid.y]
    main_ids = np.where(comp == main)[0]
    tree = cKDTree(xy[main_ids])
    nbrs = {k: list(v) for k, v in w.neighbors.items()}
    for c in set(comp) - {main}:
        ids = np.where(comp == c)[0]
        d, j = tree.query(xy[ids])
        a, b = int(ids[d.argmin()]), int(main_ids[j[d.argmin()]])
        nbrs[a].append(b); nbrs[b].append(a)
    return weights.W(nbrs, id_order=w.id_order, silence_warnings=True)


def label_cells_by_centroid(cells: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame, name_col: str) -> pd.Series:
    """Ground-truth label of each cell = polygon containing its centroid (nearest if none)."""
    cen = gpd.GeoDataFrame(geometry=cells.geometry.centroid, crs=cells.crs)
    joined = gpd.sjoin(cen, boundary[[name_col, 'geometry']].to_crs(cells.crs),
                       how='left', predicate='within')
    joined = joined[~joined.index.duplicated()]
    missing = joined[name_col].isna()
    if missing.any():
        near = gpd.sjoin_nearest(cen[missing], boundary[[name_col, 'geometry']].to_crs(cells.crs))
        joined.loc[missing, name_col] = near[~near.index.duplicated()][name_col]
    return joined[name_col]


# ---- tokens -------------------------------------------------------------------

STOP = set("""
a an and the of for in on at to by with from or de la le el las los del y
inc llc ltd co corp company corporation group international enterprises services service
shop store market cafe coffee restaurant bar grill kitchen bakery deli pizza sushi taqueria
salon spa nails hair barber beauty studio gallery fitness gym yoga dental dentist clinic
medical center centre office offices law attorney attorneys insurance realty real estate
properties property management consulting consultants associates partners solutions
school academy church hotel motel apartments apartment park parking garage auto
san francisco sf ca california usa us street st ave avenue blvd boulevard rd road dr drive
way ln lane ct court pl place
""".split())


def tokenize(name: str) -> list[str]:
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    return [t for t in re.split(r'[^a-z]+', s) if len(t) > 1 and t not in STOP]


def cell_token_counts(places: gpd.GeoDataFrame, res: int) -> tuple[pd.Series, dict]:
    """Per cell: tokens counted once per distinct normalized name (the Cadmus support cap).
    Returns (cell id per place, {cell: Counter})."""
    cell_of = pd.Series([h3.latlng_to_cell(p.y, p.x, res) for p in places.geometry], index=places.index)
    names_by_cell = defaultdict(set)
    for c, n in zip(cell_of, places['name']):
        names_by_cell[c].add(' '.join(tokenize(n)))
    counts = {c: Counter(t for n in names for t in set(n.split()) if t) for c, names in names_by_cell.items()}
    return cell_of, counts


def smooth_counts(counts: dict, cells: list[str], ring: int) -> dict:
    """Sum counts over each cell's k-ring: a scale knob, not a model."""
    if ring == 0:
        return counts
    index = set(cells)
    out = {}
    for c in cells:
        acc = Counter()
        for n in h3.grid_disk(c, ring):
            if n in index and n in counts:
                acc.update(counts[n])
        out[c] = acc
    return out


def build_features(raw_counts: dict, cells: list[str], ring: int = 1, min_df: int = 5,
                   max_df_frac: float = 0.2, svd_dims: int = 30, drop: set | None = None):
    """Name-token features per cell.

    Vocabulary comes from the *unsmoothed* counts (cell document frequency in
    [min_df, max_df_frac * n]), so the k-ring smoothing changes the evidence per cell
    but not which tokens count. Then sqrt(tf) * idf, L2-normalised per cell, reduced
    by truncated SVD. `drop` removes tokens from the vocabulary (e.g. street names). Unit-length rows keep Ward from peeling off dense cells as
    outliers, which is what happened with raw or clr features (see notes).
    Returns dict with 'vocab', 'M' (smoothed counts), 'X' (svd features), 'n_tokens'."""
    n = len(cells)
    df = Counter()
    for c in cells:
        for t in raw_counts.get(c, {}):
            df[t] += 1
    drop = drop or set()
    vocab = sorted(t for t in df if min_df <= df[t] <= max_df_frac * n and t not in drop)
    vidx = {t: i for i, t in enumerate(vocab)}
    counts = smooth_counts(raw_counts, cells, ring)
    rows, cols, vals = [], [], []
    for i, c in enumerate(cells):
        for t, k in counts.get(c, {}).items():
            if t in vidx:
                rows.append(i); cols.append(vidx[t]); vals.append(k)
    M = coo_matrix((vals, (rows, cols)), shape=(n, len(vocab))).tocsr().astype(float)
    return {'vocab': vocab, 'M': M, 'X': reduce_counts(M, df, vocab, n, svd_dims),
            'n_tokens': np.asarray(M.sum(1)).ravel()}


def reduce_counts(M, df: Counter, vocab: list[str], n: int, svd_dims: int) -> np.ndarray:
    idf = np.log(n / np.array([df[t] for t in vocab]))
    X = normalize(M.sqrt() @ diags(idf))
    return TruncatedSVD(svd_dims, random_state=0).fit_transform(X) if M.nnz else np.zeros((n, svd_dims))


def permute_counts(raw_counts: dict, cells: list[str], rng: np.random.Generator) -> dict:
    """Null model: the same bags of names, dealt to random cells."""
    bags = [raw_counts.get(c, Counter()) for c in cells]
    perm = rng.permutation(len(cells))
    return {cells[i]: bags[perm[i]] for i in range(len(cells))}


# ---- regionalization ----------------------------------------------------------

def ward(gdf: gpd.GeoDataFrame, w: weights.W, X: np.ndarray, k: int) -> np.ndarray:
    """SCHC Ward (spopt.WardSpatial) on feature matrix X with contiguity w."""
    cols = [f'f{i}' for i in range(X.shape[1])]
    g = gpd.GeoDataFrame(pd.DataFrame(X, columns=cols, index=gdf.index),
                         geometry=gdf.geometry, crs=gdf.crs)
    m = WardSpatial(g, w, cols, n_clusters=k); m.solve()
    return np.asarray(m.labels_).astype(int)


def random_contiguous(w: weights.W, k: int, rng: np.random.Generator) -> np.ndarray:
    """Grow k regions from random seeds by random frontier expansion: the floor."""
    n = w.n
    labels = -np.ones(n, dtype=int)
    seeds = rng.choice(n, k, replace=False)
    frontier = []
    for r, s in enumerate(seeds):
        labels[s] = r; frontier.append((s, r))
    while frontier:
        i = rng.integers(len(frontier)); u, r = frontier.pop(i)
        for v in w.neighbors[u]:
            if labels[v] < 0:
                labels[v] = r; frontier.append((v, r))
    # unreachable cells (should not exist after bridging) get nearest label
    labels[labels < 0] = 0
    return labels


def heterogeneity_removed(X: np.ndarray, labels: np.ndarray) -> float:
    tot = ((X - X.mean(0)) ** 2).sum()
    within = sum(((X[labels == r] - X[labels == r].mean(0)) ** 2).sum() for r in np.unique(labels))
    return 100 * (1 - within / tot) if tot > 0 else 0.0


def score(labels: np.ndarray, truth: np.ndarray, mask=None) -> dict:
    if mask is not None:
        labels, truth = labels[mask], truth[mask]
    return {'ari': adjusted_rand_score(truth, labels), 'nmi': normalized_mutual_info_score(truth, labels)}


def kmeans_ceiling(X: np.ndarray, k: int) -> np.ndarray:
    return KMeans(k, n_init=10, random_state=0).fit(X).labels_


def region_top_tokens(M, vocab_all, labels, n=6) -> dict:
    """For each region, tokens with the highest share lift relative to the city."""
    tot = np.asarray(M.sum(0)).ravel() + 1e-9
    out = {}
    for r in np.unique(labels):
        s = np.asarray(M[labels == r].sum(0)).ravel()
        lift = (s / s.sum()) / (tot / tot.sum()) if s.sum() else np.zeros_like(s)
        lift[s < 3] = 0
        top = np.argsort(-lift)[:n]
        out[int(r)] = [vocab_all[j] for j in top if lift[j] > 0]
    return out
