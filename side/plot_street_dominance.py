"""Figure for side/street_dominance.py: four maps and two comparison panels.

    python3 side/plot_street_dominance.py   # writes side/out/street-dominance.png
"""
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from street_dominance import CITIES, OUT, STOREFRONT, run

NAMES = {'sf': 'San Francisco', 'vancouver': 'Vancouver', 'chicago': 'Chicago', 'toronto': 'Toronto'}
COLOR = {'sf': '#2a78d6', 'vancouver': '#eb6834', 'chicago': '#1baf7a', 'toronto': '#c98500'}
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#d9d8d3'
plt.rcParams.update({'font.size': 10, 'text.color': INK, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.edgecolor': GRID})


def lines_xy(geoms):
    for g in geoms:
        for part in getattr(g, 'geoms', [g]):
            if part.geom_type == 'LineString':
                yield np.asarray(part.coords)


fig = plt.figure(figsize=(16, 11.5), facecolor='#fcfcfb')
gs = fig.add_gridspec(2, 4, height_ratios=[1.25, 1], hspace=0.02, wspace=0.18)
results, curves = {}, {}
for i, city in enumerate(CITIES):
    res, cur, (area, length, arterial, lines, rows) = run(city)
    results[city], curves[city] = res, cur['storefront']
    s = res['storefront']
    ax = fig.add_subplot(gs[0, i])
    top = s['top10_streets']
    for n, gs_ in lines.items():
        if n in top:
            continue
        for xy in lines_xy(gs_):
            ax.plot(xy[:, 0], xy[:, 1], color=GRID, lw=0.25, zorder=1)
    pts = np.array([(r[0], r[1]) for r in rows if STOREFRONT.search(r[3]) and r[2] in length])
    ax.scatter(pts[:, 0], pts[:, 1], s=0.4, color=MUTED, alpha=0.35, lw=0, zorder=2)
    for rank, n in enumerate(top):
        for xy in lines_xy(lines[n]):
            ax.plot(xy[:, 0], xy[:, 1], color=COLOR[city], lw=2.2 if rank < 5 else 1.2,
                    alpha=1 if rank < 5 else 0.6, zorder=3, solid_capstyle='round')
    ax.set_aspect('equal'); ax.axis('off'); ax.set_anchor('N')
    x0, y0, x1, y1 = area.bounds
    ax.plot([x0, x0 + 5000], [y0 - 0.03 * (y1 - y0)] * 2, color=INK, lw=1.5)
    ax.text(x0, y0 - 0.06 * (y1 - y0), '5 km', va='top', fontsize=8, color=MUTED)
    ax.set_title(f"{NAMES[city]}\n\n\n\n", loc='left', fontsize=13, fontweight='bold')
    ax.text(0, 1.02, f"Top 5 streets hold {s['top5_share']:.0%} of storefronts\n"
            f"on {s['top5_length_share']:.1%} of named street length.\n"
            + ', '.join(n.title() for n in top[:3]) + ',\n' + ', '.join(n.title() for n in top[3:5]), transform=ax.transAxes,
            fontsize=8.5, color=MUTED, va='bottom', linespacing=1.4)

# Panel A: concentration against street length.
ax = fig.add_subplot(gs[1, 0:2])
for city in CITIES:
    x, y = curves[city]
    s = results[city]['storefront']
    ax.plot(x * 100, y * 100, color=COLOR[city], lw=2,
            label=f"{NAMES[city]}: half on {s['length_share_for_half']:.1%} of length")
ax.plot([0, 100], [0, 100], color=MUTED, lw=1, ls=(0, (3, 3)))
ax.text(32, 10, 'storefronts spread evenly\nalong every street', color=MUTED, fontsize=8.5)
ax.legend(loc='upper right', bbox_to_anchor=(1, 0.8), frameon=False, fontsize=9)
ax.set_xlim(0, 50); ax.set_ylim(0, 100)
ax.set_xlabel('% of named street length (streets ranked by storefronts per km)')
ax.set_ylabel('% of storefronts')
ax.set_title('A. Every city piles storefronts onto a sliver of its streets',
             loc='left', fontsize=12, fontweight='bold', pad=22)
ax.text(0, 1.03, 'This part is trivial: the four curves nearly coincide, far above the even-spread line',
        transform=ax.transAxes, fontsize=8.5, color=MUTED, va='bottom')
ax.grid(color=GRID, lw=0.5); ax.spines[['top', 'right']].set_visible(False)

# Panel B: long streets, share of length vs share of storefronts.
ax = fig.add_subplot(gs[1, 2:4])
order = list(CITIES)
for j, city in enumerate(order):
    s = results[city]['storefront']
    a, b = s['long_street_length_share'] * 100, s['long_street_share'] * 100
    ax.plot([a, b], [j, j], color=GRID, lw=3, zorder=1, solid_capstyle='round')
    ax.scatter([a], [j], s=60, facecolor='#fcfcfb', edgecolor=COLOR[city], lw=2, zorder=2)
    ax.scatter([b], [j], s=60, color=COLOR[city], zorder=3)
    ax.text(max(a, b) + 2, j, f"{b / a:.1f}x  ({s['long_streets']} long streets)", va='center',
            fontsize=9, color=INK)
ax.set_yticks(range(len(order)), [NAMES[c] for c in order]); ax.invert_yaxis()
ax.set_xlim(0, 100); ax.set_ylim(len(order) - 0.4, -0.9)
ax.scatter([], [], s=60, facecolor='#fcfcfb', edgecolor=MUTED, lw=2, label='share of street length')
ax.scatter([], [], s=60, color=MUTED, label='share of storefronts')
ax.legend(loc='lower right', frameon=False, fontsize=9)
ax.set_xlabel('% on streets that reach at least halfway across the city')
ax.set_title('B. Only Toronto (and partly SF) is ruled by a few long streets',
             loc='left', fontsize=12, fontweight='bold', pad=22)
ax.text(0, 1.03, 'In grid cities nearly every street is long, so long streets get storefronts in '
        'proportion to their length', transform=ax.transAxes, fontsize=8.5, color=MUTED, va='bottom')
ax.grid(axis='x', color=GRID, lw=0.5); ax.spines[['top', 'right', 'left']].set_visible(False)
ax.tick_params(axis='y', length=0)

fig.text(0.125, 0.035, 'Storefronts: Overture places 2026-08-19.0, confidence ≥ 0.5, food, drink, retail and '
         'personal-service categories, placed on the street named in their own address. Streets: Overture '
         'road segments inside city limits, one street per name with directions dropped (N/S Western Ave is one '
         'street;\nQueen St W/E is one; Bloor and Danforth are two). Top 10 streets per city drawn in colour, '
         'top 5 thicker; grey dots are storefronts.', fontsize=8, color=MUTED)
OUT.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT / 'street-dominance.png', dpi=130, bbox_inches='tight', facecolor=fig.get_facecolor())
