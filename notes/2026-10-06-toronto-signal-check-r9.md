# toronto signal check, H3 res 9

Date: 2026-10-06. Places: Overture 2026-08-19.0, 162551 rows, sha256 63343c77a88c…; 162551 with a primary name, 124189 inside the city cells.
Ground truth: Overture neighbourhoods inside the Toronto county polygon (174 vs the City's 158; provisional).
Cells: 5837 H3-9 cells (centroid inside the union of the 174 polygons), 3 graph component(s) before bridging; 5069 cells with at least one token; tokens per cell p10/p25/p50/p75/p90 = 0/4/12/46/128.
Features: 7279 tokens with cell-df in [5, 20% of cells] on unsmoothed counts; counts summed over the k-ring (`ring`); sqrt(tf)·idf, L2 per cell, truncated SVD to 30. One token per distinct name per cell.

## Reading

1. Weakest of the four cities against its ground truth, and the ground truth is the
   least trustworthy: 174 Overture neighbourhoods against the City's 158 census-style
   hyphenated units. At k = 174 even random contiguous partitions (0.32) beat Ward on
   coordinates (0.29); ARI at that many small areas is mostly noise.
2. Unsmoothed names: ARI 0.08 at k = 174 (null 0.00), largest region 30% of cells.
   Ring 1: 0.27 against a null of 0.18, coordinates-only 0.29. Ring 2 is geometry.
3. The regions are the places people name, which the 158 mostly are not: greektown /
   leslieville / beaches; thorncliffe / leaside / flemingdon; cliffside / bluffs /
   guildwood; alderwood / mimico / queensway / sherway; uoft / harbord / tmu; the
   airport (carlingview, terminals); the Islands (hanlan, ferry, docks); the Zoo. This
   matches the Cadmus-links naming test, where the lexicon returned leslieville,
   greektown, cabbagetown with no polygon in the official set.
4. Three graph components before bridging (the Islands and the airport lands); the
   median cell has 12 tokens, the sparsest of the four cities.

## Agreement with the 174 areas

ARI/NMI over all cells (ground truth = polygon containing the cell centroid). `largest` is the share of cells in the biggest region.

| ring   |   k | method                                        |    ari |   nmi |   largest |
|:-------|----:|:----------------------------------------------|-------:|------:|----------:|
| -      |   5 | SCHC Ward: coordinates only                   |  0.069 | 0.447 |   nan     |
| -      |   5 | floor: random contiguous (mean of 20)         |  0.057 | 0.414 |   nan     |
| -      |  10 | SCHC Ward: coordinates only                   |  0.139 | 0.576 |   nan     |
| -      |  10 | floor: random contiguous (mean of 20)         |  0.112 | 0.540 |   nan     |
| -      |  20 | SCHC Ward: coordinates only                   |  0.253 | 0.671 |   nan     |
| -      |  20 | floor: random contiguous (mean of 20)         |  0.179 | 0.628 |   nan     |
| -      |  40 | SCHC Ward: coordinates only                   |  0.349 | 0.728 |   nan     |
| -      |  40 | floor: random contiguous (mean of 20)         |  0.267 | 0.694 |   nan     |
| -      | 174 | SCHC Ward: coordinates only                   |  0.293 | 0.770 |   nan     |
| -      | 174 | floor: random contiguous (mean of 20)         |  0.323 | 0.757 |   nan     |
| 0      |   5 | SCHC Ward: names                              |  0.032 | 0.337 |     0.555 |
| 0      |   5 | null: names dealt to random cells (mean of 5) |  0.000 | 0.002 |   nan     |
| 0      |   5 | k-means on names, no contiguity               |  0.006 | 0.058 |   nan     |
| 0      |  10 | SCHC Ward: names                              |  0.033 | 0.352 |     0.539 |
| 0      |  10 | null: names dealt to random cells (mean of 5) | -0.000 | 0.003 |   nan     |
| 0      |  10 | k-means on names, no contiguity               |  0.006 | 0.089 |   nan     |
| 0      |  20 | SCHC Ward: names                              |  0.051 | 0.434 |     0.432 |
| 0      |  20 | null: names dealt to random cells (mean of 5) |  0.000 | 0.007 |   nan     |
| 0      |  20 | k-means on names, no contiguity               |  0.015 | 0.135 |   nan     |
| 0      |  40 | SCHC Ward: names                              |  0.071 | 0.487 |     0.346 |
| 0      |  40 | null: names dealt to random cells (mean of 5) |  0.000 | 0.015 |   nan     |
| 0      |  40 | k-means on names, no contiguity               |  0.021 | 0.192 |   nan     |
| 0      | 174 | SCHC Ward: names                              |  0.077 | 0.553 |     0.298 |
| 0      | 174 | null: names dealt to random cells (mean of 5) | -0.000 | 0.066 |   nan     |
| 0      | 174 | k-means on names, no contiguity               |  0.033 | 0.310 |   nan     |
| 1      |   5 | SCHC Ward: names                              |  0.059 | 0.413 |     0.340 |
| 1      |   5 | null: names dealt to random cells (mean of 5) |  0.008 | 0.147 |   nan     |
| 1      |   5 | k-means on names, no contiguity               |  0.015 | 0.163 |   nan     |
| 1      |  10 | SCHC Ward: names                              |  0.085 | 0.497 |     0.256 |
| 1      |  10 | null: names dealt to random cells (mean of 5) |  0.015 | 0.252 |   nan     |
| 1      |  10 | k-means on names, no contiguity               |  0.042 | 0.298 |   nan     |
| 1      |  20 | SCHC Ward: names                              |  0.145 | 0.599 |     0.145 |
| 1      |  20 | null: names dealt to random cells (mean of 5) |  0.020 | 0.332 |   nan     |
| 1      |  20 | k-means on names, no contiguity               |  0.073 | 0.383 |   nan     |
| 1      |  40 | SCHC Ward: names                              |  0.248 | 0.676 |     0.060 |
| 1      |  40 | null: names dealt to random cells (mean of 5) |  0.057 | 0.467 |   nan     |
| 1      |  40 | k-means on names, no contiguity               |  0.115 | 0.481 |   nan     |
| 1      | 174 | SCHC Ward: names                              |  0.266 | 0.738 |     0.026 |
| 1      | 174 | null: names dealt to random cells (mean of 5) |  0.176 | 0.691 |   nan     |
| 1      | 174 | k-means on names, no contiguity               |  0.157 | 0.613 |   nan     |
| 2      |   5 | SCHC Ward: names                              |  0.055 | 0.399 |     0.394 |
| 2      |   5 | null: names dealt to random cells (mean of 5) |  0.038 | 0.356 |   nan     |
| 2      |   5 | k-means on names, no contiguity               |  0.038 | 0.299 |   nan     |
| 2      |  10 | SCHC Ward: names                              |  0.107 | 0.529 |     0.188 |
| 2      |  10 | null: names dealt to random cells (mean of 5) |  0.080 | 0.480 |   nan     |
| 2      |  10 | k-means on names, no contiguity               |  0.056 | 0.394 |   nan     |
| 2      |  20 | SCHC Ward: names                              |  0.187 | 0.634 |     0.091 |
| 2      |  20 | null: names dealt to random cells (mean of 5) |  0.153 | 0.604 |   nan     |
| 2      |  20 | k-means on names, no contiguity               |  0.140 | 0.560 |   nan     |
| 2      |  40 | SCHC Ward: names                              |  0.262 | 0.695 |     0.055 |
| 2      |  40 | null: names dealt to random cells (mean of 5) |  0.243 | 0.681 |   nan     |
| 2      |  40 | k-means on names, no contiguity               |  0.220 | 0.650 |   nan     |
| 2      | 174 | SCHC Ward: names                              |  0.279 | 0.759 |     0.017 |
| 2      | 174 | null: names dealt to random cells (mean of 5) |  0.306 | 0.768 |   nan     |
| 2      | 174 | k-means on names, no contiguity               |  0.271 | 0.748 |   nan     |

## Lifted tokens per region, names ring 1, k=20

- region 0: westway, burnhamthorpe, westmore, humberwood, humberline, thistletown
- region 1: utsc, morningside, malvern, cedarbrae, neilson, bendale
- region 2: milvan, keelesdale, caledonia, promed, yorkdale, latina
- region 3: zoo, rouge, port, tundra, mcintyre, pickering
- region 4: alderwood, mimico, queensway, sherway, cloverdale, stonegate
- region 5: bindery, fabricators, lettering, instructor, middlefield, agincourt
- region 6: wynford, flemingdon, concorde, cosburn, thorncliffe, leaside
- region 7: cliffside, bluffers, bluffs, guildwood, birchcliff, cliffcrest
- region 8: bridlewood, bamburgh, horne, bridletowne, amoreaux, seneca
- region 9: tmu, mines, mos, swipe, invest, sherbourne
- region 10: davisville, chaplin, redpath, sotheby, summerhill, deer
- region 11: won, sina, centerpoint, yazdani, empress, hullmark
- region 12: carlingview, servicemaster, accu, carquest, monitoring, ancient
- region 13: hanlan, carousel, ferry, islands, forestry, beau
- region 14: roncy, humberside, dovercourt, roncesvalles, parkdale, ossington
- region 15: yachts, docks, beavertails, pinewood, billy, herc
- region 16: nai, fairlawn, gan, baycrest, northview, bales
- region 17: balmy, greektown, ashbridges, leslieville, beaches, kew
- region 18: giorgio, dirt, homemade, skyway, rosewood, sells
- region 19: lambton, recreational, kingsway, tilt, reaction, neuro

Maps: `figures/2026-10-06-toronto-signal-check-r9-maps.png`, `figures/2026-10-06-toronto-signal-check-r9-density.png`.
