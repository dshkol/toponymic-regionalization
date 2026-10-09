"""Bounded, provenance-preserving Overture Places extract.

Same pattern as cadmus/demo/research/overture_places.py: download one pinned release
for one bbox with the official client, then write a manifest (release, bbox, rows,
sha256) next to it. `verify` re-checks an existing extract against its manifest.

    python pipeline/fetch_places.py download --bbox=-122.55,37.68,-122.33,37.84 \
        --release 2026-08-19.0 --output data/sf/overture-sf-2026-08-19.0.parquet
    python pipeline/fetch_places.py verify data/sf/overture-sf-2026-08-19.0.parquet
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(path: Path, bbox, release):
    result = {'source': 'Overture Places', 'release': release, 'bbox': bbox,
              'recorded_at': datetime.now(timezone.utc).isoformat(),
              'sha256': sha256(path),
              'rows': pq.read_metadata(path).num_rows,
              'documentation': 'https://docs.overturemaps.org/guides/places/',
              'filters': 'BBox only; all statuses and confidence values retained'}
    path.with_suffix('.manifest.json').write_text(json.dumps(result, indent=2))
    return result


def verify(path: Path) -> dict:
    manifest = json.loads(path.with_suffix('.manifest.json').read_text())
    if sha256(path) != manifest['sha256']:
        raise ValueError(f'{path} does not match its manifest sha256')
    if pq.read_metadata(path).num_rows != manifest['rows']:
        raise ValueError(f'{path} row count differs from manifest')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    dl = sub.add_parser('download')
    dl.add_argument('--bbox', required=True, help='west,south,east,north')
    dl.add_argument('--release', required=True)
    dl.add_argument('--output', type=Path, required=True)
    vf = sub.add_parser('verify')
    vf.add_argument('extract', type=Path)
    args = parser.parse_args()
    if args.command == 'download':
        bounds = [float(x) for x in args.bbox.split(',')]
        w, s, e, n = bounds
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90) or e - w > 2 or n - s > 2:
            parser.error('Use a local bbox, at most 2 degrees per side')
        if args.output.exists():
            parser.error('Output already exists; use a new path to preserve snapshots')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(Path(sys.executable).with_name('overturemaps')), 'download',
                        '--bbox=' + args.bbox, '--release=' + args.release, '--type=place',
                        '-f', 'geoparquet', '-o', str(args.output)], check=True)
        print(json.dumps(write_manifest(args.output, bounds, args.release), indent=2))
    else:
        print(json.dumps(verify(args.extract), indent=2))


if __name__ == '__main__':
    main()
