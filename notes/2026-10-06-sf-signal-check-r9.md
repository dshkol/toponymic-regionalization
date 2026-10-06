# SF signal check, H3 res 9

Date: 2026-10-06. Places: Overture 2026-08-19.0, 60536 rows, sha256 ebe20a80d0eb…; 60536 with a primary name, 57656 inside the city cells.
Ground truth: DataSF Analysis Neighborhoods (41), copied from cadmus/data/neighborhoods.geojson.
Cells: 1114 H3-9 cells (centroid inside the union of the 41 polygons), 2 graph component(s) before bridging; 1054 cells with at least one token; tokens per cell p10/p25/p50/p75/p90 = 3/10/29/112/318.
Features: 4159 tokens with cell-df in [5, 20% of cells] on unsmoothed counts; counts summed over the k-ring (`ring`); sqrt(tf)·idf, L2 per cell, truncated SVD to 30. One token per distinct name per cell.

## Reading

1. **Names carry signal, but less than geography does.** On unsmoothed cells (ring 0) the
   names partition agrees with DataSF at ARI 0.15–0.20 (k = 20, 40) while names dealt to
   random cells give 0.00, so the agreement is real. But Ward on cell coordinates alone
   reaches 0.44 at k = 20, and even random contiguous partitions reach 0.30. A compact,
   contiguous partition of SF agrees with the 41 analysis neighbourhoods about as well as
   one driven by names, because the analysis neighbourhoods are themselves compact tract
   aggregations.
2. **Smoothing manufactures agreement.** Summing counts over the 1-ring lifts names to
   0.36 (k = 20), but the permutation null rises to 0.26, so only about +0.10 ARI is the
   names; at ring 2 the null (0.33) matches the names run (0.34) and the signal is gone.
   Any future number from a smoothed pipeline needs this null beside it.
3. **Unsmoothed Ward on 1,114 sparse cells collapses.** The first run (top-200 tokens by
   locality, centred log-ratio with pseudocount, the brief's option (a)) produced one
   region of 1,072 cells plus specks, ARI 0.00 at every k: Ward peels off the few
   token-rich cells as outliers. Unit-length rows (sqrt tf·idf, L2) fix the collapse
   (`largest` falls from 0.96 to 0.35–0.43) but the partition is still one big region
   and many small ones at ring 0.
4. **The regions are nameable even when the ARI is modest.** At ring 1, k = 20, the lifted
   tokens per region read as neighbourhoods (noe/valencia/guerrero/castro/dolores;
   irving/judah/noriega/sunset; dogpatch/mariposa/potrero; bayview/candlestick/hunters;
   treasure/island; fremont/fidi/salesforce). ARI against a tract-based 41-way partition
   is a harsh reading of that.
5. **Scale.** Median 29 tokens per H3-9 cell, 10% of cells have 3 or fewer; evidence is
   concentrated downtown (density map). H3-9 is below the scale at which names are dense
   enough to cluster on their own; the honest next test is cells at H3-8, or max-p with a
   floor on places per region, rather than more smoothing.

What to do next, in order: (a) max-p with a places-per-region floor on unsmoothed H3-9
counts, which is the formulation the brief argues for; (b) H3-8 cells, same nulls;
(c) a ground truth that is not tract aggregation (SF Planning neighbourhood groups, or
the Cadmus engine's `supported` rate on the output polygons, which is the comparison that
matters for Cadmus). Toronto, Vancouver and Chicago wait until one of those beats the
coordinates-only baseline.

## Agreement with the 41 neighbourhoods

ARI/NMI over all cells (ground truth = polygon containing the cell centroid). `largest` is the share of cells in the biggest region.

| ring   |   k | method                                        |   ari |   nmi |   largest |
|:-------|----:|:----------------------------------------------|------:|------:|----------:|
| -      |   5 | SCHC Ward: coordinates only                   | 0.234 | 0.538 |   nan     |
| -      |   5 | floor: random contiguous (mean of 20)         | 0.135 | 0.438 |   nan     |
| -      |  10 | SCHC Ward: coordinates only                   | 0.356 | 0.638 |   nan     |
| -      |  10 | floor: random contiguous (mean of 20)         | 0.224 | 0.558 |   nan     |
| -      |  20 | SCHC Ward: coordinates only                   | 0.444 | 0.704 |   nan     |
| -      |  20 | floor: random contiguous (mean of 20)         | 0.303 | 0.639 |   nan     |
| -      |  40 | SCHC Ward: coordinates only                   | 0.345 | 0.719 |   nan     |
| -      |  40 | floor: random contiguous (mean of 20)         | 0.359 | 0.688 |   nan     |
| 0      |   5 | SCHC Ward: names                              | 0.042 | 0.250 |     0.777 |
| 0      |   5 | null: names dealt to random cells (mean of 5) | 0.000 | 0.010 |   nan     |
| 0      |   5 | k-means on names, no contiguity               | 0.028 | 0.156 |   nan     |
| 0      |  10 | SCHC Ward: names                              | 0.044 | 0.304 |     0.724 |
| 0      |  10 | null: names dealt to random cells (mean of 5) | 0.000 | 0.020 |   nan     |
| 0      |  10 | k-means on names, no contiguity               | 0.042 | 0.230 |   nan     |
| 0      |  20 | SCHC Ward: names                              | 0.148 | 0.503 |     0.433 |
| 0      |  20 | null: names dealt to random cells (mean of 5) | 0.001 | 0.048 |   nan     |
| 0      |  20 | k-means on names, no contiguity               | 0.065 | 0.291 |   nan     |
| 0      |  40 | SCHC Ward: names                              | 0.197 | 0.584 |     0.346 |
| 0      |  40 | null: names dealt to random cells (mean of 5) | 0.000 | 0.084 |   nan     |
| 0      |  40 | k-means on names, no contiguity               | 0.082 | 0.373 |   nan     |
| 1      |   5 | SCHC Ward: names                              | 0.164 | 0.469 |     0.387 |
| 1      |   5 | null: names dealt to random cells (mean of 5) | 0.066 | 0.314 |   nan     |
| 1      |   5 | k-means on names, no contiguity               | 0.090 | 0.343 |   nan     |
| 1      |  10 | SCHC Ward: names                              | 0.267 | 0.587 |     0.195 |
| 1      |  10 | null: names dealt to random cells (mean of 5) | 0.135 | 0.475 |   nan     |
| 1      |  10 | k-means on names, no contiguity               | 0.139 | 0.499 |   nan     |
| 1      |  20 | SCHC Ward: names                              | 0.360 | 0.680 |     0.095 |
| 1      |  20 | null: names dealt to random cells (mean of 5) | 0.256 | 0.605 |   nan     |
| 1      |  20 | k-means on names, no contiguity               | 0.347 | 0.650 |   nan     |
| 1      |  40 | SCHC Ward: names                              | 0.363 | 0.718 |     0.049 |
| 1      |  40 | null: names dealt to random cells (mean of 5) | 0.293 | 0.669 |   nan     |
| 1      |  40 | k-means on names, no contiguity               | 0.336 | 0.698 |   nan     |
| 2      |   5 | SCHC Ward: names                              | 0.191 | 0.498 |     0.314 |
| 2      |   5 | null: names dealt to random cells (mean of 5) | 0.149 | 0.462 |   nan     |
| 2      |   5 | k-means on names, no contiguity               | 0.203 | 0.488 |   nan     |
| 2      |  10 | SCHC Ward: names                              | 0.262 | 0.588 |     0.215 |
| 2      |  10 | null: names dealt to random cells (mean of 5) | 0.231 | 0.571 |   nan     |
| 2      |  10 | k-means on names, no contiguity               | 0.339 | 0.624 |   nan     |
| 2      |  20 | SCHC Ward: names                              | 0.338 | 0.673 |     0.126 |
| 2      |  20 | null: names dealt to random cells (mean of 5) | 0.328 | 0.663 |   nan     |
| 2      |  20 | k-means on names, no contiguity               | 0.332 | 0.665 |   nan     |
| 2      |  40 | SCHC Ward: names                              | 0.333 | 0.710 |     0.063 |
| 2      |  40 | null: names dealt to random cells (mean of 5) | 0.341 | 0.715 |   nan     |
| 2      |  40 | k-means on names, no contiguity               | 0.321 | 0.713 |   nan     |

## Lifted tokens per region, names ring 1, k=20

- region 0: zoo, playa, highway, andytown, doggie, archery
- region 1: glen, bruno, portola, bayshore, cab, cutting
- region 2: harding, merced, ripple, tee, junior, camps
- region 3: omi, daly, ingleside, excelsior, ccsf, geneva
- region 4: richmond, clement, vladimir, past, balboa, kwok
- region 5: noe, valencia, guerrero, castro, levis, dolores
- region 6: portal, taraval, parkside, stern, stonestown, ulloa
- region 7: dogpatch, mariposa, potrero, pediatric, mb, hughes
- region 8: greenwich, chestnut, fishermans, wharf, fisherman, lombard
- region 9: nopa, panhandle, usf, endoscopy, parnassus, divisadero
- region 10: bayview, candlestick, hunters, southeast, ers, tabernacle
- region 11: corbett, peaks, twin, miraloma, defender, brendan
- region 12: overlook, cemetery, crissy, presidio, parade, crosby
- region 13: mclaren, crocker, pointe, grande, samoan, ab
- region 14: visitacion, leland, bayshore, clubs, worship, celtic
- region 15: treasure, island, dependable, distillery, winery, guard
- region 16: shipyard, hunters, diva, ron, hilltop, pit
- region 17: irving, judah, noriega, sunset, lawton, vegetarian
- region 18: fremont, fidi, salesforce, counter, fan, alloy
- region 19: sfsu, stonestown, students, studies, junipero, thornton

Maps: `figures/2026-10-06-sf-signal-check-r9-maps.png`, `figures/2026-10-06-sf-signal-check-r9-density.png`.
