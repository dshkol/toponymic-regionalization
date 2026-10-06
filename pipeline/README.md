# pipeline

The layer this project shares with Cadmus: pinned Overture extracts, a typed
toponym lexicon per city, and the tests that score it. Everything runs from
this directory with the system Python and `requirements-shared.txt`.

```
python3 fetch_overture.py --all            # places, segments, divisions per city (gitignored parquet + manifests)
python3 build_lexicon.py --all             # data/lexicon/<city>-<release>.{jsonl,cells.jsonl,summary.json}
python3 name_recovery.py --all             # notes/name-recovery/<city>-<release>.json
python3 vernacular.py --all                # notes/vernacular/<city>-<release>.md
python3 name_polygon.py --city sf poly.geojson   # ranked typed candidates for one polygon
python3 -m unittest test_names test_lexicon
```

| file | what it holds |
|---|---|
| `fetch_overture.py` | release, city bboxes, direct S3 read; refuses to overwrite a pinned extract |
| `places.py` | byte copy of Cadmus `demo/research/overture_places.py` (category groups) |
| `names.py` | Cadmus normalization, phrases, site key and the support cap, with its regression cases in `test_names.py` |
| `boundaries.py` | ground truth: SF official file; Toronto, Vancouver, Chicago derived from Overture divisions, marked provisional |
| `cells.py` | places to H3 cells, study-area cells |
| `lexicon.py` | per-phrase support, locality ratio, Moran's I, street/division/person/institution evidence, `classify()` |
| `given_names.py` | given-name set from the optional `gender-guesser` dictionary (nothing vendored) |
| `build_lexicon.py` | runs the above per city; `--resolution 8` writes tagged files |
| `features.py` | cell × term matrix for the regionalization step; streets stay in by default |
| `name_recovery.py` | Cadmus's lexical ranking on each official polygon; `--lexicon-tag=-r8` scores a tagged lexicon |
| `vernacular.py` | area terms no official or Overture polygon names, for gazetteer curation |
| `name_polygon.py` | Cadmus-compatible candidates for an input polygon |

Classes, in the order `classify()` tests them: brand, generic, mixed,
division, street, person, institution, landmark, point, area. The naming
channel is area + division + mixed; clustering features also take street,
landmark, institution and point. Numbers and the reasoning behind each rule
are in `../notes/2026-10-06-shared-layer.md`.
