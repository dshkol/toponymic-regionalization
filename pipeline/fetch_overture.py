"""Pinned Overture extracts for the four cities, one release for all.

Wraps the official client. Every extract gets a manifest in the same shape as
cadmus/demo/research/overture_places.py writes (source, release, bbox, sha256,
rows), so `places.Places` can open the place extracts unchanged. Refuses to
overwrite an existing extract.

    python3 pipeline/fetch_overture.py --city sf --type place
    python3 pipeline/fetch_overture.py --all
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '2026-08-19.0'  # The release of the cadmus SF extract. Do not mix.

# West, south, east, north. City limits with a small margin; under 2 degrees a side.
CITIES = {
    'sf': [-122.55, 37.68, -122.33, 37.84],       # cadmus bbox, kept identical
    'toronto': [-79.64, 43.58, -79.11, 43.86],
    'vancouver': [-123.23, 49.19, -123.02, 49.32],
    'chicago': [-87.95, 41.64, -87.52, 42.03],
}
TYPES = ('place', 'segment', 'division_area')
DOCS = {
    'place': 'https://docs.overturemaps.org/guides/places/',
    'segment': 'https://docs.overturemaps.org/guides/transportation/',
    'division_area': 'https://docs.overturemaps.org/guides/divisions/',
}


def path_for(city, type_, release=RELEASE):
    return ROOT / 'data' / city / f'overture-{type_}-{release}.parquet'


def manifest(path, bbox, release, type_):
    result = {'source': f'Overture {type_}', 'release': release, 'bbox': bbox,
              'recorded_at': datetime.now(timezone.utc).isoformat(),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'rows': pq.read_metadata(path).num_rows,
              'documentation': DOCS[type_],
              'filters': 'BBox only; all statuses and confidence values retained'}
    path.with_suffix('.manifest.json').write_text(json.dumps(result, indent=2))
    return result


THEME = {'place': 'places', 'segment': 'transportation', 'division_area': 'divisions'}


def read_bbox(type_, bbox, release=RELEASE):
    """The official client's query, done directly: the public bucket, anonymous,
    filtered on the per-row bbox columns. Used because the client insists on its
    STAC catalog host, which this network does not allow; S3 itself is reachable.
    Goes through HTTPS_PROXY when set."""
    import os
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    import pyarrow.fs as fs
    s3 = fs.S3FileSystem(anonymous=True, region='us-west-2',
                         proxy_options=os.environ.get('HTTPS_PROXY') or None)
    path = f'overturemaps-us-west-2/release/{release}/theme={THEME[type_]}/type={type_}/'
    dataset = ds.dataset(path, filesystem=s3, format='parquet')
    w, s, e, n = bbox
    expr = ((pc.field('bbox', 'xmin') < e) & (pc.field('bbox', 'xmax') > w)
            & (pc.field('bbox', 'ymin') < n) & (pc.field('bbox', 'ymax') > s))
    return dataset.to_table(filter=expr)


def fetch(city, type_, release=RELEASE):
    bbox = CITIES[city]
    out = path_for(city, type_, release)
    if out.exists():
        raise SystemExit(f'{out} exists; use a new path to preserve snapshots')
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix('.partial')
    table = read_bbox(type_, bbox, release)
    pq.write_table(table, tmp, compression='zstd')
    tmp.rename(out)
    m = manifest(out, bbox, release, type_)
    print(json.dumps({'city': city, 'type': type_, 'rows': m['rows'], 'path': str(out)}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city', choices=CITIES)
    p.add_argument('--type', choices=TYPES)
    p.add_argument('--all', action='store_true')
    p.add_argument('--release', default=RELEASE)
    a = p.parse_args()
    jobs = [(c, t) for c in CITIES for t in TYPES] if a.all else [(a.city, a.type)]
    for city, type_ in jobs:
        if path_for(city, type_, a.release).exists():
            print(json.dumps({'city': city, 'type': type_, 'skipped': 'exists'}))
            continue
        fetch(city, type_, a.release)


if __name__ == '__main__':
    main()
