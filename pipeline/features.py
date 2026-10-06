"""Cell-by-term feature matrix from a city's lexicon, for the regionalization step.

This is the point where the lexicon's class column does its work: which terms
enter the area channel. The default keeps area, division and mixed terms and
leaves streets, landmarks, points, brands and generics out. Pass other classes
to test the hypothesis that streets pull the clustering toward corridors.

    from features import matrix
    cells, terms, X = matrix('sf', classes=('area', 'division', 'mixed'), top=200)

X is cells x terms of support units. `clr=True` returns the centred log-ratio of
the per-cell composition with a pseudo-count, the treatment HANDOFF.md asks for;
empty cells stay all-zero so the graph keeps them as territory.
"""
import json
from pathlib import Path

import numpy as np

from fetch_overture import RELEASE

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLASSES = ('area', 'division', 'mixed')


def load_lexicon(city, release=RELEASE):
    stem = str(ROOT / 'data' / 'lexicon' / f'{city}-{release}')
    rows = [json.loads(l) for l in open(stem + '.jsonl')]
    units = {}
    for l in open(stem + '.cells.jsonl'):
        r = json.loads(l)
        units[r['phrase']] = r['cells']
    return rows, units


def select_terms(rows, classes=DEFAULT_CLASSES, top=None, longest_only=True):
    """Terms of the given classes, ranked by locality * log1p(support).

    With longest_only, a term contained in a selected longer term is dropped
    ('noe' under 'noe valley'), the rule cadmus uses when it picks lexical evidence.
    """
    chosen = []
    for r in rows:  # rows arrive sorted by the lexicon's ranking
        if r['class'] not in classes:
            continue
        if longest_only and any(f' {r["phrase"]} ' in f' {c} ' for c in chosen):
            continue
        chosen.append(r['phrase'])
        if top and len(chosen) >= top:
            break
    return chosen


def matrix(city, classes=DEFAULT_CLASSES, top=200, clr=False, pseudo=0.5, release=RELEASE):
    rows, units = load_lexicon(city, release)
    terms = select_terms(rows, classes, top)
    cells = sorted({c for t in terms for c in units[t]})
    ci = {c: i for i, c in enumerate(cells)}
    X = np.zeros((len(cells), len(terms)))
    for j, t in enumerate(terms):
        for c, u in units[t].items():
            X[ci[c], j] = u
    if clr:
        X = clr_transform(X, pseudo)
    return cells, terms, X


def clr_transform(X, pseudo=0.5):
    """Centred log-ratio per row with a pseudo-count. All-zero rows stay zero."""
    out = np.zeros_like(X, dtype=float)
    nonempty = X.sum(axis=1) > 0
    Z = X[nonempty] + pseudo
    L = np.log(Z / Z.sum(axis=1, keepdims=True))
    out[nonempty] = L - L.mean(axis=1, keepdims=True)
    return out
