# Findings

Running conclusions and parked side-findings. Dated experiment notes sit next to this file.

## 2026-10-06, SF signal check (`2026-10-06-sf-signal-check-r9.md`)

- Place-name tokens on H3-9 cells carry real but weak neighbourhood signal in San
  Francisco: SCHC Ward on names reaches ARI 0.15–0.20 against the 41 DataSF analysis
  neighbourhoods where names dealt to random cells give 0.00, but Ward on coordinates
  alone reaches 0.44 and random contiguous partitions 0.30. Names alone do not beat
  geography on this ground truth at this scale.
- k-ring smoothing of counts inflates agreement through geometry, not names: at ring 2
  the permutation null equals the real run. Always report the permutation null.
- The brief's feature option (a), top locality tokens with a centred log-ratio, fails on
  sparse cells (one giant region). Unit-length sqrt-tf·idf rows reduced by SVD are the
  working default.
- The output regions are nameable from their lifted tokens even at modest ARI, which is
  the property Cadmus needs; ARI against tract aggregations understates it.

- Dropping street-name tokens (DataSF centerline aliases) from the vocabulary does not
  improve agreement and hurts on unsmoothed cells: street names are locational evidence
  for clustering even if they are false positives for naming.

## 2026-10-06, four cities (`2026-10-06-<city>-signal-check-r9.md`)

Same pipeline, same nulls, H3-9. Ground truth is official for SF only; the other three
are Overture divisions standing in (Vancouver 22 = the City's local areas by name;
Chicago 73 of 77 community areas; Toronto 174 vs the City's 158). ARI at k = number of
ground-truth areas, with the 1-ring smoothed names run, its permutation null, and Ward on
coordinates only:

| city | cells | median tokens/cell | names (ring 1) | names null | coordinates only | random contiguous |
|---|---|---|---|---|---|---|
| San Francisco (k=40) | 1,114 | 29 | 0.36 | 0.29 | 0.35 | 0.36 |
| Vancouver (k=22) | 1,273 | 13 | 0.40 | 0.26 | 0.44 | 0.37 |
| Chicago (k=73) | 5,318 | 16 | 0.36 | 0.10 | 0.39 | 0.38 |
| Toronto (k=174) | 5,837 | 12 | 0.27 | 0.18 | 0.29 | 0.32 |

Unsmoothed (ring 0) names score 0.05 to 0.20 everywhere with a null of 0.00 and one
region holding 20 to 75% of the cells; ring 2 smoothing makes the null equal the names run
in every city.

- The pattern holds in all four cities: name tokens carry signal that survives a
  permutation null, but a compact contiguous partition of the city agrees with the
  official areas about as well, and sometimes better. On ARI against official polygons,
  names alone do not beat geography at H3-9.
- The names-minus-null gap grows with city size (Chicago +0.26, Vancouver +0.14, SF
  +0.07 at k=40, Toronto +0.09) because 1-ring smoothing is a smaller share of a bigger
  city; the smoothing, not the names, is what the small cities' numbers mostly measure.
- In every city the lifted tokens per region read as the vernacular neighbourhoods
  (SF: noe/valencia/castro; Vancouver: kitsilano, kerrisdale, marpole; Chicago:
  bronzeville/hyde/kenwood, pilsen/bridgeport/chinatown, wicker/sheffield; Toronto:
  leslieville/greektown/beaches, thorncliffe/leaside), including places with no polygon
  in the official set. Naming the regions is the readout that works; ARI against
  administrative polygons understates it, most of all in Toronto and Chicago, where the
  official names are not what businesses use (see the Cadmus-links naming test).
- Next: max-p with a places-per-region floor on unsmoothed counts, so empty cells are
  absorbed instead of smoothed over; then score each region by name recovery
  (`name_recovery.rank_inside` on the Cadmus-links branch) alongside ARI.

Side-findings parked here:

- DataSF's 41 analysis neighbourhoods include open water and large parks (the Bayview
  polygon extends into the Bay; Golden Gate Park, Presidio and McLaren Park are their own
  units), so cells there are scored against a label with no place names behind it.
- The cloud environment's network policy blocks data.sfgov.org, open.toronto.ca,
  opendata.vancouver.ca, data.cityofchicago.org and the Overture STAC catalog;
  `overturemaps download` fails there. This run reused the cadmus extract (checksum
  verified against its manifest) and the cadmus copy of the DataSF polygons.

## 2026-10-08, name fields and the boundary test (`2026-10-08-name-fields-and-boundaries.md`)

- Name fields (each toponym as its own kernel density, replacing k-ring smoothing) give the
  highest ARI yet (Chicago 0.47 at k=73) and a permutation null of 0.45: smoothing again.
  The idea fails as a feature set for Ward.
- The ARI results of 2026-10-06 are contiguity and compactness. Random contiguous
  partitions reach 0.34–0.40 at the official k; any smooth feature set gives Ward a compact
  partition that scores the same. Names only rise above their null when the features are
  rough, and then they lose to coordinates.
- A boundary test with a positive control (AUC of adjacent-cell feature divergence for
  predicting boundary edges) is at chance for official and vernacular boundaries in SF,
  Vancouver and Chicago (0.46–0.56, nulls 0.48–0.55, random boundaries 0.47–0.54) while
  Ward's own cuts score 0.6–0.86. Same with the vocabulary cut to the lexicon's locality
  classes, and at resolution 8. The exception is small: Chicago edges where both cells
  carry an unsmoothed toponym (7% of edges) score 0.63.
- Names localize but do not delimit at this scale and with this data. The vernacular
  polygon sets (click_that_hood via GitHub, with manifests) score the same as the official
  ones, so the ground truth was not what held the numbers down.
- Compact regions of neighbourhood size are as nameable from their lifted tokens whether
  they came from names or from coordinates; naming is the working readout, boundaries are
  not. The brief's regionalize-first thesis is not supported in its boundary form; the
  supportable version is coverage: where each toponym holds, with soft edges.

## 2026-10-09, toponymic-use posterior (`2026-10-09-occurrence-posterior.md`)

- A two-component spatial mixture per word (same-name kernel density vs place-density
  background, EM for the toponymic share, no sampling) classifies single uses of a word as
  toponymic or incidental. Known cases behave: noe 0.97, dogpatch 1.00, nopa 0.91,
  leslieville 0.95, starbucks 0.00, bank 0.05; "sunset" splits into 107 supported uses and
  13 Sunset Dentals.
- Median pi by lexicon class, untuned, comes out division ~0.9, mixed ~0.9, street 0.6–0.9,
  area 0.3–0.8, generic and brand 0.0 in all four cities.
- What it cannot do: tell a toponym in a dense district (fidi, chinatown) from the district's
  trade words (llp, ubs); both are contiguous. The hotspot flag marks both; co-occurrence of
  cores is the next test.
- Bug fixed on the way: scipy's sparse_distance_matrix returns the self pairs, so the
  2026-10-08 field kernels had a doubled diagonal (self-weight 2). Those results were at
  their null either way.
