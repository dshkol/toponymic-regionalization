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

Side-findings parked here:

- DataSF's 41 analysis neighbourhoods include open water and large parks (the Bayview
  polygon extends into the Bay; Golden Gate Park, Presidio and McLaren Park are their own
  units), so cells there are scored against a label with no place names behind it.
- The cloud environment's network policy blocks data.sfgov.org, open.toronto.ca,
  opendata.vancouver.ca, data.cityofchicago.org and the Overture STAC catalog;
  `overturemaps download` fails there. This run reused the cadmus extract (checksum
  verified against its manifest) and the cadmus copy of the DataSF polygons.
