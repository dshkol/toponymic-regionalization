# Toponymic regionalization — agent handoff

Status: new project, 2026-10-05. Nothing built yet. This document is the brief.
Owner: Dmitry Shkolnik. Sibling projects: `~/Projects/cadmus` (polygon naming) and
`~/Projects/regionalization-lab` (interactive lab on regionalization algorithms).

## The idea in one paragraph

Cadmus names an arbitrary polygon from the place names inside it. That is hard because
an arbitrary polygon straddles real places, so the evidence is mixed by construction.
Invert it: start from the place-name evidence and find the boundaries. Aggregate places
to small cells, describe each cell by the vocabulary of its place names, and run
contiguity-constrained clustering (regionalization) on those vectors. The regions that
come out are, by definition, areas where one naming signal dominates. Naming them is
then the easy case for Cadmus. Question to answer: **do place names alone carry enough
signal to recover a city's neighbourhoods, and at what scale?**

Dmitry's framing (verbatim intent): "linguistic / token / placename-based regionalization,
ideally in real time, related to Cadmus." Treat everything below as hypotheses to test,
not a spec to implement. He prefers small empirical checks over building the whole
pipeline first. Challenge the plan where the data disagrees with it.

## Cities

Four, chosen for having a published neighbourhood polygon set to evaluate against and
good Overture Places coverage:

| City | Ground truth polygons | Notes |
|---|---|---|
| San Francisco | DataSF Analysis Neighborhoods (41): https://data.sfgov.org/Geographic-Locations-and-Boundaries/Analysis-Neighborhoods/p5b7-5n3h | Cadmus already has an Overture extract (release 2026-08-19.0, bbox -122.55,37.68,-122.33,37.84, 60,536 rows) at `~/Projects/cadmus/demo/work/overture-sf-2026-08-19.0.parquet` with a sha256 manifest, plus a DataSF business-registration phrase index. Reuse both. |
| Toronto | City of Toronto Neighbourhoods (158): https://open.toronto.ca/dataset/neighbourhoods/ | Also has "social planning neighbourhoods" history; 158 is the current set. |
| Vancouver | City of Vancouver Local Area Boundaries (22): https://opendata.vancouver.ca/explore/dataset/local-area-boundary/ | Coarse (22 areas). Expect the method to find finer structure than the ground truth; treat disagreement at fine scale as a finding, not a failure. |
| Chicago | Community Areas (77): https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas/cauq-8yn6 | The canonical fixed set (Burgess, 1920s). Strong historical names (Hyde Park, Pilsen, Bronzeville) that businesses use. |

A fifth, if time: Montreal (quartiers) for a bilingual test of the tokenizer.

## Data

- **Places:** Overture Maps Places, one release pinned for all cities. Use the official
  `overturemaps` Python client (`pip install overturemaps`), `overturemaps download
  --type=place --bbox=...` to GeoParquet. Record release, bbox, row count and sha256 in a
  manifest exactly as `cadmus/demo/research/overture_places.py` does; copy that pattern.
  Fields needed: `names.primary`, `categories.primary`, `confidence`, geometry, `brand`.
- **Ground truth:** the four polygon sets above, GeoJSON, pinned by download date.
- **Cells:** H3 resolution 9 (~0.1 km², ~170 m across) clipped to the city polygon;
  try resolution 8 as a sensitivity check. `pip install h3`. Cells with zero places
  are kept in the graph (they are territory) but carry a zero vector; see floors below.
- **Contiguity:** H3 k-ring neighbours. Fully connected by construction except across
  water; check `connected_components` anyway and bridge if needed (helper in
  `regionalization-lab/companion/regionalization_lab.py`, `bridge_components`).

## Features per cell (the part most likely to need iteration)

1. Tokenize `names.primary`: lowercase, ASCII-fold, split on non-letters, drop stopwords
   and generic business words (the Cadmus 1-3-gram index already has a support-capped
   phrase list; start from its vocabulary).
2. Count tokens per cell, with the Cadmus support cap: a token counts at most once per
   distinct name and once per distinct site, so chains and stacked registrations do not
   dominate.
3. Weight by locality: tf-idf over cells, or better, the log ratio of a token's share in
   the cell to its share city-wide. Tokens that appear everywhere ("market", "cafe",
   brand names) must score near zero everywhere.
4. Reduce: the vocabulary is thousands wide and the cells are sparse. Options, in order
   of preference: (a) keep the top ~200 locality-weighted tokens and apply the centred
   log-ratio (the vectors are compositional, exactly like the Vancouver occupation
   shares in the lab); (b) truncated SVD to ~20 dimensions; (c) a small sentence
   embedding of the concatenated names per cell (last resort; harder to explain).
5. Optional second channel: `categories.primary` shares per cell, same treatment.
   Keep it separate so you can test names-only versus names-plus-categories.

## Methods

Use the Python companion from the lab as the starting harness
(`~/Projects/regionalization-lab/companion/regionalization_lab.py`); it already runs
every method below on a GeoDataFrame with a weights object and prints structure kept.

- **SCHC Ward** first. One run gives the whole merge tree. The first test of the whole
  idea is whether the tree recovers the known hierarchy (the Mission inside the eastern
  half inside SF) without being told. If it does not, stop and fix features before
  touching anything else.
- **SKATER** as the fast reproducible baseline.
- **Max-p** with a floor on *places per region* (not population), so k is endogenous
  and empty residential cells get absorbed until a region has enough evidence to be
  named. This is the formulation that matches the problem.
- **AZP** (annealing) to polish, started from SCHC.
- **SA3** if the noise concept helps: cells that belong to no stable naming region are
  a real category (industrial edges, parks, transitional strips).

Known library traps, all verified in the lab (see
`regionalization-lab/notes/python_verification.md`): rgeoda/pygeoda segfault on a
disconnected graph; libpysal `attach_islands` only fixes zero-neighbour units; Python
spopt's AZP default objective is pairwise and is worse than its start, pass
`ObjectiveFunctionCenter()`; spopt's SA/tabu classes do not construct in 0.8, use the
`AllowMoveAZPSimulatedAnnealing` strategy at low temperature; SA3 needs `fast_hdbscan`
and `numba`. The R `spopt` package's AZP and max-p search less well than rgeoda's.

## Evaluation

Against the ground-truth polygons, per city and per method:

- **Partition agreement:** adjusted Rand index and normalised mutual information between
  the cell labelling and the ground-truth label of each cell's centroid.
- **Boundary agreement:** share of region boundary length within 100 m / 250 m of a
  ground-truth boundary, and the reverse (recall of true boundaries).
- **Structure kept** (the lab's metric), with the unconstrained k-means ceiling and the
  random-contiguous floor at the same k, so the number means something.
- **Stability:** 20 seeds for max-p and AZP; map per-cell co-assignment. Unstable cells
  are the interesting ones.
- **Naming:** for SF only, feed each output region to the Cadmus engine
  (`POST /api/name-region`) and record whether it returns an established name with
  status `supported`. The hypothesis is that regionalized polygons score far better than
  arbitrary polygons do; the Cadmus test set gives the comparison.

Report all of this as tables in `notes/`, one file per experiment, dated. Negative
results are results.

## Real time

Not a first-phase goal. SCHC and SKATER on 10-20k H3 cells run in seconds in Python
and in milliseconds per city in the lab's browser implementation
(`regionalization-lab/lab/src/algorithms.js`, which is dependency-free and could be
reused in a Cadmus UI). Interactive recompute while a user drags a polygon is phase
three. The relevant literature if it gets there: PRUC (Liu, Alrashid, Magdy, VLDB
2022, doi:10.14778/3494124.3494133: feasible partition first, then improve), SMP
(SIGSPATIAL 2022, doi:10.1145/3557915.3561011), PAGE (ACM TSAS 2023,
doi:10.1145/3611011).

## Phases

1. **Signal check (do this first, one city).** SF, H3-9, names-only tokens, SCHC
   Ward. Plot the dendrogram cut at k = 5, 10, 20, 40 against the 41 DataSF areas.
   Compute ARI. Decide whether names carry signal. Budget: a day.
2. **Four cities, three methods.** Pipeline per city, evaluation tables, stability maps.
3. **Cadmus closure.** Name the SF regions with the Cadmus engine; compare against
   naming arbitrary polygons. Write up.
4. **Interactive.** Only if 1-3 justify it.

## Deliverables

- `pipeline/`: fetch (places, boundaries), cells + features, regionalize, evaluate.
  Python, pinned requirements, manifests with checksums for every download.
- `notes/`: dated experiment notes with tables; `notes/findings.md` for conclusions.
- A small static viewer (optional) using the lab's page as a template: map of cells,
  regions, ground-truth overlay, token cloud per region.

## Working rules (from Dmitry's standing preferences)

- This is a research tool. Plain interface, no branding or product polish.
- Make it its own git repo from the first commit (this folder already is).
- Commits end with the Claude co-author trailer; see the lab's git log for the form.
- Verify library calls by running them before writing them down anywhere.
- Prefer a small test that could kill the idea over a large build that assumes it works.
- Park side-findings in `notes/findings.md` rather than widening scope.

## Pointers

- Lab: `~/Projects/regionalization-lab` (README, `companion/`, `notes/`,
  `lab/src/algorithms.js`). Published page: see the project memory for the artifact link.
- Cadmus: `~/Projects/cadmus` (`README.md`, `demo/research/README.md`,
  `demo/research/overture_places.py`, `demo/reports/*.md`).
- Compositional treatment of share vectors: Aitchison (1982),
  doi:10.1111/j.2517-6161.1982.tb01195.x; the lab's cost section has the clr and
  Hellinger implementations in JavaScript.
