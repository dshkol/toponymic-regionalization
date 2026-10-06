# chicago signal check, H3 res 9

Date: 2026-10-06. Places: Overture 2026-08-19.0, 197853 rows, sha256 fccac540f984…; 197853 with a primary name, 135943 inside the city cells.
Ground truth: Overture macrohoods inside the Chicago locality (73 of the 77 community areas; provisional).
Cells: 5318 H3-9 cells (centroid inside the union of the 73 polygons), 2 graph component(s) before bridging; 4449 cells with at least one token; tokens per cell p10/p25/p50/p75/p90 = 0/4/16/56/140.
Features: 7340 tokens with cell-df in [5, 20% of cells] on unsmoothed counts; counts summed over the k-ring (`ring`); sqrt(tf)·idf, L2 per cell, truncated SVD to 30. One token per distinct name per cell.

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

## Lifted tokens per region, names ring 2, k=20

- region 0: qatar, sas, ord, swissport, ohare, hare
- region 1: cragin, mont, galewood, kelvyn, portage, dunning
- region 2: hegewisch, eastside, tapatio, lanes, norfolk, florian
- region 3: indio, comales, villita, brighton, fruteria, milagro
- region 4: zabiha, bais, lincolnwood, lubavitch, sauganash, morse
- region 5: stony, chatham, josephine, avalon, townsend, jeffery
- region 6: calumet, skyway, pullman, amigos, salem, norfolk
- region 7: bronzeville, hyde, kenwood, quadrangle, obama, drexel
- region 8: saic, ontario, divorce, iparkit, greektown, clothiers
- region 9: beverly, hills, greenwood, tommie, xavier, wholistic
- region 10: edgebrook, norwood, gladstone, cumberland, bankers, edison
- region 11: altgeld, carver, lively, convenience, trades, concordia
- region 12: englewood, auburn, xperience, gresham, fernwood, tish
- region 13: habilitative, tilton, homan, douglass, kipp, westside
- region 14: cargo, fcu, newsstand, swissport, berghoff, airline
- region 15: mdw, clearing, aeropuerto, midway, caray, hale
- region 16: sheffield, clarendon, exlsly, southport, clybourn, wicker
- region 17: bridgeport, chinatown, hotpot, dim, pilsen, liu
- region 18: roseland, pullman, marshfield, pipe, humble, jurisdiction
- region 19: marsh, processing, port, railroad, liquid, materials

Maps: `figures/2026-10-06-chicago-signal-check-r9-maps.png`, `figures/2026-10-06-chicago-signal-check-r9-density.png`.
