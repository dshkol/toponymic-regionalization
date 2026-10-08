"""Rank-size of storefronts per street: Zipf, Pareto, or lognormal?

Fits the tail of storefronts-per-street with the discrete power-law method of
Clauset, Shalizi and Newman (2009, SIAM Review 51:661), via the `powerlaw`
package (Alstott, Bullmore and Plenz 2014, PLoS ONE 9:e85777), and compares it
with a lognormal and a truncated power law by likelihood ratio. Street length
gets the same treatment, since a heavy tail in storefronts could be inherited
from a heavy tail in how long streets are.

    python3 side/street_rank_size.py     # writes side/out/street-rank-size.json
"""
import json
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import powerlaw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from street_dominance import CITIES, OUT, STOREFRONT, run

warnings.filterwarnings('ignore')


def fit(values, discrete):
    f = powerlaw.Fit(values, discrete=discrete, verbose=False)
    out = {'alpha': f.power_law.alpha, 'xmin': float(f.power_law.xmin),
           'n_tail': int(np.sum(np.asarray(values) >= f.power_law.xmin)), 'n': len(values),
           'zipf_exponent': 1 / (f.power_law.alpha - 1)}
    for alt in ('lognormal', 'truncated_power_law', 'exponential'):
        R, p = f.distribution_compare('power_law', alt, normalized_ratio=True)
        out[f'vs_{alt}'] = {'R': float(R), 'p': float(p)}  # R > 0 favours the power law
    return out


def rank_slope(values, top=50):
    """Least-squares slope of log size on log rank over the top streets: -1 is Zipf."""
    v = np.sort(values)[::-1][:top]
    r = np.arange(1, len(v) + 1)
    return float(np.polyfit(np.log(r), np.log(v), 1)[0])


if __name__ == '__main__':
    results, sizes = {}, {}
    for city in CITIES:
        _, _, (area, length, arterial, lines, rows) = run(city)
        counts = Counter(r[2] for r in rows if STOREFRONT.search(r[3]) and r[2] in length)
        c = np.array(list(counts.values()))
        L = np.array([v for v in length.values() if v > 0]) / 1e3
        results[city] = {'storefronts': fit(c, True), 'length_km': fit(L, False),
                         'rank_slope_top50': rank_slope(c), 'length_rank_slope_top50': rank_slope(L)}
        sizes[city] = {'storefronts': sorted(c.tolist(), reverse=True), 'length_km': sorted(L.tolist(), reverse=True)}
        s = results[city]['storefronts']
        print(city, f"alpha {s['alpha']:.2f} zipf {s['zipf_exponent']:.2f} xmin {s['xmin']:.0f} tail {s['n_tail']}/{s['n']}",
              {k: (round(v['R'], 2), round(v['p'], 3)) for k, v in s.items() if k.startswith('vs_')},
              'rank slope', round(results[city]['rank_slope_top50'], 2),
              '| length alpha', round(results[city]['length_km']['alpha'], 2),
              'lognormal R', round(results[city]['length_km']['vs_lognormal']['R'], 2),
              'rank slope', round(results[city]['length_rank_slope_top50'], 2))
    (OUT / 'street-rank-size.json').write_text(json.dumps({'fits': results, 'sizes': sizes}))
