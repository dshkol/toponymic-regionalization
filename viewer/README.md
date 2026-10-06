# Results viewer

A single static page that shows the four-city signal check on a map: H3-9 cells coloured by
SCHC Ward region (names with one ring of smoothing, names unsmoothed, or coordinates only) at
each k, the ground-truth outlines, lifted tokens per region on hover, and the ARI table from
the dated notes. No build step and no external libraries; the map is a plain canvas.

Regenerate the data after a pipeline change (same code path as `run_city.py`, so the labels
are the ones the notes score):

    for c in sf vancouver chicago toronto; do python pipeline/export_viewer.py --city $c; done

View it locally:

    python3 -m http.server -d viewer 8765   # then open http://localhost:8765/

`data/<city>.json` is committed because it is a result, not an input: about 3 MB in total,
derived from the pinned Overture extracts whose manifests live next to them under `data/`.

Published copy (private link): https://claude.ai/artifact/JZnJQHPi3AbSPoXGSVErxN
