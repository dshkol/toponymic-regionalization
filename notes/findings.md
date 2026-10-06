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
