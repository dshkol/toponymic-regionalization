# 2026-10-09: is this use of a name toponymic? A spatial mixture per occurrence

Script: `pipeline/occurrence_posterior.py`. Tables: `2026-10-09-<city>-occurrence-posterior-r9.csv`
(one row per word with at least five uses) and `-by-class.csv` (cross-tab against the typed
lexicon on the shared-layer branch, `data/lexicon/<city>-2026-08-19.0.jsonl`). The viewer's
name-field layer shows the result per name (`viewer/data/<city>-posterior.json`).

## The question

Dmitry's framing (2026-10-09): for a word with a spatial distribution, can proximity and
contiguity act as evidence that *this* use of the word is a toponymic construct (a
neighbourhood, a microhood, a functional cluster) rather than an incidental or merely common
use? "Sunset" is one word with two populations: a block of places in the Sunset and a tail
of Sunset Dentals elsewhere. The lexicon scores words; this scores uses.

## The model

Each use of a word t (counted once per distinct place name per cell, as everywhere here) is
toponymic or incidental. A toponymic use sits where the other toponymic uses of t sit; an
incidental use sits where businesses sit. With n_tc uses of t in cell c:

    L1(c) = leave-one-out Gaussian kernel density of t's other uses at c   (same-name evidence)
    L0(c) = kernel density of all place names at c                        (background)
    p(c)  = pi L1(c) / (pi L1(c) + (1 - pi) L0(c))                        (posterior: toponymic)
    pi    = sum_c n_tc p(c) / n_t, iterated from 0.5 (EM, 25 steps)

Both densities use the same kernel (bandwidth one cell width, 350 m at H3-9) and are
normalised over the city's cells. No sampling: the update is the kernel sum over
neighbours, which is the "proximity updates" Dmitry asked for. A word clustered only because
its businesses are downtown has L1 close to L0 there and stays near its prior; a word whose
uses sit next to each other at ordinary density gets L1 far above L0 and a posterior near
one; a lone use with no same-name neighbour within the kernel has L1 near zero and is
incidental whatever the word.

Per word: pi (toponymic share), the core (cells with p > 0.5), core share, core extent (the
largest ring-1 connected component of the core, in cells), the median place-density
percentile of the core, and a label: *scattered* (pi < 0.3 or no core), *point* (core of one
to three cells: landmark, institution, microhood), *area* (four or more). *Hotspot* flags a
core whose median density percentile is at least 0.9.

A bug found on the way: `scipy`'s `sparse_distance_matrix` already returns the zero-distance
self pairs, so the kernel matrices in `fields.py` (2026-10-08) had a doubled diagonal, i.e.
self-weight 2. With the mixture that made every word toponymic; fixed in both files. The
2026-10-08 field results were run with the doubled diagonal, which is a slightly sharper
kernel; they were at their null with it and nothing there depends on the exact kernel.

## Does it do what we meant? Known cases

San Francisco (pi, core extent in cells, label):

| toponyms | | incidental words | | dense-district words | |
|---|---|---|---|---|---|
| noe | 0.97, 15, area | starbucks | 0.00, scattered | llp | 0.95, 25, area, hotspot |
| castro | 0.94, 21, area | bank | 0.05, scattered | ubs | 1.00, 3, point, hotspot |
| sunset | 0.89, 42, area | united | 0.02, scattered | ameriprise | 0.93, 6, area, hotspot |
| dogpatch | 1.00, 10, area | cleaners | 0.19, scattered | fidi | 1.00, 7, area, hotspot |
| nopa | 0.91, 4, area | acupuncture | 0.29, scattered | chinatown | 1.00, 10, area, hotspot |
| cow / hollow | 0.89 / 0.79, 7, area | repair | 0.31, 6, area | soma | 0.97, 38, area, hotspot |
| stonestown | 0.95, 4, area | state | 0.31, 5, area | tenderloin | 0.96, 12, area, hotspot |
| usf | 0.92, 4, area | merrill | 0.02, scattered | valencia | 0.93, 13, area, hotspot |

Vancouver: kitsilano 0.91 (32 cells), kerrisdale 0.95, marpole 0.97, dunbar 0.93, yaletown
0.96 (hotspot), gastown 1.00 (hotspot), langara 1.00, hastings 0.97, main 0.96, pleasant 0.98;
starbucks 0.00; ubc 0.41 (a university whose name is on shuttles and clinics across town).
Chicago: pilsen 0.95, bronzeville 0.98, wrigleyville 0.89, wicker 0.96, hyde 0.97,
englewood 0.96, beverly 0.91, andersonville 0.98, loop 0.96 (87 cells, hotspot), pullman
0.90, hegewisch 0.88; starbucks 0.08; logan 0.47 and village 0.50 (words shared by several
places). Toronto: leslieville 0.95, danforth 0.94, beaches 0.92, yorkville 0.94, kensington
0.91, roncesvalles 1.00, leaside 0.96, thorncliffe 0.96, mimico 0.95, scarborough 0.97 (94
cells); starbucks 0.00; king 0.38 and queen 0.63 (streets that run the length of the city).

The split inside one word is the point. "Sunset": 107 of 120 uses supported, 13 incidental,
and the 13 are the Sunset Dentals in other districts. "Hill": 0.75, with Nob, Russian, Potrero
and Bernal Hills as separate components of one core. "Presidio": 0.87 over 34 cells, with the
Presidio Heights uses and a few citywide ones in the tail.

What it does not do: separate a toponym in a dense district from the district's industry
words. llp, ubs and ameriprise are as supported as fidi and chinatown, because they are
genuinely contiguous. The *hotspot* flag marks all of them; telling them apart needs the word
itself (the lexicon's brand and generic classes) or the co-occurrence structure (a functional
cluster's core is shared with many other words of its kind, a toponym's is not). That is the
next test if this matters.

## Against the lexicon classes

Median pi by lexicon class (the lexicon never saw the geometry used here beyond its own
locality score; classes come from word lists, categories and brand shares):

| class | SF | Vancouver | Chicago | Toronto |
|---|---|---|---|---|
| division | 0.91 | 0.89 | 0.92 | 0.92 |
| mixed | 0.92 | 0.86 | 0.95 | 0.90 |
| street | 0.63 | 0.76 | 0.89 | 0.92 |
| area | 0.35 | 0.25 | 0.78 | 0.84 |
| institution | 0.15 | 0.38 | 0.84 | 0.90 |
| generic | 0.00 | 0.00 | 0.00 | 0.00 |
| brand | 0.02 | 0.00 | 0.00 | 0.00 |
| person | 0.03 | 0.00 | 0.08 | (none) |

The order is the one a toponymic model should give and it was not tuned to the lexicon. The
"area" class is the lexicon's broadest (547 words in SF) and the mixture splits it: in SF 26%
of area words have an area-sized core, 29% a point core, 45% no core. In Chicago and Toronto
the lexicon's area class is small and clean and the median pi is 0.8.

Overall: SF 4,357 words with five or more uses, 383 area, 680 point, 3,294 scattered;
Vancouver 3,105 / 207 / 378 / 2,520; Chicago 7,604 / 464 / 976 / 6,164; Toronto 7,496 / 344 /
784 / 6,368. About one word in ten has spatial support; about one in twenty has an area-sized
core.

## Reading

- Proximity works as evidence at the level of the single use, with no gazetteer. The model
  finds nopa, dogpatch, cow hollow, stonestown, leslieville and roncesvalles on the same
  footing as the official names, and it drops the Sunset Dentals.
- The toponymic share and the core are the honest version of "where a name holds": the
  coverage framing from 2026-10-08, now with the incidental uses taken out.
- It is a per-word model; words that name several places (hill, village, park, logan) get
  one pi and several cores, which is right for coverage and wrong for naming until the
  components are split, which the core components already give.
- The dense-district ambiguity is real and is the next test: co-occurrence of cores
  (how many other words share this core) should separate a district's name from its trade.

## Next

1. Use the posterior-weighted counts as the naming evidence in name recovery and in the
   lexicon (shared-layer branch): drop the tail, keep the core.
2. Core co-occurrence as the functional-cluster test.
3. Bandwidth sensitivity (0.7 and 1.5 cells) and resolution 8, to see which pi values move.
