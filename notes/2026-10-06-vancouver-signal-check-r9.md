# vancouver signal check, H3 res 9

Date: 2026-10-06. Places: Overture 2026-08-19.0, 43096 rows, sha256 d3adc6fc8d8f…; 43096 with a primary name, 37700 inside the city cells.
Ground truth: Overture macrohoods inside the Vancouver locality (22; provisional, names equal the City's 22 local areas).
Cells: 1273 H3-9 cells (centroid inside the union of the 22 polygons), 1 graph component(s) before bridging; 1140 cells with at least one token; tokens per cell p10/p25/p50/p75/p90 = 0/4/13/55/177.
Features: 2936 tokens with cell-df in [5, 20% of cells] on unsmoothed counts; counts summed over the k-ring (`ring`); sqrt(tf)·idf, L2 per cell, truncated SVD to 30. One token per distinct name per cell.

## Reading

Same shape as San Francisco (`2026-10-06-sf-signal-check-r9.md`), on a ground truth
whose 22 names are the ones people use (Kitsilano, Kerrisdale, Mount Pleasant):

1. Unsmoothed names: ARI 0.05 at k = 22 with one region holding 70% of cells; the
   permutation null is 0.00, so it is signal, but Ward still collapses on sparse cells
   (median 13 tokens per cell, lower than SF's 29).
2. Ring-1 smoothing: names 0.40 at k = 22 against a null of 0.26, the largest
   names-minus-null gap of any city so far (+0.14), and close to coordinates-only (0.44).
   Ring 2 is geometry again (null 0.45 vs names 0.42).
3. The ring-1, k = 20 regions are the local areas by their lifted tokens: kerrisdale;
   marpole; dunbar; kitsilano/kits/fourth/alma; oakridge/langara; fraserview;
   renfrew/rupert/boundary; coal/thurlow/denman (West End); musqueam. The map shows
   Kitsilano, Kerrisdale, Dunbar, Marpole and Killarney as coherent regions and the
   east-side areas split along Kingsway rather than the City's grid of lines.
4. Ground truth is provisional: Overture macrohoods, which match the City's 22 local
   areas by name but have not been checked against the official polygons.

## Agreement with the 22 areas

ARI/NMI over all cells (ground truth = polygon containing the cell centroid). `largest` is the share of cells in the biggest region.

| ring   |   k | method                                        |   ari |   nmi |   largest |
|:-------|----:|:----------------------------------------------|------:|------:|----------:|
| -      |   5 | SCHC Ward: coordinates only                   | 0.265 | 0.558 |   nan     |
| -      |   5 | floor: random contiguous (mean of 20)         | 0.201 | 0.512 |   nan     |
| -      |  10 | SCHC Ward: coordinates only                   | 0.407 | 0.667 |   nan     |
| -      |  10 | floor: random contiguous (mean of 20)         | 0.290 | 0.601 |   nan     |
| -      |  20 | SCHC Ward: coordinates only                   | 0.455 | 0.712 |   nan     |
| -      |  20 | floor: random contiguous (mean of 20)         | 0.362 | 0.661 |   nan     |
| -      |  40 | SCHC Ward: coordinates only                   | 0.384 | 0.710 |   nan     |
| -      |  40 | floor: random contiguous (mean of 20)         | 0.391 | 0.689 |   nan     |
| -      |  22 | SCHC Ward: coordinates only                   | 0.444 | 0.714 |   nan     |
| -      |  22 | floor: random contiguous (mean of 20)         | 0.373 | 0.670 |   nan     |
| 0      |   5 | SCHC Ward: names                              | 0.041 | 0.228 |     0.756 |
| 0      |   5 | null: names dealt to random cells (mean of 5) | 0.000 | 0.007 |   nan     |
| 0      |   5 | k-means on names, no contiguity               | 0.020 | 0.095 |   nan     |
| 0      |  10 | SCHC Ward: names                              | 0.044 | 0.284 |     0.740 |
| 0      |  10 | null: names dealt to random cells (mean of 5) | 0.000 | 0.015 |   nan     |
| 0      |  10 | k-means on names, no contiguity               | 0.023 | 0.134 |   nan     |
| 0      |  20 | SCHC Ward: names                              | 0.049 | 0.325 |     0.704 |
| 0      |  20 | null: names dealt to random cells (mean of 5) | 0.000 | 0.031 |   nan     |
| 0      |  20 | k-means on names, no contiguity               | 0.034 | 0.171 |   nan     |
| 0      |  40 | SCHC Ward: names                              | 0.054 | 0.394 |     0.613 |
| 0      |  40 | null: names dealt to random cells (mean of 5) | 0.000 | 0.066 |   nan     |
| 0      |  40 | k-means on names, no contiguity               | 0.039 | 0.223 |   nan     |
| 0      |  22 | SCHC Ward: names                              | 0.049 | 0.326 |     0.701 |
| 0      |  22 | null: names dealt to random cells (mean of 5) | 0.000 | 0.034 |   nan     |
| 0      |  22 | k-means on names, no contiguity               | 0.029 | 0.176 |   nan     |
| 1      |   5 | SCHC Ward: names                              | 0.123 | 0.449 |     0.522 |
| 1      |   5 | null: names dealt to random cells (mean of 5) | 0.088 | 0.326 |   nan     |
| 1      |   5 | k-means on names, no contiguity               | 0.075 | 0.273 |   nan     |
| 1      |  10 | SCHC Ward: names                              | 0.311 | 0.614 |     0.181 |
| 1      |  10 | null: names dealt to random cells (mean of 5) | 0.132 | 0.452 |   nan     |
| 1      |  10 | k-means on names, no contiguity               | 0.116 | 0.382 |   nan     |
| 1      |  20 | SCHC Ward: names                              | 0.392 | 0.676 |     0.110 |
| 1      |  20 | null: names dealt to random cells (mean of 5) | 0.249 | 0.588 |   nan     |
| 1      |  20 | k-means on names, no contiguity               | 0.277 | 0.563 |   nan     |
| 1      |  40 | SCHC Ward: names                              | 0.398 | 0.703 |     0.063 |
| 1      |  40 | null: names dealt to random cells (mean of 5) | 0.295 | 0.650 |   nan     |
| 1      |  40 | k-means on names, no contiguity               | 0.302 | 0.628 |   nan     |
| 1      |  22 | SCHC Ward: names                              | 0.399 | 0.681 |     0.110 |
| 1      |  22 | null: names dealt to random cells (mean of 5) | 0.257 | 0.600 |   nan     |
| 1      |  22 | k-means on names, no contiguity               | 0.289 | 0.582 |   nan     |
| 2      |   5 | SCHC Ward: names                              | 0.189 | 0.512 |     0.400 |
| 2      |   5 | null: names dealt to random cells (mean of 5) | 0.185 | 0.482 |   nan     |
| 2      |   5 | k-means on names, no contiguity               | 0.208 | 0.496 |   nan     |
| 2      |  10 | SCHC Ward: names                              | 0.304 | 0.624 |     0.264 |
| 2      |  10 | null: names dealt to random cells (mean of 5) | 0.324 | 0.617 |   nan     |
| 2      |  10 | k-means on names, no contiguity               | 0.247 | 0.574 |   nan     |
| 2      |  20 | SCHC Ward: names                              | 0.420 | 0.702 |     0.116 |
| 2      |  20 | null: names dealt to random cells (mean of 5) | 0.435 | 0.696 |   nan     |
| 2      |  20 | k-means on names, no contiguity               | 0.388 | 0.684 |   nan     |
| 2      |  40 | SCHC Ward: names                              | 0.420 | 0.733 |     0.052 |
| 2      |  40 | null: names dealt to random cells (mean of 5) | 0.406 | 0.720 |   nan     |
| 2      |  40 | k-means on names, no contiguity               | 0.376 | 0.715 |   nan     |
| 2      |  22 | SCHC Ward: names                              | 0.424 | 0.708 |     0.116 |
| 2      |  22 | null: names dealt to random cells (mean of 5) | 0.445 | 0.704 |   nan     |
| 2      |  22 | k-means on names, no contiguity               | 0.432 | 0.710 |   nan     |

## Lifted tokens per region, names ring 1, k=20

- region 0: marpole, airport, mews, lube, singh, progressive
- region 1: kerrisdale, regent, nando, lai, joan, select
- region 2: fraserview, sweets, astrologer, sri, fraser, psychic
- region 3: boundary, renfrew, rupert, kaslo, superstore, bmw
- region 4: counsel, coal, minerals, exploration, thurlow, nightclub
- region 5: trout, cottage, britannia, grandview, woodland, sister
- region 6: oakridge, langara, jewish, course, herb, boss
- region 7: musqueam, band, tri, blake, golf, core
- region 8: fourth, kitsilano, alma, kits, vine, yew
- region 9: grey, jericho, banks, outdoors, hostelling, monarch
- region 10: dunbar, heaven, pets, dave, sage, southlands
- region 11: shaughnessy, ronald, brock, exterior, blood, roman
- region 12: collingwood, hoa, joyce, kingsway, herbal, linh
- region 13: champlain, cook, mj, captain, heights, tasty
- region 14: brighton, hastings, franklin, nights, nanaimo, bianca
- region 15: strathcona, mec, sportswear, benevolent, romeo, olympic
- region 16: trafalgar, ridge, arbutus, prince, driver, banks
- region 17: river, district, irrigation, solid, crossing, pointe
- region 18: southlands, bake, farms, perry, trail, country
- region 19: killarney, edgar, ki, faith, capoeira, tsai

Maps: `figures/2026-10-06-vancouver-signal-check-r9-maps.png`, `figures/2026-10-06-vancouver-signal-check-r9-density.png`.
