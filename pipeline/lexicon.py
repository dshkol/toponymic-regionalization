"""Typed toponym lexicon for one city.

Offline, built once per city from the Overture place extract on H3 cells. Both
projects read the result: here the lexicon decides which tokens enter the area
feature channel; in cadmus it is the specificity prior and geographic-term filter
its ranking trial asked for ("precomputed term specificity features").

Per phrase (1-3-gram from names.phrases), the table carries:

support        units citywide under the cadmus cap (min names, sites, identities)
cells          number of cells with at least one unit
spread         share of all sites citywide that carry the phrase
locality       cadmus's smoothed log rate ratio, inside vs rest of city, taken
               over the best H3 disk of radius k in SCALES (k=1: 7 cells, about
               0.7 km² at res 9) that holds at least MIN_SUPPORT units. Fixed
               zone sizes, so the number is comparable across phrases and
               cities; locality_k records which radius won.
morans_i       Moran's I of per-cell units over H3 first-ring contiguity
top_share      share of units in the top 5% of cells by units
sd_km          standard distance of the phrase's sites, in km
brand_share    share of records carrying a declared Overture brand
landmark_share share of records in landmark taxonomy groups or categories
is_street      phrase equals a transportation segment name with generic words removed
is_division    same, against division-area names
class          brand, generic, division, street, mixed, landmark, point, area (rule in classify)

The class rule is a first cut to review against the top-200 list, not a result.
"""
import json
import math
import re
from collections import defaultdict

import h3
import numpy as np
import pyarrow.parquet as pq
from libpysal.weights import W

from names import MIN_SUPPORT, STOP, Support, log_ratio, normalize, phrases

# Overture taxonomy groups and categories that name a thing people refer to by
# position (a park, a hill, a station, a campus), rather than a business.
LANDMARK_GROUPS = {'geographic_entities', 'cultural_and_historic'}
LANDMARK_CATEGORIES = {'park', 'historic_site', 'landmark_and_historical_building', 'monument',
                       'train_station', 'light_rail_station', 'metro_station', 'bus_station',
                       'university', 'college_university', 'school', 'high_school', 'stadium_arena',
                       'hospital', 'beach', 'lake', 'mountain', 'plaza', 'public_plaza', 'zoo',
                       'museum', 'library', 'airport', 'pier', 'marina', 'cemetery', 'bridge'}

GENERIC_LOCALITY = 1.0   # best-disk rate under e times the city rate: not a place term
SCALES = (1,)            # H3 grid_disk radii the locality ratio is taken over; (1, 2) was tried,
                         # see the shared-layer note: +2 Chicago polygons, +114 SF first names
SCALE_SUPPORT = {1: 0, 2: 1}  # extra units a disk needs over MIN_SUPPORT: a wider disk must hold more
GENERIC_SD_KM = 3.0      # standard distance of a neighbourhood-scale term is well under this
BRAND_SHARE = 0.25       # Overture declares a brand on only part of a chain's records
CHAIN_RATIO = 0.2        # units / records: identical names repeated collapse under the cap
MAJORITY = 0.5


def h3_weights(cells):
    idx = {c: i for i, c in enumerate(cells)}
    neighbors = {i: [idx[n] for n in h3.grid_ring(c, 1) if n in idx] for c, i in idx.items()}
    return W(neighbors, silence_warnings=True)


def morans_i(x, Wr, s0):
    """Moran's I with a row-standardized sparse W, the same number esda.Moran gives
    (checked on SF to 1e-12), without esda's per-call overhead; the per-phrase loop
    over tens of thousands of phrases needs it to be cheap."""
    z = x - x.mean()
    zz = float(z @ z)
    if zz == 0:
        return float('nan')
    return float(len(z) / s0 * (z @ (Wr @ z)) / zz)


def strip_generic(name):
    """'Valencia Street' -> 'valencia'; used to match phrases to street and division names."""
    return ' '.join(t for t in normalize(name).split() if t not in STOP and not t.isdigit())


ROAD_CLASSES = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential',
                'unclassified', 'living_street', 'unknown'}
# Division subtypes that name places people live in or refer to, not jurisdictions.
AREA_SUBTYPES = {'neighborhood', 'macrohood', 'microhood', 'locality'}


def _names(table, keep):
    out = set()
    for row in table.to_pylist():
        n = (row.get('names') or {}).get('primary')
        if n and keep(row):
            out.add(strip_generic(n))
    out.discard('')
    return out


DIRECTIONS = {'north', 'south', 'east', 'west', 'n', 's', 'e', 'w', 'nw', 'ne', 'sw', 'se'}


def street_names(segment_path):
    """Stripped names of drivable roads: 'Valencia Street' -> 'valencia'. Footways,
    steps, paths and service ways are left out; their names repeat the road's.
    A leading direction is also dropped ('North Western Avenue' -> 'western'),
    since Chicago and Toronto prefix most roads that way and business names do not."""
    if segment_path is None or not segment_path.exists():
        return set()
    t = pq.read_table(segment_path, columns=['subtype', 'class', 'names'])
    base = _names(t, lambda r: r['subtype'] == 'road' and r['class'] in ROAD_CLASSES)
    out = set(base)
    for n in base:
        toks = n.split()
        if len(toks) > 1 and toks[0] in DIRECTIONS:
            out.add(' '.join(toks[1:]))
    return out


def division_names(division_path, reference_names=()):
    """Stripped names of Overture neighbourhood-type divisions plus the city's
    ground-truth polygon names when supplied. Counties, regions and countries are
    not place terms for this purpose."""
    out = set()
    for n in reference_names:
        out |= name_parts(n)
    if division_path is not None and division_path.exists():
        t = pq.read_table(division_path, columns=['subtype', 'names'])
        for n in _names(t, lambda r: r['subtype'] in AREA_SUBTYPES):
            out |= name_parts(n)
    out.discard('')
    return out


def name_parts(name):
    """'Castro/Upper Market' -> {'castro upper', 'castro', 'upper'} (market is a stopword).
    Official polygon names often join two places ('Kensington-Cedar Cottage',
    'Oceanview/Merced/Ingleside'); each part is a term, and so is the whole."""
    parts = {strip_generic(name)}
    for piece in re.split(r'\s*[/,]\s*|\s*-\s*|—|–', name):
        parts.add(strip_generic(piece))
    parts.discard('')
    return parts


def _sd_km(latlngs):
    pts = np.asarray(latlngs)
    lat0 = math.radians(pts[:, 0].mean())
    dx = (pts[:, 1] - pts[:, 1].mean()) * 111.32 * math.cos(lat0)
    dy = (pts[:, 0] - pts[:, 0].mean()) * 110.57
    return float(math.sqrt((dx ** 2 + dy ** 2).mean()))


def build(places, cells, street_names=frozenset(), division_names=frozenset(),
          min_support=MIN_SUPPORT):
    """Return (rows, cell_units): the lexicon, and phrase -> {cell: units}."""
    cell_set = set(cells)
    places = [p for p in places if p.cell in cell_set]
    by_phrase_cell = defaultdict(lambda: defaultdict(Support))
    citywide = defaultdict(Support)
    branded = defaultdict(int)
    landmark = defaultdict(int)
    sites_by_cell = defaultdict(set)
    all_sites = set()
    for p in places:
        r = p.record
        key = f'{r.x:.5f},{r.y:.5f}'
        sites_by_cell[p.cell].add(key)
        all_sites.add(key)
        is_landmark = p.group in LANDMARK_GROUPS or p.category in LANDMARK_CATEGORIES
        # A phrase is brand evidence when it is part of the declared brand's own
        # name, not merely when it appears in a branded record ('Tim Hortons
        # Davie St' must not make 'davie' a brand).
        brand_phrases = phrases(r.brand) if r.brand else ()
        for ph in phrases(r.name):
            by_phrase_cell[ph][p.cell].add(r)
            citywide[ph].add(r)
            branded[ph] += ph in brand_phrases
            landmark[ph] += is_landmark
    n_sites = len(all_sites)
    w = h3_weights(cells)
    w.transform = 'r'
    Wr = w.sparse.tocsr()
    s0 = Wr.sum()
    cell_index = {c: i for i, c in enumerate(cells)}
    cell_xy = {c: h3.cell_to_latlng(c) for c in cells}
    # One disk per scale: the res-8 check showed the width of the disk matters more
    # than the cell size, so the ratio is taken at each scale and the best kept.
    disks = {k: {c: [n for n in h3.grid_disk(c, k) if n in cell_set] for c in cells} for k in SCALES}
    disk_sites = {k: {c: sum(len(sites_by_cell[n]) for n in disks[k][c]) for c in cells} for k in SCALES}
    rows, cell_units = [], {}
    for ph, sup in citywide.items():
        if sup.units < min_support:
            continue
        units = {c: s.units for c, s in by_phrase_cell[ph].items() if s.units > 0}
        total = sum(units.values())
        vec = np.zeros(len(cells))
        for c, u in units.items():
            vec[cell_index[c]] = u
        mi = morans_i(vec, Wr, s0)
        # Best disk with enough units at any scale: cadmus's inside-vs-rest ratio.
        best, best_k = -math.inf, 0
        for k in SCALES:
            for c in units:
                du = sum(units.get(n, 0) for n in disks[k][c])
                # Three units in nineteen cells is a coincidence (first names,
                # trades); the wider disk has to earn the ratio with more units.
                if du < min_support + SCALE_SUPPORT[k]:
                    continue
                lr = log_ratio(du, disk_sites[k][c], total - du, n_sites - disk_sites[k][c])
                if lr > best:
                    best, best_k = lr, k
        if best == -math.inf:
            best = float('nan')
        k = max(1, math.ceil(0.05 * len(cells)))
        top_share = float(np.sort(vec)[::-1][:k].sum() / total)
        row = {'phrase': ph, 'support': sup.units, 'records': sup.records, 'cells': len(units),
               'spread': len(sup.sites) / n_sites, 'locality': best, 'locality_k': best_k, 'morans_i': mi,
               'top_share': top_share,
               'sd_km': _sd_km([cell_xy[c] for c in units for _ in range(units[c])]),
               'brand_share': branded[ph] / sup.records,
               'landmark_share': landmark[ph] / sup.records,
               'is_street': ph in street_names, 'is_division': ph in division_names,
               'examples': sup.examples[:3]}
        row['class'] = classify(row)
        rows.append(row)
        cell_units[ph] = units
    rows.sort(key=lambda r: (-(0 if math.isnan(r['locality']) else r['locality']) * math.log1p(r['support']),
                             r['phrase']))
    return rows, cell_units


def classify(r):
    """First-cut class. Order matters; each rule is a hypothesis to check on the top-200.

    brand     a quarter or more of records carry a declared brand, or the support
              cap collapses the records (identical names repeated: a chain)
    generic   no disk reaches MIN_SUPPORT units, the best disk's rate is under e
              times the city rate, or the sites spread at city scale (standard
              distance over GENERIC_SD_KM): the phrase follows commerce, not place
    mixed     both a division and a street carry the name (Mission, Valencia-type cases)
    division  matches a division-area name
    street    matches a transportation segment name
    landmark  most records are landmark-category places
    point     clustered but in one cell only: a single site or block, not an area
    area      clustered, local, none of the above: a candidate vernacular area term
    """
    if r['records'] >= 10 and (r['brand_share'] >= BRAND_SHARE or r['support'] / r['records'] <= CHAIN_RATIO):
        return 'brand'
    if math.isnan(r['locality']) or r['locality'] < GENERIC_LOCALITY or r['sd_km'] > GENERIC_SD_KM:
        return 'generic'
    if r['is_division'] and r['is_street']:
        return 'mixed'
    if r['is_division']:
        return 'division'
    if r['is_street']:
        return 'street'
    if r['landmark_share'] >= MAJORITY:
        return 'landmark'
    if r['cells'] < 2:
        return 'point'
    return 'area'


def write(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
