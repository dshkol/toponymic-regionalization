"""Rank-size figure for side/street_rank_size.py.

    python3 side/plot_rank_size.py   # writes side/out/street-rank-size.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent / 'out'
d = json.loads((OUT / 'street-rank-size.json').read_text())
NAMES = {'sf': 'San Francisco', 'vancouver': 'Vancouver', 'chicago': 'Chicago', 'toronto': 'Toronto'}
COLOR = {'sf': '#2a78d6', 'vancouver': '#eb6834', 'chicago': '#1baf7a', 'toronto': '#c98500'}
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#d9d8d3'
plt.rcParams.update({'font.size': 10, 'text.color': INK, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.edgecolor': GRID})

fig, ax = plt.subplots(figsize=(8.5, 6.2), facecolor='#fcfcfb')
ax.set_facecolor('#fcfcfb')
for city in NAMES:
    v = np.array(d['sizes'][city]['storefronts'], float)
    share = v / v.sum() * 100
    r = np.arange(1, len(v) + 1)
    f = d['fits'][city]
    ax.loglog(r, share, color=COLOR[city], lw=2,
              label=f"{NAMES[city]}: slope {f['rank_slope_top50']:.2f} over the top 50")
r = np.array([1, 1000])
ax.loglog(r, 6 * r ** -1.0, color=MUTED, lw=1, ls=(0, (3, 3)))
ax.text(30, 6 / 30 * 0.55, 'Zipf (slope −1)', color=MUTED, fontsize=9, rotation=-33)
ax.set_xlabel('Street rank by storefront count (log)')
ax.set_ylabel('% of the city\'s storefronts on that street (log)')
ax.set_title('Heavy-tailed, but bending: lognormal, not Zipf', loc='left', fontsize=13,
             fontweight='bold', pad=24)
ax.text(0, 1.02, 'Every city falls away from a straight line at both ends; a lognormal beats a '
        'power law in all four (p < 0.01)', transform=ax.transAxes, fontsize=9, color=MUTED, va='bottom')
ax.legend(loc='lower left', frameon=False, fontsize=9)
ax.set_xlim(1, 2000); ax.set_ylim(0.004, 10)
ax.grid(color=GRID, lw=0.5, which='major'); ax.spines[['top', 'right']].set_visible(False)
fig.savefig(OUT / 'street-rank-size.png', dpi=140, bbox_inches='tight', facecolor=fig.get_facecolor())
