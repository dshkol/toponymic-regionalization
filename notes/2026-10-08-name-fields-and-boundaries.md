# 2026-10-08: name fields as features, and whether names change at the boundaries

Scripts: `pipeline/fields.py`, `pipeline/run_fields.py`, `pipeline/boundary_auc.py`,
`pipeline/locality_boundary_auc.py`, `pipeline/fetch_reference.py`. Tables:
`2026-10-08-<city>-name-fields-r9.csv`, `2026-10-08-chicago-name-fields-vernacular-r9.csv`,
`2026-10-08-<city>-boundary-auc-r9.csv`. H3-9, Overture Places 2026-08-19.0, same cells,
tokens and Ward as the 2026-10-06 signal check.

## What was tried

1. **Name fields as features.** Each vocabulary token becomes a kernel density over the
   cells that carry it, with its own bandwidth (median nearest-neighbour distance between
   its cells, clipped to 1–4 cell widths; or a fixed one-cell bandwidth). The field matrix
   replaces the k-ring smoothed counts and goes through the same sqrt·idf, L2, SVD-30 into
   SCHC Ward. Same permutation null (deal the bags of names to random cells, then build
   fields). Ablations: the watershed (every cell takes its strongest idf-weighted field, no
   clustering) and max-p with a tokens-per-region floor on the field features.
2. **Name recovery as a second score.** A region is *named* when one of its top-3 lifted
   tokens (from unsmoothed counts) is a word of the area holding the plurality of its
   cells; an area is *recovered* when some region names it. Computed for every partition,
   including coordinates-only and random ones, so the naming step is held constant.
3. **A second, vernacular ground truth.** The click_that_hood polygon sets, which GitHub
   serves and the city portals do not (`fetch_reference.py`, manifests in
   `data/reference/`): SF 37 (older SF Planning neighbourhoods), Chicago 98 (Zillow-style
   vernacular: Printers Row, Wrigleyville, Sheffield & DePaul), Toronto 140 (the City's
   pre-2021 official set), Vancouver 23 (the 22 local areas plus Stanley Park).
4. **A boundary test that does not depend on k or compactness.** Every pair of adjacent
   cells is an edge; it is a boundary edge when the two centroids fall in different areas.
   The divergence of an edge is the distance between the two cells' feature vectors (the
   matrices Ward clusters on), also at a wider scale between the means of the two sides
   (each cell's ring-2 or ring-3 disk minus the other's). The score is the AUC of that
   divergence for predicting boundary edges, against the official areas, the vernacular
   polygons, random contiguous partitions with the same k, and, as a positive control, the
   boundaries of the Ward partition built on the same features. Edges need at least three
   tokens on both cells (SF 2,750 edges, Vancouver 2,618, Chicago 10,641).

## Results

### Fields as features: equal to their own null

ARI against the official areas (SF 41 DataSF; Chicago 73 Overture macrohoods), one run each,
permutation null averaged over two deals:

| | SF k=20 | SF k=41 | Chicago k=20 | Chicago k=73 |
|---|---|---|---|---|
| names ring 1 (2026-10-06 baseline) | 0.36 | 0.35 | 0.22 | 0.36 |
| its permutation null | 0.25 | 0.29 | 0.04 | 0.11 |
| fields, adaptive bandwidth | 0.36 | 0.33 | 0.29 | **0.47** |
| its permutation null | **0.37** | 0.36 | 0.34 | **0.45** |
| fields, fixed 1 cell | 0.35 | 0.32 | 0.24 | 0.40 |
| coordinates only | 0.44 | 0.35 | 0.32 | 0.39 |
| random contiguous (floor) | 0.31 | 0.34 | 0.28 | 0.40 |

The adaptive fields give the highest ARI of anything so far (Chicago 0.47 at k=73, above
coordinates-only), and their permutation null is the same number. Permuted names have wide
bandwidths, so their fields are smooth, Ward cuts them into compact blobs, and compact blobs
agree with the community areas at 0.45. Narrower bandwidths (0.5, 0.75, 1 cell) in SF behave
like ring 1: 0.32–0.38 against nulls of 0.30–0.37. The watershed gives 107 regions in SF and
258 in Chicago at ARI 0.26 / 0.42; max-p on the fields gives 0.35 (k≈20) and 0.42 (k≈41) in SF
with no floor-specific gain. **The fields idea, done as features into Ward, fails its kill
test**: nothing it adds is distinguishable from smoothing.

### Name recovery: compact partitions are as nameable as name-based ones

Share of regions named by their own lifted tokens, at k = number of areas:

| | SF (41) | Chicago official (73) | Chicago vernacular (98) |
|---|---|---|---|
| names ring 1 | 0.44 | 0.25 | 0.33 |
| fields adaptive | 0.39 | 0.33 | 0.35 |
| coordinates only | 0.44 | 0.33 | 0.38 |
| fields null (names permuted) | 0.33 | 0.33 | 0.38 |
| random contiguous | 0.28 | 0.31 | 0.28 |

At k=20 the fields partition is the most nameable in both cities (SF 0.30 is the exception;
Chicago 0.50 vs 0.35 coordinates, 0.32 null), but single runs at k=20 vary by ±0.1. At the
official k the naming step finds the area's word in any compact region of that size. The
unnamed SF regions are instructive: dogpatch (inside Potrero Hill), cow hollow (Marina),
miraloma (West of Twin Peaks), stonestown / sfsu (Lakeshore), fidi (Financial District/South
Beach): real neighbourhoods the official list spells differently or does not have.

### Chicago against the vernacular polygons

Scoring the same partitions against the 98 Zillow-style polygons instead of the 73 community
areas changes little: ring 1 0.36 → 0.36, fields 0.47 → 0.42, coordinates 0.39 → 0.36, random
contiguous 0.40 → 0.39. The vernacular truth is not the thing that was holding the numbers
down.

### Boundary test: name change across cell edges is at chance

AUC of adjacent-cell divergence for predicting boundary edges (full tables, with the two-sided
ring-2 and ring-3 versions, in the CSVs; those are at or below these numbers everywhere):

| feature | SF official | SF vernacular | SF random | **SF own Ward** | Van. official | Van. random | **Van. own Ward** | Chi. official | Chi. vernacular | Chi. random | **Chi. own Ward** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| names ring 0 | 0.51 | 0.52 | 0.48 | 0.69 | 0.49 | 0.50 | 0.64 | 0.50 | 0.47 | 0.51 | 0.61 |
| names ring 1 | 0.52 | 0.53 | 0.51 | **0.86** | 0.46 | 0.49 | **0.85** | 0.51 | 0.51 | 0.51 | **0.84** |
| fields adaptive | 0.47 | 0.48 | 0.51 | 0.60 | 0.53 | 0.47 | 0.63 | 0.56 | 0.49 | 0.54 | 0.66 |
| fields fixed 1 cell | 0.50 | 0.52 | 0.51 | 0.75 | 0.56 | 0.50 | 0.82 | 0.56 | 0.55 | 0.50 | 0.78 |
| coordinates only | 0.49 | 0.49 | 0.50 | 0.55 | 0.46 | 0.49 | 0.59 | 0.50 | 0.52 | 0.50 | 0.56 |
| permutation nulls | 0.48–0.52 | 0.49–0.53 | | | 0.51–0.55 | | | 0.50–0.54 | 0.50–0.53 | | |

The positive control works: where Ward cut, the features differ (0.6–0.86). Where the official
or vernacular boundaries run, they do not (0.46–0.56, the same as against random contiguous
boundaries and the same as the permutation nulls). The only numbers above 0.53 are the
fixed-bandwidth fields in Vancouver and Chicago (0.56), and their nulls are 0.52–0.55: a
kernel over permuted names still encodes where the businesses are, and the boundaries run
through low-density ground (the density-difference predictor alone scores 0.54 in SF).

Cutting the vocabulary to the typed lexicon's locality classes (area, division, mixed; 594
SF tokens, 416 Vancouver, 99 Chicago) does not change this on the full edge set:
official-boundary AUC 0.50–0.55 in SF, 0.48–0.57 in Vancouver, 0.53–0.54 in Chicago, with
nulls 0.48–0.54 and positive controls 0.79–0.98. The one number above noise is Chicago on the
7% of edges where *both* cells carry an unsmoothed locality token: AUC 0.63 (official) and
0.65 (vernacular) against 0.50 for random boundaries and 0.51 for the null. Where two
neighbouring cells both say which neighbourhood they are in, they disagree more often across
a boundary; that condition holds almost nowhere.

### Resolution 8 (cells of about 1.2 km) does not change the picture

SF: 408 edges, every name feature at or below chance against official and vernacular
boundaries (0.40–0.53; the fields sit at 0.40 because the coarse boundaries run through the
smooth, evidence-poor cells), positive controls 0.61–0.88. Chicago: 1,904 edges, names ring
1 0.58 and fixed fields 0.59 against official boundaries with nulls of 0.55 and 0.56;
coordinates 0.49. Two or three points above a null that is itself above chance, i.e.
density, with a trace of names on top.

## Reading

- The 2026-10-06 ARI numbers are contiguity and compactness. Any smooth feature set, names
  or not, gives Ward a compact partition, and a compact partition at the right k scores
  0.35–0.45 against official areas. Names only showed above their null when the features
  were rough (ring 0, ring 1), and then they lost to coordinates. There is no bandwidth at
  which names beat geometry, because the thing ARI rewards is geometry.
- Names do not delimit. At 350 m cells, the places where the name vocabulary changes between
  neighbours are not the neighbourhood boundaries, official or vernacular, and not when the
  vocabulary is only toponyms. The signal that survives the permutation null on rough
  features comes from cells deep inside areas pulling together, not from edges.
- Names do localize. The lifted tokens name compact regions of neighbourhood size whether
  the regions came from names or from coordinates, and they name real places the official
  lists lack. The vocabulary says *where a name holds*, with soft edges, not *where it stops*.
- So the brief's thesis, regionalize a city from name evidence first, is not supported in
  its boundary form at this scale and with this data. What the data supports is the
  inverse of Cadmus as a coverage problem: fields of where each toponym is used, overlapping,
  with boundaries, if boundaries are wanted, drawn by geometry and named by the fields.

## Caveats

- One Ward run per cell and setting; nulls over two deals, floors over three to five seeds.
  Differences under 0.05 in ARI and under 0.03 in AUC are inside the noise.
- The edge test needs three tokens on both cells, so it ignores the emptiest ground, where
  many official boundaries run (parks, freeways, water). Boundaries that *are* density gaps
  are picked up by the density predictor, not by names; a test on evidence-poor edges would
  need a different design.
- At resolution 8 neighbourhoods are four or five cells across, so the edge test there is
  coarse by construction.
- The Chicago vernacular polygons overlap and leave gaps; cells outside them take the
  nearest polygon. Chicago's official set is still the 73 Overture macrohoods.

## Next

Stop improving the regionalizer until there is a score it can move. Candidates: (1) the
field-coverage framing scored by name recovery at the toponym level (for each lexicon
toponym with a polygon in either ground truth, does its field's support overlap that
polygon more than a permuted field's would); (2) a centre-versus-edge test, whether name
evidence is more concentrated at area centroids than at area edges, which is the
localize-not-delimit claim made testable; (3) street-name change points as a second,
independent boundary signal (DataSF centerlines are on disk for SF).
