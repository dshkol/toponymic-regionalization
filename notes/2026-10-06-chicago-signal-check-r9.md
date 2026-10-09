# chicago signal check, H3 res 9

Date: 2026-10-06. Places: Overture 2026-08-19.0, 197853 rows, sha256 fccac540f984…; 197853 with a primary name, 135943 inside the city cells.
Ground truth: Overture macrohoods inside the Chicago locality (73 of the 77 community areas; provisional).
Cells: 5318 H3-9 cells (centroid inside the union of the 73 polygons), 2 graph component(s) before bridging; 4449 cells with at least one token; tokens per cell p10/p25/p50/p75/p90 = 0/4/16/56/140.
Features: 7340 tokens with cell-df in [5, 20% of cells] on unsmoothed counts; counts summed over the k-ring (`ring`); sqrt(tf)·idf, L2 per cell, truncated SVD to 30. One token per distinct name per cell.

## Reading

1. Chicago is where names come closest to standing on their own. Unsmoothed, Ward on
   names reaches ARI 0.19 at k = 73 (null 0.00) with the largest region at 22% of cells,
   not the 70% collapse of SF and Vancouver: 5,318 cells give Ward enough dense
   neighbours to grow regions. With 1-ring smoothing names reach 0.36 at k = 73 against a
   null of 0.10, a gap of +0.26, the largest of the four cities; coordinates-only is 0.39
   and the random floor 0.38, so on ARI geography still ties it.
2. The ring-1, k = 20 regions are the airports (O'Hare and Midway as their own regions,
   on airline and cargo tokens), the Lower West Side as pilsen / villita / tortilleria,
   bridgeport / chinatown / wicker / bucktown lumped by the Ward cut, Hyde Park and
   Kenwood as hyde / uchicago / quadrangle, Englewood, Beverly, Roseland / Pullman,
   Hegewisch / Calumet, the North Lawndale institutions (homan, kipp), Edgebrook /
   Sauganash / the kosher cluster (zabiha, bais) on the far north side. The Loop comes
   out as a region of law and finance tokens (divorce, valuation). These are the names
   businesses use; the 1920s community-area names are recovered where they are also the
   living name (Englewood, Beverly, Roseland, Hegewisch) and not where they are not
   (Near North Side, Near West Side, West Town, Lower West Side), which is what the
   Cadmus-links naming test found.
3. Ground truth is provisional: 73 of the 77 community areas (Logan Square, Humboldt
   Park, New City and Gage Park are missing from the Overture release), so those four
   areas' cells are outside the cell set; two graph components (O'Hare) bridged.

## Agreement with the 73 areas

ARI/NMI over all cells (ground truth = polygon containing the cell centroid). `largest` is the share of cells in the biggest region.

| ring   |   k | method                                        |    ari |   nmi |   largest |
|:-------|----:|:----------------------------------------------|-------:|------:|----------:|
| -      |   5 | SCHC Ward: coordinates only                   |  0.131 | 0.515 |   nan     |
| -      |   5 | floor: random contiguous (mean of 20)         |  0.094 | 0.462 |   nan     |
| -      |  10 | SCHC Ward: coordinates only                   |  0.222 | 0.622 |   nan     |
| -      |  10 | floor: random contiguous (mean of 20)         |  0.175 | 0.591 |   nan     |
| -      |  20 | SCHC Ward: coordinates only                   |  0.317 | 0.699 |   nan     |
| -      |  20 | floor: random contiguous (mean of 20)         |  0.264 | 0.673 |   nan     |
| -      |  40 | SCHC Ward: coordinates only                   |  0.393 | 0.745 |   nan     |
| -      |  40 | floor: random contiguous (mean of 20)         |  0.357 | 0.728 |   nan     |
| -      |  73 | SCHC Ward: coordinates only                   |  0.390 | 0.767 |   nan     |
| -      |  73 | floor: random contiguous (mean of 20)         |  0.383 | 0.751 |   nan     |
| 0      |   5 | SCHC Ward: names                              |  0.016 | 0.235 |     0.768 |
| 0      |   5 | null: names dealt to random cells (mean of 5) | -0.000 | 0.002 |   nan     |
| 0      |   5 | k-means on names, no contiguity               |  0.019 | 0.108 |   nan     |
| 0      |  10 | SCHC Ward: names                              |  0.087 | 0.488 |     0.398 |
| 0      |  10 | null: names dealt to random cells (mean of 5) | -0.000 | 0.004 |   nan     |
| 0      |  10 | k-means on names, no contiguity               |  0.023 | 0.134 |   nan     |
| 0      |  20 | SCHC Ward: names                              |  0.165 | 0.581 |     0.224 |
| 0      |  20 | null: names dealt to random cells (mean of 5) |  0.000 | 0.008 |   nan     |
| 0      |  20 | k-means on names, no contiguity               |  0.039 | 0.159 |   nan     |
| 0      |  40 | SCHC Ward: names                              |  0.183 | 0.605 |     0.218 |
| 0      |  40 | null: names dealt to random cells (mean of 5) |  0.000 | 0.015 |   nan     |
| 0      |  40 | k-means on names, no contiguity               |  0.056 | 0.199 |   nan     |
| 0      |  73 | SCHC Ward: names                              |  0.188 | 0.618 |     0.215 |
| 0      |  73 | null: names dealt to random cells (mean of 5) |  0.000 | 0.033 |   nan     |
| 0      |  73 | k-means on names, no contiguity               |  0.066 | 0.235 |   nan     |
| 1      |   5 | SCHC Ward: names                              |  0.082 | 0.456 |     0.357 |
| 1      |   5 | null: names dealt to random cells (mean of 5) |  0.003 | 0.046 |   nan     |
| 1      |   5 | k-means on names, no contiguity               |  0.052 | 0.283 |   nan     |
| 1      |  10 | SCHC Ward: names                              |  0.127 | 0.561 |     0.303 |
| 1      |  10 | null: names dealt to random cells (mean of 5) |  0.011 | 0.143 |   nan     |
| 1      |  10 | k-means on names, no contiguity               |  0.078 | 0.366 |   nan     |
| 1      |  20 | SCHC Ward: names                              |  0.222 | 0.655 |     0.185 |
| 1      |  20 | null: names dealt to random cells (mean of 5) |  0.043 | 0.337 |   nan     |
| 1      |  20 | k-means on names, no contiguity               |  0.103 | 0.425 |   nan     |
| 1      |  40 | SCHC Ward: names                              |  0.329 | 0.718 |     0.092 |
| 1      |  40 | null: names dealt to random cells (mean of 5) |  0.068 | 0.471 |   nan     |
| 1      |  40 | k-means on names, no contiguity               |  0.144 | 0.499 |   nan     |
| 1      |  73 | SCHC Ward: names                              |  0.362 | 0.743 |     0.060 |
| 1      |  73 | null: names dealt to random cells (mean of 5) |  0.104 | 0.573 |   nan     |
| 1      |  73 | k-means on names, no contiguity               |  0.176 | 0.557 |   nan     |
| 2      |   5 | SCHC Ward: names                              |  0.080 | 0.457 |     0.396 |
| 2      |   5 | null: names dealt to random cells (mean of 5) |  0.055 | 0.387 |   nan     |
| 2      |   5 | k-means on names, no contiguity               |  0.071 | 0.374 |   nan     |
| 2      |  10 | SCHC Ward: names                              |  0.197 | 0.623 |     0.211 |
| 2      |  10 | null: names dealt to random cells (mean of 5) |  0.125 | 0.533 |   nan     |
| 2      |  10 | k-means on names, no contiguity               |  0.145 | 0.512 |   nan     |
| 2      |  20 | SCHC Ward: names                              |  0.290 | 0.696 |     0.108 |
| 2      |  20 | null: names dealt to random cells (mean of 5) |  0.267 | 0.660 |   nan     |
| 2      |  20 | k-means on names, no contiguity               |  0.220 | 0.627 |   nan     |
| 2      |  40 | SCHC Ward: names                              |  0.361 | 0.743 |     0.062 |
| 2      |  40 | null: names dealt to random cells (mean of 5) |  0.354 | 0.720 |   nan     |
| 2      |  40 | k-means on names, no contiguity               |  0.290 | 0.682 |   nan     |
| 2      |  73 | SCHC Ward: names                              |  0.410 | 0.778 |     0.034 |
| 2      |  73 | null: names dealt to random cells (mean of 5) |  0.375 | 0.751 |   nan     |
| 2      |  73 | k-means on names, no contiguity               |  0.357 | 0.735 |   nan     |

## Lifted tokens per region, names ring 1, k=20

- region 0: hegewisch, calumet, tapatio, norfolk, eastside, task
- region 1: jarvis, clarendon, lac, sather, sheffield, edgewater
- region 2: ashburn, pisgah, stony, gulf, auburn, sox
- region 3: entry, enrollment, cargo, aviation, airline, flights
- region 4: milagro, lineage, villita, brighton, teloloapan, tortilleria
- region 5: edgebrook, zabiha, bais, ewa, sauganash, norwood
- region 6: chinatown, wicker, humboldt, bucktown, bridgeport, hotpot
- region 7: mdw, midway, clearing, aeropuerto, fonseca, caray
- region 8: beverly, hills, greenwood, tommie, xavier, celtic
- region 9: englewood, antioch, canaan, tish, benedict, seashell
- region 10: hyde, quadrangle, cornell, uchicago, kenwood, drexel
- region 11: cragin, galewood, avondale, kelvyn, mont, hermosa
- region 12: sas, qatar, ord, swissport, uso, airways
- region 13: tilton, lawndale, homan, kipp, habilitative, kostner
- region 14: altgeld, carver, trades, tca, lively, cics
- region 15: divorce, iparkit, gynecologic, valuation, manhattan, centric
- region 16: ohare, delta, hare, airport, terminal, airlines
- region 17: marsh, processing, nature, trail, steel, indian
- region 18: roseland, pullman, chesterfield, fernwood, langley, dominique
- region 19: cargo, fcu, newsstand, swissport, berghoff, ord

Maps: `figures/2026-10-06-chicago-signal-check-r9-maps.png`, `figures/2026-10-06-chicago-signal-check-r9-density.png`.
