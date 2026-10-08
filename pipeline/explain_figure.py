"""Three-panel San Francisco explainer: names localize (A), do not delimit (B), and ARI rewards compact
blobs (C). Writes notes/figures/2026-10-08-sf-localize-not-delimit.png.

    python pipeline/explain_figure.py
"""
import numpy as np, geopandas as gpd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects
from matplotlib.colors import to_rgb
from sklearn.preprocessing import StandardScaler
import fields as nf, toponymic as tp
from run_city import CITIES, ROOT
city = CITIES['sf']; gt = gpd.read_file(ROOT / city['truth']); places = tp.load_places(ROOT / city['extract'])
cells = tp.city_cells(gt, 9); cl = list(cells['cell']); n = len(cl)
w = tp.h3_weights(cells['cell']); wb = tp.bridge_components(w, cells)
_, raw = tp.cell_token_counts(places, 9)
truth = tp.label_cells_by_centroid(cells, gt, 'nhood').values
vocab, df, M = nf.count_matrix(raw, cl)
vi = {t: i for i, t in enumerate(vocab)}
proj = cells.to_crs(cells.estimate_utm_crs()); gtp = gt.to_crs(proj.crs)

fig, axes = plt.subplots(1, 3, figsize=(18, 7.2))
# Panel A: where three toponyms are used (unsmoothed counts per cell)
ax = axes[0]
proj.plot(ax=ax, color='#eeece6', edgecolor='none')
cols = {'noe': '#2a78d6', 'castro': '#eb6834', 'sunset': '#1baf7a', 'bayview': '#4a3aa7', 'marina': '#e34948', 'richmond': '#eda100'}
for tok, col in cols.items():
    v = M[:, vi[tok]].toarray().ravel()
    sel = v > 0
    rgb = np.array(to_rgb(col))
    alpha = np.clip(0.35 + 0.65 * v[sel] / v.max(), 0, 1)
    proj[sel].plot(ax=ax, color=[(*rgb, a) for a in alpha], edgecolor='none')
gtp.boundary.plot(ax=ax, color='#1d1c19', linewidth=0.6)
for tok, col in cols.items():
    v = M[:, vi[tok]].toarray().ravel(); c = proj[v > 0].geometry.centroid
    ax.text(np.median(c.x), np.median(c.y), tok, color=col, fontsize=12, fontweight='bold', ha='center',
            path_effects=[matplotlib.patheffects.withStroke(linewidth=3, foreground='white')])
ax.set_title('A. Names localize\ncoloured: cells with a business whose name contains the word\nblack: the 41 official areas', fontsize=11, loc='left')

# Panel B: where name features change between neighbouring cells, vs official boundaries
ax = axes[1]
X = tp.build_features(raw, cl, ring=1)['X']
A = w.sparse.tocoo(); edges = np.array([(i, j) for i, j in zip(A.row, A.col) if i < j])
d = np.linalg.norm(X[edges[:, 0]] - X[edges[:, 1]], axis=1)
tokens = np.array([sum(raw.get(c, {}).values()) for c in cl]); ok = (tokens[edges[:, 0]] >= 3) & (tokens[edges[:, 1]] >= 3)
proj.plot(ax=ax, color='#eeece6', edgecolor='none')
cen = proj.geometry.centroid; cx, cy = cen.x.values, cen.y.values
thr = np.quantile(d[ok], 0.8)
hot = ok & (d >= thr)
for i, j in edges[hot]:  # the shared hex side: perpendicular to the centroid line at its midpoint
    mx, my = (cx[i] + cx[j]) / 2, (cy[i] + cy[j]) / 2
    dx, dy = cx[j] - cx[i], cy[j] - cy[i]; L = np.hypot(dx, dy); px, py = -dy / L, dx / L; h = L / (2 * np.sqrt(3))
    ax.plot([mx - px * h, mx + px * h], [my - py * h, my + py * h], color='#e34948', linewidth=2.5, alpha=0.9, solid_capstyle='round')
gtp.boundary.plot(ax=ax, color='#1d1c19', linewidth=0.9)
ax.set_title('B. Names do not delimit\nred: the 20% of cell edges where the name features change most\nblack: official boundaries. They do not line up.', fontsize=11, loc='left')

# Panel C: a random contiguous partition scores like the names partition
ax = axes[2]
rng = np.random.default_rng(3)
lab_names = tp.ward(cells, wb, X, 41)
lab_rand = tp.random_contiguous(wb, 41, rng)
from sklearn.metrics import adjusted_rand_score
a1 = adjusted_rand_score(truth, lab_names); a2 = adjusted_rand_score(truth, lab_rand)
palette = plt.get_cmap('tab20')
sub = fig.add_axes([0.67, 0.06, 0.16, 0.7]); sub2 = fig.add_axes([0.835, 0.06, 0.16, 0.7])
ax.axis('off')
for a, lab, ttl in ((sub, lab_names, f'names, Ward k=41\nARI {a1:.2f}'), (sub2, lab_rand, f'random contiguous k=41\nARI {a2:.2f}')):
    proj.plot(ax=a, color=[palette(l % 20) for l in lab], edgecolor='none')
    gtp.boundary.plot(ax=a, color='#1d1c19', linewidth=0.5)
    a.set_title(ttl, fontsize=10); a.set_axis_off()
ax.set_title('C. The agreement score rewards compact blobs\nany contiguous partition into 41 pieces\nscores about the same as the names one', fontsize=11, loc='left')
for a in axes: a.set_axis_off()
fig.suptitle('San Francisco, H3-9 cells, Overture place names: what the names do and do not tell you', fontsize=13, x=0.01, ha='left')
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = ROOT / 'notes/figures/2026-10-08-sf-localize-not-delimit.png'
fig.savefig(out, dpi=130); print('wrote', out, a1, a2)
