"""Phase 1 signal check per city: H3 cells, names-only tokens, SCHC Ward.

    python pipeline/run_city.py --city sf --res 9 --rings 0,1,2

For each smoothing ring and k in (5, 10, 20, 40, number of ground-truth areas): ARI/NMI of the SCHC Ward partition on
name features against the city's ground-truth areas, next to the nulls that say
whether the number means anything: the same pipeline on names dealt to random cells
(permutation null), Ward on coordinates only, random contiguous partitions (floor), and
unconstrained k-means on the same name features (no contiguity).
"""
import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

import toponymic as tp
from fetch_places import verify

ROOT = Path(__file__).resolve().parents[1]
KS = (5, 10, 20, 40)
RELEASE = '2026-08-19.0'

# extract, ground-truth file, name column, how the ground truth was obtained
CITIES = {
    'sf': dict(extract=f'data/sf/overture-sf-{RELEASE}.parquet',
               truth='data/sf/datasf-analysis-neighborhoods.geojson', name='nhood',
               truth_label='DataSF Analysis Neighborhoods (41, official; copied from cadmus/data/neighborhoods.geojson)'),
    'vancouver': dict(extract=f'data/vancouver/overture-place-{RELEASE}.parquet',
                      truth=f'data/reference/vancouver-overture-macrohood-{RELEASE}.geojson', name='name',
                      truth_label='Overture macrohoods inside the Vancouver locality (22; provisional, names equal the City\'s 22 local areas)'),
    'chicago': dict(extract=f'data/chicago/overture-place-{RELEASE}.parquet',
                    truth=f'data/reference/chicago-overture-macrohood-{RELEASE}.geojson', name='name',
                    truth_label='Overture macrohoods inside the Chicago locality (73 of the 77 community areas; provisional)'),
    'toronto': dict(extract=f'data/toronto/overture-place-{RELEASE}.parquet',
                    truth=f'data/reference/toronto-overture-neighborhood-{RELEASE}.geojson', name='name',
                    truth_label='Overture neighbourhoods inside the Toronto county polygon (174 vs the City\'s 158; provisional)'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--city', choices=CITIES, default='sf')
    ap.add_argument('--res', type=int, default=9)
    ap.add_argument('--rings', default='0,1,2', help='k-ring smoothing radii to compare')
    ap.add_argument('--out', default=None, help='note path stem; default notes/2026-10-06-<city>-signal-check')
    ap.add_argument('--seeds', type=int, default=20, help='random contiguous partitions per k')
    ap.add_argument('--perms', type=int, default=5, help='name permutations per ring and k')
    args = ap.parse_args()
    rings = [int(r) for r in args.rings.split(',')]
    city = CITIES[args.city]
    name_col = city['name']
    out = ROOT / (args.out or f'notes/2026-10-06-{args.city}-signal-check')

    extract = ROOT / city['extract']
    manifest = verify(extract)
    gt = gpd.read_file(ROOT / city['truth'])
    places = tp.load_places(extract)
    ks = KS + ((len(gt),) if len(gt) not in KS else ())

    cells = tp.city_cells(gt, args.res)
    cl = list(cells['cell'])
    w0 = tp.h3_weights(cells['cell'])
    w = tp.bridge_components(w0, cells)
    n_comp0 = tp.connected_components(w0.sparse, directed=False)[0]
    truth = tp.label_cells_by_centroid(cells, gt, name_col).values
    cell_of, raw_counts = tp.cell_token_counts(places, args.res)
    inside = cell_of.isin(set(cl))
    raw_tokens = np.array([sum(raw_counts.get(c, {}).values()) for c in cl])

    proj = cells.to_crs(cells.estimate_utm_crs())
    XY = StandardScaler().fit_transform(np.c_[proj.centroid.x, proj.centroid.y])
    rng = np.random.default_rng(0)

    rows, labels_out, vocab_n = [], {}, None
    for k in ks:
        lab = tp.ward(cells, w, XY, k); s = tp.score(lab, truth)
        rows.append(dict(ring='-', k=k, method='SCHC Ward: coordinates only', ari=s['ari'], nmi=s['nmi']))
        labels_out[('xy', k)] = lab
        fl = [tp.score(tp.random_contiguous(w, k, rng), truth) for _ in range(args.seeds)]
        rows.append(dict(ring='-', k=k, method=f'floor: random contiguous (mean of {args.seeds})',
                         ari=np.mean([f['ari'] for f in fl]), nmi=np.mean([f['nmi'] for f in fl])))
    feats_by_ring = {}
    for ring in rings:
        feats = tp.build_features(raw_counts, cl, ring=ring)
        feats_by_ring[ring] = feats
        vocab_n = len(feats['vocab'])
        perm_feats = [tp.build_features(tp.permute_counts(raw_counts, cl, rng), cl, ring=ring)['X']
                      for _ in range(args.perms)]
        for k in ks:
            lab = tp.ward(cells, w, feats['X'], k); s = tp.score(lab, truth)
            rows.append(dict(ring=ring, k=k, method='SCHC Ward: names', ari=s['ari'], nmi=s['nmi'],
                             largest=np.bincount(lab).max() / len(cl)))
            labels_out[(ring, k)] = lab
            pn = [tp.score(tp.ward(cells, w, Xp, k), truth) for Xp in perm_feats]
            rows.append(dict(ring=ring, k=k, method=f'null: names dealt to random cells (mean of {args.perms})',
                             ari=np.mean([p['ari'] for p in pn]), nmi=np.mean([p['nmi'] for p in pn])))
            km = tp.kmeans_ceiling(feats['X'], k); s = tp.score(km, truth)
            rows.append(dict(ring=ring, k=k, method='k-means on names, no contiguity', ari=s['ari'], nmi=s['nmi']))
        print(f'ring {ring} done', flush=True)
    table = pd.DataFrame(rows)[['ring', 'k', 'method', 'ari', 'nmi', 'largest']]

    out.parent.mkdir(parents=True, exist_ok=True)
    figdir = out.parent / 'figures'; figdir.mkdir(exist_ok=True)
    stem = f'{out.name}-r{args.res}'
    # map the ring whose names run beats its own permutation null by the most at k=20
    def gap(r):
        t = table[(table.ring == r) & (table.k == 20)]
        return (t[t.method == 'SCHC Ward: names'].ari.iloc[0]
                - t[t.method.str.startswith('null')].ari.iloc[0])
    best_ring = max(rings, key=gap)

    fig, axes = plt.subplots(2, 3, figsize=(15, 11)); axes = axes.ravel()
    gt.plot(ax=axes[0], column=name_col, cmap='tab20', edgecolor='white', linewidth=0.3)
    axes[0].set_title(f'ground truth: {len(gt)} areas')
    for ax, k in zip(axes[1:5], KS):
        cells.assign(r=labels_out[(best_ring, k)]).plot(ax=ax, column='r', cmap='tab20', edgecolor='none')
        gt.boundary.plot(ax=ax, color='black', linewidth=0.4)
        ax.set_title(f'names, ring {best_ring}, SCHC Ward k={k}')
    cells.assign(r=labels_out[('xy', 20)]).plot(ax=axes[5], column='r', cmap='tab20', edgecolor='none')
    gt.boundary.plot(ax=axes[5], color='black', linewidth=0.4)
    axes[5].set_title('coordinates only, SCHC Ward k=20')
    for ax in axes: ax.set_axis_off()
    fig.tight_layout(); fig.savefig(figdir / f'{stem}-maps.png', dpi=110); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 7))
    cells.assign(n=np.log1p(raw_tokens)).plot(ax=ax, column='n', cmap='viridis', legend=True)
    gt.boundary.plot(ax=ax, color='white', linewidth=0.3); ax.set_axis_off()
    ax.set_title('log(1 + name tokens per cell), unsmoothed')
    fig.tight_layout(); fig.savefig(figdir / f'{stem}-density.png', dpi=110); plt.close(fig)

    fb = feats_by_ring[best_ring]
    top_tokens = tp.region_top_tokens(fb['M'], fb['vocab'], labels_out[(best_ring, 20)])
    q = np.percentile(raw_tokens, [10, 25, 50, 75, 90])
    md = [f'# {args.city} signal check, H3 res {args.res}', '',
          f'Date: 2026-10-06. Places: Overture {manifest["release"]}, {manifest["rows"]} rows, '
          f'sha256 {manifest["sha256"][:12]}…; {len(places)} with a primary name, {int(inside.sum())} inside the city cells.',
          f'Ground truth: {city["truth_label"]}.',
          f'Cells: {len(cells)} H3-{args.res} cells (centroid inside the union of the {len(gt)} polygons), '
          f'{n_comp0} graph component(s) before bridging; {int((raw_tokens > 0).sum())} cells with at least one token; '
          f'tokens per cell p10/p25/p50/p75/p90 = {"/".join(str(int(v)) for v in q)}.',
          f'Features: {vocab_n} tokens with cell-df in [5, 20% of cells] on unsmoothed counts; counts summed over the '
          'k-ring (`ring`); sqrt(tf)·idf, L2 per cell, truncated SVD to 30. One token per distinct name per cell.',
          '', f'## Agreement with the {len(gt)} areas', '',
          'ARI/NMI over all cells (ground truth = polygon containing the cell centroid). `largest` is the share of cells in the biggest region.', '']
    md.append(table.to_markdown(index=False, floatfmt='.3f'))
    md += ['', f'## Lifted tokens per region, names ring {best_ring}, k=20', '']
    md += [f'- region {r}: ' + ', '.join(ts) for r, ts in top_tokens.items()]
    md += ['', f'Maps: `figures/{stem}-maps.png`, `figures/{stem}-density.png`.']
    note = Path(f'{out}-r{args.res}.md')
    text = '\n'.join(md) + '\n'
    if note.exists() and '## Reading' in note.read_text():
        # keep the hand-written reading of a previous run; everything else is regenerated
        prev = note.read_text()
        reading = prev[prev.index('## Reading'):prev.index('## Agreement')]
        text = text.replace('## Agreement', reading + '## Agreement', 1)
    note.write_text(text)
    table.to_csv(f'{out}-r{args.res}.csv', index=False)
    print(table.to_string(index=False, float_format=lambda v: f'{v:.3f}'))


if __name__ == '__main__':
    main()
