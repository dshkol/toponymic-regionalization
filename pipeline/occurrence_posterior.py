"""Is this use of a name toponymic? A spatial mixture with closed-form updates, no MCMC.

    python pipeline/occurrence_posterior.py --city sf [--bandwidth 1.0] [--lexicon data/lexicon/sf-2026-08-19.0.jsonl]

Every occurrence of a word in a place name (counted once per distinct name per cell, as
everywhere in this pipeline) is either a toponymic use, in which case it sits where the other
toponymic uses of that word sit, or an incidental one, in which case it sits where businesses
sit. For a word t with occurrences n_tc per cell c:

    L1(c) = leave-one-out kernel density of t's other occurrences at c   (same-name evidence)
    L0(c) = kernel density of all place names at c                       (background)
    p(c)  = pi L1(c) / (pi L1(c) + (1 - pi) L0(c))                       (posterior: toponymic)
    pi    = sum_c n_tc p(c) / n_t, iterated (EM) from pi = 0.5

Both densities use the same Gaussian kernel (bandwidth in cell widths) and are normalised over
the city's cells, so a word clustered only because its businesses are downtown gets L1 ~ L0
there and stays near its prior, while a word whose uses sit next to each other in ordinary
density gets L1 >> L0 and a posterior near one. Proximity is the update: each same-name
neighbour within the kernel raises the posterior of the others.

Per word: pi (toponymic share), the core (cells with p > 0.5), core share of occurrences,
core extent (cells; largest ring-1 connected component), the median background density
percentile of the core (a density-hotspot flag), and a label:
    scattered      pi < 0.3 or no core
    point          core of 1 to 3 cells      (landmark, institution, microhood)
    area           core of 4 or more cells   (neighbourhood-sized)
plus 'hotspot' when the core's median density percentile is 0.9 or more (functional cluster
candidates: the names of a district's industry rather than the district).
Writes notes/2026-10-09-<city>-occurrence-posterior-r9.csv and, with --lexicon, a cross-tab
of pi by the typed lexicon's class.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, diags
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

import fields as nf
import toponymic as tp
from fetch_places import verify
from run_city import CITIES, ROOT


def kernel_matrix(xy: np.ndarray, h: float, cutoff: float = 3.0) -> csr_matrix:
    n = len(xy)
    tree = cKDTree(xy)
    D = tree.sparse_distance_matrix(tree, cutoff * h, output_type='coo_matrix')
    # the coo output already holds the zero-distance self pairs, so the diagonal is exp(0) = 1
    return csr_matrix((np.exp(-D.data ** 2 / (2 * h * h)), (D.row, D.col)), shape=(n, n))


def posterior_for(M, K, L0, w, min_support=5, iters=25):
    """M: cells x words counts (csr). Returns per-word dicts."""
    n, V = M.shape
    Mc = M.tocsc()
    out = []
    Ksum = np.asarray(K.sum(0)).ravel()
    Kn = K @ diags(1 / Ksum)             # each source cell spreads unit mass over the city
    for j in range(V):
        idx = Mc.indices[Mc.indptr[j]:Mc.indptr[j + 1]]
        cnt = Mc.data[Mc.indptr[j]:Mc.indptr[j + 1]]
        n_t = cnt.sum()
        if n_t < min_support:
            continue
        # leave-one-out same-name density at each occurrence cell: all occurrences minus self
        src = np.zeros(n); src[idx] = cnt
        full = Kn @ src                                  # density from all occurrences (sums to n_t)
        loo = full[idx] - cnt / Ksum[idx]                # minus each cell's own occurrences
        L1 = np.maximum(loo, 0) / max((n_t - 1), 1)      # leave-one-out density, sums to ~1 over cells
        L0c = L0[idx]
        pi = 0.5
        for _ in range(iters):
            p = pi * L1 / (pi * L1 + (1 - pi) * L0c + 1e-300)
            pi = float((cnt * p).sum() / n_t)
            pi = min(max(pi, 1e-4), 1 - 1e-4)
        p = pi * L1 / (pi * L1 + (1 - pi) * L0c + 1e-300)
        core = idx[p > 0.5]
        core_share = float(cnt[p > 0.5].sum() / n_t)
        if len(core):
            sub = w.sparse[core][:, core]
            ncomp, comp = connected_components(sub, directed=False)
            largest = int(np.bincount(comp).max())
        else:
            ncomp, largest = 0, 0
        out.append(dict(word_index=j, support=int(n_t), cells=int(len(idx)), pi=pi, core_cells=int(len(core)),
                        core_share=core_share, core_components=int(ncomp), core_largest=largest,
                        core_idx=core.tolist(), post=p.tolist(), occ_idx=idx.tolist()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--city', choices=CITIES, default='sf')
    ap.add_argument('--res', type=int, default=9)
    ap.add_argument('--bandwidth', type=float, default=1.0, help='kernel bandwidth in cell widths')
    ap.add_argument('--min_support', type=int, default=5)
    ap.add_argument('--lexicon', default=None, help='typed lexicon jsonl (shared-layer branch) for a class cross-tab')
    ap.add_argument('--export', default=None, help='also write a compact JSON of posteriors for the viewer')
    args = ap.parse_args()
    city = CITIES[args.city]
    verify(ROOT / city['extract'])
    gt = gpd.read_file(ROOT / city['truth'])
    places = tp.load_places(ROOT / city['extract'])
    cells = tp.city_cells(gt, args.res)
    cl = list(cells['cell'])
    w = tp.h3_weights(cells['cell'])
    _, raw = tp.cell_token_counts(places, args.res)
    xy = nf.cell_xy(cells)
    cell_width = float(np.median(cKDTree(xy).query(xy, k=2)[0][:, 1]))
    h = args.bandwidth * cell_width
    truth = tp.label_cells_by_centroid(cells, gt, city['name']).values

    # vocabulary: every word in at least one cell; counts once per distinct name per cell
    vocab, df, M = nf.count_matrix(raw, cl, min_df=1, max_df_frac=1.0)
    K = kernel_matrix(xy, h)
    tokens = np.asarray(M.sum(1)).ravel()
    Ksum = np.asarray(K.sum(0)).ravel()
    L0 = (K @ diags(1 / Ksum)) @ tokens / tokens.sum()   # background density, sums to 1 over cells
    dens_pct = pd.Series(tokens).rank(pct=True).values

    rows = posterior_for(M, K, L0, w, min_support=args.min_support)
    recs = []
    for r in rows:
        core = np.array(r['core_idx'], dtype=int)
        hotspot = float(np.median(dens_pct[core])) if len(core) else float('nan')
        label = 'scattered' if (r['pi'] < 0.3 or r['core_cells'] == 0) else ('point' if r['core_largest'] <= 3 else 'area')
        top_area = Counter(truth[core]).most_common(1)[0][0] if len(core) else ''
        recs.append(dict(word=vocab[r['word_index']], support=r['support'], cells=r['cells'], pi=round(r['pi'], 3),
                         core_cells=r['core_cells'], core_share=round(r['core_share'], 3), core_components=r['core_components'],
                         core_largest=r['core_largest'], core_density_pct=round(hotspot, 2) if hotspot == hotspot else '',
                         hotspot=bool(hotspot >= 0.9) if hotspot == hotspot else False, label=label, core_area=top_area))
    df_out = pd.DataFrame(recs).sort_values(['pi', 'support'], ascending=False)
    out = ROOT / f'notes/2026-10-09-{args.city}-occurrence-posterior-r{args.res}.csv'
    df_out.to_csv(out, index=False)
    print(f'{args.city}: {len(df_out)} words with support >= {args.min_support}; labels:',
          df_out.label.value_counts().to_dict(), '| hotspot cores:', int(df_out.hotspot.sum()))
    print(df_out.head(25).to_string(index=False))

    if args.lexicon:
        lex = {json.loads(l)['phrase']: json.loads(l)['class'] for l in open(args.lexicon)}
        df_out['class'] = df_out.word.map(lex).fillna('(not in lexicon)')
        xt = df_out.groupby('class').agg(words=('word', 'size'), mean_pi=('pi', 'mean'), median_pi=('pi', 'median'),
                                         area=('label', lambda s: (s == 'area').mean()), point=('label', lambda s: (s == 'point').mean()),
                                         scattered=('label', lambda s: (s == 'scattered').mean())).round(2)
        print('\npi by lexicon class:\n', xt.to_string())
        xt.to_csv(out.with_name(out.stem + '-by-class.csv'))

    if args.export:
        comp = {}
        for r in rows:
            flat = []
            for i, p in zip(r['occ_idx'], r['post']):
                flat.extend((int(i), round(float(p), 2)))
            comp[vocab[r['word_index']]] = {'pi': round(r['pi'], 3), 'core_share': round(r['core_share'], 2),
                                            'core_largest': r['core_largest'], 'p': flat}
        Path(args.export).write_text(json.dumps(comp, separators=(',', ':')))
        print('exported', args.export)


if __name__ == '__main__':
    main()
