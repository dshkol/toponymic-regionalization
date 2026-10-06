# What this project and Cadmus should share — 2026-10-06

Cadmus names a polygon that someone else drew. This project draws the polygons
from name evidence and then names them. Both read the same evidence: named places
inside an area. The two projects should share the evidence layer and keep their
decision layers separate.

Sources read for this note: `HANDOFF.md` in this repo; in `~/Projects/cadmus`, the
`README.md`, `demo/lib/lexical.ts`, `demo/research/{README.md, prior-art-and-task.md,
overture_places.py, support.py}`, and the reports `research-iteration-1.md`,
`overture-source-audit.md`, `overture-evidence-trial.md`,
`overture-ranking-trial.md` and `first-human-calibration.md`; the
regionalization-lab README. Nothing was run. Statements about Cadmus describe its
state on 2026-09-12.

## Corrections to HANDOFF.md first

Four assumptions in the brief do not match what Cadmus contains. Each one
changes a phase.

1. **The 1-3-gram phrase index is built from DataSF business registrations, not
   Overture.** It has 8,369 phrases from 98,893 registration rows. Cadmus's own
   source audit replaced that source: in the same polygons, 17-27% of
   registration names are address-like, against 4-8% for Overture. Reuse the
   index's *method* (normalization, support cap). Do not seed the vocabulary from
   it. Rebuild the vocabulary from Overture for every city, so that SF is not the
   one city with a different input.
2. **Cadmus has no naming test set to compare against.** Its tests are behaviour
   tests, and its README says "known boundaries are available to the ranker".
   The only human labels are three SF development polygons (Valencia corridor,
   Mission, Dolores area) with eight accepted expressions. Phase 3 has to build
   its comparison set of arbitrary polygons, and it has to be labelled
   before the regionalized polygons are named.
3. **Naming SF regions with `POST /api/name-region` is circular.** The browser
   engine names by area overlap with the DataSF 41 analysis neighbourhoods.
   Those 41 polygons are also this project's SF ground truth. A `supported`
   status then measures agreement with the 41 polygons a second time, which ARI
   already measures. Lexical evidence does not change the engine's label at all.
   For the Phase 3 closure, use Cadmus's contained-evidence path
   (`research/resolve.py`, Overture only, no reference boundaries), or a
   reviewed label set. Toronto, Vancouver and Chicago have no Cadmus coverage.
4. **Cadmus does not treat landmarks, streets, universities and stations as
   false positives.** McKenzie et al. (2018) list six false-positive kinds
   (landmarks, universities, major streets, broader regions, transit stations,
   companies). They are false positives only because the target there is
   neighbourhood names, and the authors note that some are real colloquial
   usage. Cadmus's position is that for naming
   these are valid referring terms. Two of the three human-accepted SF answers
   are street-based ("Valencia Corridor", "Mission - Van Ness"). The draft
   project instruction "treat landmarks… as likely false positives" therefore
   applies to this project's *features*, not to naming. See component 3.

## Components to share

### 1. Places provider — share as is

`cadmus/demo/research/overture_places.py` does the work this project needs. It
downloads with the official client, requires a pinned release and a bounded
bbox, writes a sha256 manifest, refuses to overwrite a snapshot, and rejects
modified extracts. It queries exact polygon containment (boundary included,
holes excluded) and keeps GERS IDs, brand, confidence, operating status and
both taxonomy fields. Copy it into `pipeline/`. Keep the file identical, so
that later changes can go back to Cadmus.

Use one release for all four cities. Cadmus's SF extract is `2026-08-19.0`.
If that release is no longer downloadable, pull SF again with the new release.
Do not mix releases across cities.

Cadmus's evidence path also drops explicitly closed and unnamed records, and it
groups the same normalized name at the same site. Apply the same exclusions here,
so that a token count in one project means the same thing in the other.

### 2. Name normalization and support cap — share one implementation

Cadmus's rule (`lexical.ts`, "Lexical support v0.2"):

- site key = longitude and latitude rounded to 5 decimals (about 1 m);
- a phrase's support in a zone = `min(distinct normalized names, distinct sites)`;
- a phrase needs at least 3 support units to count;
- the corroboration ranking (`anchor_ranking.py`) also caps by declared brand
  identity and ignores self-name and same-site support.

For this project the zone is an H3 cell. Most res-9 cells will have fewer than
3 units for any token, so apply the floor-of-3 at the *region* level (the
max-p floor), not per cell. Inside a cell, keep the cap. Today Cadmus has this
rule only in TypeScript, plus a partial Python version in `anchor_ranking.py`.
Write one Python module here (`pipeline/names.py`) with tests carried over from
Cadmus's regression cases (the four "Green Strategies" variants at one site
give one unit). Cadmus's research path can then import it.

### 3. Typed toponym lexicon — the main shared artifact, build it here

The handoff's per-cell token matrix is already most of a McKenzie-style offline
lexicon. Cadmus's design notes propose that lexicon ("build a toponym lexicon
offline, once… at query time you only count lexicon hits"), and its ranking
trial gives the reason: query-time repetition alone ranks "San Francisco"
above local names in the Mission. Build the lexicon once per city, from the
support-capped token-by-cell counts, and write it as a file both projects read:

| field | use here | use in Cadmus |
|---|---|---|
| support (names, sites, brands) | eligibility | eligibility |
| locality ratio vs city | feature weight | specificity prior |
| spatial statistics (Moran's I, Getis-Ord hot-spot extent, McKenzie's set) | feature weight | geographic-term filter |
| class: area / street / point landmark / brand / generic / city name | which channel the token enters | which relation it supports (`within`, `along`, `near`) |
| linked place concept (e.g. Mission → neighbourhood, Mission St, Mission Dolores Park) | split one string into concepts | Cadmus decision 1: a string is not one entity |

The class column is how the McKenzie false-positive finding is applied correctly.
Street tokens spread along a line and cross neighbourhood boundaries. Mission
Street runs through several areas. If street tokens go into the area-feature
vector, they pull the clustering toward corridors. Point landmarks (a station, a
university) put a strong token in one or two cells. Here, area-class tokens
make the main feature channel. Street and landmark tokens go to a separate
channel or are left out. Cadmus uses all classes, each for its own relation.
Classify streets mechanically by matching tokens to Overture Transportation
segment names. Landmarks come from categories plus review. Cadmus already flags
park records with transit-stop names and school records with organization
names, and those flags carry over.

Phase 1 needs only support and locality. Add the class column before Phase 2.
Without it, the SF result will mix name signal with the street grid.

### 4. Scale — one hierarchy, read two ways

The two projects handle scale with different tools, and the tools fit together.

- Cadmus gates by polygon size: the point-evidence `near` relation is disabled
  above 0.5 km². The engine thresholds are 80% dominant area, 65% inclusion
  before qualifying, composites of 2-3 areas at least 12% each and 85% together,
  and query limits of 10 m² to 2,000 km². The human calibration showed these
  gates are too strict: Mission (4.88 km²) never reached the model.
- This project gets a merge tree from SCHC and an evidence floor from max-p.

Connect them: the SCHC dendrogram is the hierarchy that Cadmus's expression
types need. A Cadmus "parent + qualifier" ("Mission - Dolores") is a node and
one of its children. A composite is two siblings. "No good name" is a node whose
token distribution has no dominant area-class term. Two things should therefore be
the same in both projects: (a) the evidence floor, which is max-p's
places-per-region floor here and Cadmus's support floor of 3 there; (b) the
region sizes at which the tree is cut, given in km² so that the cut matches
Cadmus's area gates. Report results by tree level in km², not only by k. A k
does not carry over between cities. An area does.

H3 res 9 versus res 8 is a separate scale question. Res 9 cells (~0.1 km²) are
smaller than Cadmus's 0.5 km² gate. Res 8 cells (~0.7 km²) are larger. So
Phase 1 at res 9 can represent everything Cadmus can name.

### 5. Evaluation fixtures — share the loaders and the three SF cases, nothing else

Share the ground-truth loaders and their manifests. Use Cadmus's three reviewed
SF polygons as sanity checks: a working SF result should produce a Valencia
corridor or an equivalent region, and a Mission/Dolores split at some tree
level. They are development cases and must not be used as a test. Cadmus loads
the *original* DataSF neighbourhood geometry, because two simplified polygons
(Marina and Bayview Hunters Point) fail Shapely validation. Do the same.

## Keep separate

- The Cadmus browser engine and its DataSF boundary-overlap logic. It is SF
  only and circular for evaluation here.
- The Cadmus LoRA pilot (Qwen2.5 1.5B). It distils a rule policy and is not a
  naming model.
- The regionalization methods. They stay in the lab's companion harness. Cadmus
  does not need them unless it splits a drawn polygon (see below).

## Where the real-time regionalization papers fit

The Magdy group's papers solve **scale**: max-p and p-regions on hundreds of
thousands to millions of units.

- **PRUC**, P-Regions with User-Defined Constraint (Liu, Alrashid, Magdy; PVLDB
  15, 2022; doi:10.14778/3494124.3494133). It builds a feasible partition into p
  regions under a SUM-style constraint, then improves it.
- **SMP**, Scalable Max-P Regionalization (SIGSPATIAL 2022 poster;
  doi:10.1145/3557915.3561011). Randomized construction, then heuristic
  improvement, on datasets an order of magnitude larger than earlier methods
  handle.
- **PAGE**, Parallel Scalable Regionalization Framework (Alrashid, Liu, Magdy;
  ACM TSAS 2023; doi:10.1145/3611011). A parallel, partitioned version of the
  same two-stage method.
- Also found while checking these: "Towards Scalable and Expressive Spatial
  Grouping Queries" (SIGSPATIAL 2024, doi:10.1145/3678717.3695757). Not read.

This project's scale is 10-20k H3 cells per city. The lab's SCHC and SKATER
already run in milliseconds at that size in the browser. So city scale is not a
use case for these papers. They become relevant in three cases:

1. **Max-p with the places floor at metro or national extent.** SMP and PAGE are
   the methods to use if the project moves past four cities, for example to all
   of Overture for one country. PRUC's user-defined constraint has the same form
   as the places-per-region floor, so its feasibility phase applies directly.
2. **Interactive re-cutting is a hierarchy problem, not a scale problem.** When a
   user moves a k or floor slider, the SCHC tree cut is instant without
   recomputing. Use the tree for this before reaching for incremental max-p.
3. **The Cadmus closure in real time.** When a user draws a polygon that
   straddles places, regionalize only the cells inside it, then name each part.
   That gives Cadmus a principled composite ("Mission - Bernal Heights") in place
   of its 12%/85% heuristic. The problem is small, a few hundred cells, so the
   lab's `algorithms.js` can run it inside the Cadmus UI. None of the papers
   cover regionalization constrained inside a query polygon. That is the
   original contribution if Phase 4 happens.

Put the papers in the Phase 4 reading list with this framing. Do not add them
to Phases 1-3.

## Suggested order

1. Phase 1 as briefed, with corrections 1 and 4 applied: vocabulary from
   Overture, street tokens kept out of the name channel (exact-match on
   Overture street names is enough here).
2. Before Phase 2: `pipeline/names.py` (component 2), and the lexicon file with
   the class column (component 3).
3. Before Phase 3: label a set of arbitrary SF polygons blind, then name both
   the regionalized and the arbitrary polygons through Cadmus's
   contained-evidence path.
4. Phase 4 only if 1-3 hold up: in-polygon regionalization for Cadmus.

## References

- McKenzie, Liu, Hu & Lee (2018), Identifying urban neighborhood names through
  user-contributed online property listings, *ISPRS IJGI* 7(10), 388.
  https://grantmckenzie.com/academics/McKenzie_Neighborhoods2018.pdf
- Hu & Janowicz (2018), POI name localness, GIScience 2018,
  doi:10.4230/LIPIcs.GISCIENCE.2018.5.
- Hu, Mao & McKenzie (2018), arXiv:1809.02824: clustered false positives
  include non-place realtor names, so clustering alone does not fix chains.
- Turner, Sripada & Reiter (2009), Generating approximate geographic
  descriptions, ENLG. https://aclanthology.org/W09-0607.pdf
- Dale & Reiter (1995), arXiv:cmp-lg/9504020.
- Liu, Alrashid & Magdy, PRUC, PVLDB 15 (2022), doi:10.14778/3494124.3494133.
- SMP, SIGSPATIAL 2022, doi:10.1145/3557915.3561011.
- Alrashid, Liu & Magdy, PAGE, ACM TSAS (2023), doi:10.1145/3611011.
