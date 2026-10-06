# Shared layer: data, lexicon and a first naming test — 2026-10-06

Follows [2026-10-06-cadmus-links.md](2026-10-06-cadmus-links.md), which named
the components both projects should share. This note records what was built
overnight, what the first numbers say, and what the data disagrees with in
`HANDOFF.md`. Everything here is from the cloud container except where the Mac
is named; nothing ran on the Mac.

## What exists now

| piece | file | status |
|---|---|---|
| Name normalization, 1-3-gram phrases, support cap | `pipeline/names.py`, `test_names.py` | cadmus's four `lexical.test.ts` cases pass, plus brand and digit cases |
| Overture places provider | `pipeline/places.py` | byte-identical copy of `cadmus/demo/research/overture_places.py` |
| Pinned extracts, four cities, one release | `pipeline/fetch_overture.py`, `data/<city>/*.manifest.json` | places, road segments, division areas; release `2026-08-19.0`; SF sha256 matches cadmus |
| Ground truth | `pipeline/boundaries.py`, `data/reference/` | SF official; others provisional (below) |
| Cells | `pipeline/cells.py` | H3 res 9 over the ground-truth union |
| Typed lexicon | `pipeline/lexicon.py`, `build_lexicon.py`, `data/lexicon/<city>-<release>.jsonl` | first-cut class rule |
| Feature matrix | `pipeline/features.py` | cell × term, class filter, optional clr |
| Naming test | `pipeline/name_recovery.py`, `notes/name-recovery/` | per-city JSON |

Run order: `fetch_overture.py --all`, `boundaries.py`, `build_lexicon.py --all`,
`name_recovery.py --all`. The container reaches the Overture bucket but not the
STAC catalog or any of the four city open-data hosts, so `fetch_overture.py`
reads S3 directly and the official polygon files cannot be fetched from here.

## Ground truth: Overture Divisions as a stand-in

Overture's division coverage differs a lot by city. Counting areas whose
representative point lies inside the city polygon:

| city | official set | Overture subtype | count | match |
|---|---|---|---|---|
| San Francisco | 41 analysis neighbourhoods | neighborhood 7, macrohood 1, microhood 21 (plazas) | unusable | official file from cadmus used |
| Vancouver | 22 local areas | macrohood | 22 | all 22 names are the City's local areas |
| Chicago | 77 community areas | macrohood | 73 | Logan Square, Humboldt Park, New City, Gage Park absent |
| Toronto | 158 neighbourhoods | neighborhood | 174 after de-duplication | the 158 plus vernacular areas (Kensington Market, Liberty Village, The Pocket, Parkdale) |

So the SF check cadmus's design notes asked for ("verify neighborhood and
microhood polygon coverage") has an answer: in SF, Overture divisions are not a
usable neighbourhood layer, and division overlap cannot be the primary canonical
signal there. Toronto and Chicago look as if Overture ingested the official
sets; Vancouver exactly. Treat the derived sets as provisional until the
official files are in `data/reference/`. The baseline thread has asked for
those files; this note does not repeat the ask.

Cell counts at res 9: SF 1,242 cells (1,117 with a place). `HANDOFF.md` says
"10-20k H3 cells" per city; SF is an order of magnitude smaller than that. The
lab's browser algorithms are more than enough; this also means the stability
and max-p runs will be fast.

## Lexicon method

`build()` in `pipeline/lexicon.py`. Per 1-3-gram phrase with at least 3 support
units citywide:

- support under the cadmus cap, per cell and citywide;
- `locality`: cadmus's smoothed log rate ratio, inside versus rest of city, over
  the best 1-ring H3 disk (7 cells, about 0.7 km²) that holds at least 3 units.
  One fixed zone size, so numbers compare across phrases and cities. The
  per-cell version was tried first and is useless: a single unit in a cell with
  three sites gives a huge ratio;
- Moran's I over H3 first-ring contiguity, top-5%-cell share, standard distance;
- brand share (Overture `brand`), landmark share (taxonomy groups
  `geographic_entities`, `cultural_and_historic`, plus a category list);
- `is_street`: the phrase equals a drivable road's name with generic words
  removed (`Valencia Street` → `valencia`); `is_division`: same against
  neighbourhood-type divisions and the ground-truth names, with joined names
  split (`Castro/Upper Market` → `castro`, `upper`).

Class rule (`classify()`), in order: brand (declared brand on a quarter of
records, or units/records ≤ 0.2, i.e. identical names collapsing), generic
(no disk reaches 3 units, locality under 1.0, or standard distance over 3 km),
mixed (division and street), division, street, landmark (majority of records),
point (one cell), area. The thresholds are hypotheses. Two are known to be
blunt: `names.STOP` contains `market`, `park`, `center`, so `Upper Market`,
`Glen Park` and `Civic Center` reduce to `upper`, `glen`, `civic`; and
institutions with campuses (UCSF, SFSU, Kaiser, CPMC) land in `area` because
Overture files them under health care or education, not landmarks. An
`institution` class would be the next split.

Two fixes made during the night, both visible in the other cities first:
brand share counts a record only when the phrase is part of the declared
brand's own name, not when the record merely has a brand (`Tim Hortons Davie
St` was making `davie` a brand); and street and division names drop a leading
direction (`North Western Avenue` → `western`) and split on hyphens
(`Kensington-Cedar Cottage`), since Chicago prefixes almost every road and
Toronto hyphenates almost every neighbourhood.

Per city (seconds are the whole build on one core):

| city | places | cells (res 9) | phrases ≥3 units | area | division | mixed | street | landmark | institution | point | person | brand | generic | s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SF | 60,536 | 1,242 | 8,095 | 732 | 27 | 13 | 201 | 33 | 170 | 34 | 62 | 100 | 6,729 | 10 |
| Vancouver | 43,096 | 1,392 | 5,773 | 533 | 15 | 10 | 103 | 19 | 34 | 31 | 25 | 116 | 4,887 | 7 |
| Toronto | 162,551 | 6,106 | 15,115 | 182 | 30 | 39 | 171 | 33 | 33 | 62 | 2 | 392 | 14,175 | 24 |
| Chicago | 197,853 | 5,790 | 15,069 | 260 | 14 | 13 | 62 | 40 | 91 | 77 | 6 | 361 | 14,152 | 27 |

`institution` is a phrase whose records are mostly in Overture's education or
health-care groups (or `campus_building`): UCSF, SFSU, Kaiser, CPMC; DePaul,
UIC, IIT, Northwestern Memorial; UofT, YorkU, CAMH, Mount Sinai; UBC, Emily
Carr, VCC. It is McKenzie's university false positive as its own class, and it
also absorbs the medical trade words (surgery, oncology, naturopathic) that
had sat in `area`. Humber stays `area` because the river, park and college
share the name below the majority. It costs Toronto four polygons whose only
local evidence is a school or clinic carrying the neighbourhood's name
(Pleasant View, Centenary, Alton Towers, Bayview Glen): when the name of the
place is the name of the area, the class cannot tell, and the division list
should. For clustering features the class stays in (a campus is a region);
for naming it is out.

`person` is the newest class: every token a common given name in Great
Britain, Ireland or the U.S.A. (frequency ≥4 of 13 in the dictionary inside
the `gender-guesser` package, read at build time, not vendored). It takes
Jennifer, Robert, Morgan Stanley, Raymond James out of `area` (SF 62,
Vancouver 25) and leaves Marina (3), Noe (1) and every division and street
alone, since those rules run first. Name recovery does not move, which is
the point: these were never top terms, they were noise in the feature
vocabulary.

Toronto and Chicago have far more generics in proportion. Part of that is real
(bigger cities, more chains), part is the 3 km standard-distance rule biting
harder where neighbourhoods are larger and further apart; it is the first
threshold to revisit with the official polygons in hand.

SF detail: 8,095 phrases; generic 6,729, area 948, street 201, brand 100,
landmark 43, point 34, division 27, mixed 13. Spot check of 45 known names
(`scratchpad`, reproduced in the summary JSON): Mission, Castro, Sunset, Marina,
Presidio are `mixed` (a street and an area share the name); Valencia, Haight,
Noe, Potrero, Fillmore, Polk, Divisadero are `street`; Noe Valley, Tenderloin,
Chinatown, Nob Hill, Hayes Valley, Russian Hill, Japantown are `division`; SoMa,
Dogpatch, Bernal, Bayview, Richmond, Cole Valley are `area`; Starbucks and
Walgreens are `brand`; Golden Gate, Ocean, Photography, Moving, Bay Area are
`generic`. The McKenzie false-positive kinds come out as their own classes
rather than as noise, which is what the links note argued for.

## Name recovery: does the lexicon name the official polygons?

`name_recovery.py` runs cadmus's lexical ranking (inside-vs-rest log ratio ×
log1p(support), cap, floor of 3) on the places inside each ground-truth polygon
and asks whether the top phrase is part of the official name. No boundary
overlap, no model: a lexical-only ceiling, and a test of the class column.

Exact: the top phrase is a part of the official name (`noe valley`). Partial:
every token of the top phrase is in the name (`richmond` for Outer Richmond).
"None" is polygons where no phrase reaches 3 units in the vocabulary.

| city | polygons (status) | term set | top-1 exact | top-1 partial | top-3 exact | none |
|---|---|---|---|---|---|---|
| SF | 41 (official) | all non-generic, non-brand | 0.34 | 0.51 | 0.63 | 2 |
| SF | 41 | area channel (area, division, mixed) | **0.56** | 0.68 | 0.66 | 2 |
| Vancouver | 22 (derived, = local areas) | all | 0.45 | 0.50 | 0.73 | 0 |
| Vancouver | 22 | area channel | 0.50 | 0.55 | **0.77** | 0 |
| Toronto | 174 (derived, 158 official + 16) | all | 0.24 | 0.33 | 0.31 | 39 |
| Toronto | 174 | area channel | **0.30** | 0.35 | 0.31 | 43 |
| Chicago | 73 (derived, community areas) | all | 0.16 | 0.21 | 0.22 | 17 |
| Chicago | 73 | area channel | **0.19** | 0.22 | 0.23 | 18 |

Per-polygon detail is in `notes/name-recovery/<city>-2026-08-19.0.json`. The
area-channel rows are after the `person` and `institution` classes were
added; before them SF was 0.54 / 0.66 / 0.63, Vancouver 0.45 / 0.50 / 0.77,
Toronto 0.29 / 0.35 / 0.31 with 39 unnamed, Chicago unchanged. The "all" rows
include both classes and do not move.

Keeping streets and landmarks out of the term set raises SF top-1 from 14/41
to 22/41 without lowering top-3. Streets are bad *names* for areas. The
baseline thread's SF signal check found the opposite for *clustering*: dropping
street tokens lowered agreement with DataSF (ARI 0.15 to 0.10 at k = 20),
because at cell scale a business on Valencia is in the Mission. Both hold, and
they settle the channel question from the links note: street terms stay in the
clustering features (`features.DEFAULT_CLASSES`) and leave the naming vocabulary
(`name_recovery.AREA`). Exclusion in `features.py` is a per-class switch, not a
rule. The misses are more informative than the hits:

- vernacular beats official: South of Market → `soma`; Western Addition →
  `fillmore`; Potrero Hill → `dogpatch`; North Beach → `wharf`; Lakeshore →
  `sfsu`; West of Twin Peaks → `west portal`, `lakeside`;
- parent beats child: Inner and Outer Richmond → `richmond`; Outer Mission →
  `excelsior`, `mission`; Bayview Hunters Point → `bayview`;
- no signal: Seacliff (18 places), McLaren Park (31), Golden Gate Park and
  Lincoln Park return landmarks inside them;
- a brand the brand rule missed: Financial District/South Beach → `morgan
  stanley`, `ubs`, because Overture declares no brand on those offices and the
  names are not identical.

Chicago and Toronto score low for the same reason, and it is the most useful
thing in the table. The lexicon's top terms there are the names businesses use,
which are not the official polygon names:

- Chicago: Near North Side → `river north`, `streeterville`; Near West Side →
  `uic`, `west loop`; Near South Side → `south loop`; West Town → `bucktown`,
  `river west`; North Center → `roscoe village`; Lower West Side → `pilsen`,
  `little village`; Douglas → `iit`, `bronzeville`; Forest Glen → `edgebrook`;
  Portage Park → `six corners`. The 77 community areas are the 1920s fixed
  set; the lexicon recovers the living neighbourhood names instead. The brief
  expected community-area names to be the ones businesses use. For the ones
  near downtown they are not; further out (Hegewisch, Roseland, Mount
  Greenwood, Lincoln Square, Edgewater, Lake View) they are.
- Toronto: the 158 are census-style hyphenated units (Agincourt South-Malvern
  West, Greenwood-Coxwell). The lexicon returns `leslieville`, `east york`,
  `greektown`, `beaches`, `cabbagetown`, `little italy`, `corktown`,
  `bloorcourt`, which are real places with no polygon in the official set,
  and 39 of 174 polygons have no area-term with 3 units at all.
- Vancouver's 22 local areas are the names people use (Kitsilano, Kerrisdale,
  Mount Pleasant), and the score is close to SF's. Vernacular sub-areas still
  show up: `yaletown`, `gastown`, `olympic village`, `south granville`.

For the regionalization this says: expect the name-evidence regions to follow
vernacular areas where those differ from the official polygons, and score that
as a finding, not an error. ARI against the Chicago community areas or the
Toronto 158 will understate what the names recover; the lexicon's own top terms
per region are the better readout there, and `name_recovery.rank_inside` gives
them in the form cadmus will use. For cadmus: a lexical top-1 of roughly half,
top-3 of two-thirds, is the ceiling for names-only on polygons with clean edges
whose official names are vernacular (SF, Vancouver); arbitrary polygons will be
lower, and cities whose official names are administrative will look worse than
the evidence is.

Coverage: of the 1,242 SF cells, 728 carry at least one of the top-200 area
terms. The other 41% have no area-name evidence at res 9. Max-p's
places-per-region floor (`HANDOFF.md`) is the right tool for that; a fixed k
would split evidence-free territory arbitrarily.

## Vernacular candidates

`pipeline/vernacular.py` lists, per city, the `area` phrases whose tokens occur
in no official or Overture polygon name, ranked by the lexicon score, with the
peak cell for review: `notes/vernacular/<city>-2026-08-19.0.md`. The top of
each list is what cadmus's design notes called the "unavoidable hand-curated
vernacular gazetteer", found rather than typed: SF Stonestown, Dogpatch,
Fishermans Wharf, Crocker Amazon, Shipyard, Candlestick, Lands End; Toronto
Leslieville, Corktown, Bloorcourt, Golden Mile, Roncy, Queens Quay, Stockyards;
Vancouver Yaletown, Gastown, English Bay, Olympic Village, Coal Harbour, Kits,
River District; Chicago Pilsen, Bronzeville, Bucktown, Edgebrook, Little
Village, Streeterville, Roscoe Village. Institutions (UCSF, SFSU, UTSC, DePaul,
IIT) and financial-district business words (private banking, wealth, PhD) are
in the same lists and need the human pass.

## Resolution sensitivity: res 8 against res 9

HANDOFF.md asks for a res-8 check. `build_lexicon.py --resolution 8` writes
tagged files (`<city>-<release>-r8.*`); `name_recovery.py --lexicon-tag=-r8`
scores them. Same places, same cap; only the cells and the 1-ring disk that
the locality ratio is computed on change (about 0.1 km² × 7 at res 9, about
0.7 km² × 7 at res 8).

| city | area hit1 / hit3, res 9 | res 8 | polygons with no top term, res 9 | res 8 |
|---|---|---|---|---|
| sf | 0.54 / 0.63 | 0.51 / 0.63 | 2 | 2 |
| vancouver | 0.46 / 0.77 | 0.50 / 0.77 | 0 | 0 |
| toronto | 0.29 / 0.31 | 0.29 / 0.32 | 39 | 46 |
| chicago | 0.19 / 0.23 | 0.25 / 0.30 | 17 | 12 |

The wider disk moves phrases from `generic` into `area` (SF 948 → 1705,
Chicago 324 → 548 area terms) because a 5 km² disk holds enough units for
the ratio where seven res-9 cells did not. That admits names the res-9 run
had called generic (Chicago Bucktown, Logan Square, Little Village, Roscoe
Village, Wrigleyville; Toronto Roncy, Jane Finch, Humbertown) and improves
Chicago, whose community areas are large. It also admits more business words
(Vancouver "mining", "resources"), and SF slips a little. Res 9 stays the
default; the res-8 summaries are committed, the full res-8 lexicons are not
(they are a rebuild of 60 s). The HANDOFF question is answered as "the scale
of the locality disk matters more than the cell size": a per-term disk
radius, chosen by support, is the better fix than a global resolution.

Tried next, in `lexicon.py` (`SCALES`, `SCALE_SUPPORT`): take the ratio over
both the 7-cell and the 19-cell disk at res 9 and keep the better. With the
same three-unit floor at both scales, Chicago area hit1 rose 0.19 → 0.25 and
Toronto's unnamed polygons fell 39 → 37, but SF moved 443 phrases from
generic to area, led by first names and trades (karen, psychiatry, ryan,
sam): three units anywhere inside 2 km² pass the ratio. Asking the wider
disk for four units keeps 114 of those and only two of the Chicago polygons;
asking for six gives back the res-9 result exactly. The Chicago gains are
rare terms (Auburn Gresham, West Pullman, Lakeview East, Near West Side,
Noble Square, Hyde Park Kenwood), so the trade is recall on names with 3–5
mentions against precision on everything else with 3–5 mentions. `SCALES`
stays `(1,)`; the mechanism is in the code with the numbers above so the
next pass can pair a wider disk with a person-name list, which is the
filter these false positives actually need.

## Naming a polygon the Cadmus way

`pipeline/name_polygon.py --city sf polygon.geojson` returns ranked typed
candidates for one polygon: lexicon phrases found inside under the support
cap, with the inside-vs-rest log ratio, their class, units and examples.
It is the lexical-candidate alternative cadmus's ranking trial asked for
(its evidence packet lists repeated words only as diagnostics because raw
repetition ranks "San Francisco" first). Run on the four polygons in
`cadmus/demo/outputs/model-experiment/`:

| polygon | km² | places | naming channel (area, division, mixed) | with streets and landmarks |
|---|---|---|---|---|
| dolores-area | 0.13 | 77 | mission | dolores, guerrero, mission |
| corridor (Valencia) | 0.34 | 599 | mission, then business words | valencia, mission, bartlett, parklet |
| mission | 4.9 | 4,921 | mission, raza, tarot, latino, vida | valencia, mission, guerrero, shotwell |
| mixed (Mission + Bernal) | 7.7 | 5,833 | bernal, mission, raza, latino | valencia, bernal, mission, guerrero, precita |

The area channel gets the neighbourhood right on all four and splits the
mixed polygon into its two parts; the street channel names the corridor and
the small block, which is what cadmus's expression types (corridor, block)
want. Below the first one or two terms the area channel is cultural
vocabulary (raza, latino, floreria), useful as evidence and wrong as a name;
a caller should take the top term by class, not the list. Output has no
extent and no boundary overlap: that is what cadmus's engine adds.

## Changes this suggests to HANDOFF.md

1. Cells: "10-20k" → about 1.2k for SF at res 9; check the other cities in
   `data/lexicon/*.summary.json`.
2. Features step 1: vocabulary from this lexicon, classes area + division +
   mixed, not from the cadmus registration index (see the links note).
3. Evaluation: add name recovery per region as a metric alongside ARI, using
   `name_recovery.rank_inside` on the regionalization output. It is the Phase 3
   closure without the cadmus engine's circularity.
4. Ground truth: Vancouver can proceed on the Overture macrohoods; Chicago on 73
   of 77; Toronto waits for the official file or filters the 174 to the 158.

## Open

- Thresholds in `classify()` are untested beyond SF; the other cities' summaries
  will show whether 3 km and locality 1.0 travel.
- Toronto and Vancouver names are English-only here; Montreal would need the
  tokenizer revisited (accent folding is in, French stopwords are not).
- Chicago has a 98-polygon "Neighborhoods" layer on its open-data portal, and
  Toronto has no official vernacular layer at all. Scoring the lexicon against
  Chicago's neighbourhood layer would separate "the lexicon is wrong" from "the
  community areas are not what people say"; the host is blocked from here.
- `morans_i` replaces `esda.Moran` per phrase with one sparse product (equal to
  1e-17 on SF); the whole four-city build is under 70 s.
