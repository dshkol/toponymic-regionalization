"""Bounded, provenance-preserving Places input, independent of SF reference data.

Download with the official client, then query exact polygons locally. No model,
outside-ring dependency, or implicit conversion of a point into an area boundary.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from shapely import from_wkb
from shapely.geometry import box, mapping, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'work/overture-sf-2026-08-19.0.parquet'


class Places:
    def __init__(self, path=DEFAULT):
        self.path = Path(path)
        self.manifest = json.loads(self.path.with_suffix('.manifest.json').read_text())
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != self.manifest['sha256']:
            raise ValueError('Extract does not match manifest')
        self.extent = box(*self.manifest['bbox'])
        self.rows = []
        self.points = []
        seen = set()
        for row in pq.read_table(self.path).to_pylist():
            if row['id'] in seen:
                raise ValueError('Duplicate GERS ID in extract')
            seen.add(row['id'])
            point = from_wkb(row.pop('geometry'))
            if point.geom_type != 'Point' or point.is_empty or not point.is_valid:
                raise ValueError('Invalid place geometry')
            row['geometry'] = mapping(point)
            row['name'] = (row.get('names') or {}).get('primary')
            row['category'] = ((row.get('taxonomy') or {}).get('primary')
                               or (row.get('categories') or {}).get('primary'))
            self.rows.append(row)
            self.points.append(point)
        self.tree = STRtree(self.points)

    def query(self, geometry):
        region = shape(geometry)
        if region.geom_type not in ('Polygon', 'MultiPolygon') or region.is_empty or not region.is_valid:
            raise ValueError('Expected a valid nonempty Polygon or MultiPolygon')
        if not self.extent.covers(region):
            raise ValueError('Polygon exceeds extract coverage; fetch a covering extract first')
        # Boundary points included; points in holes excluded. No source/status
        # filtering here: downstream policies must state their exclusions.
        return [self.rows[int(i)] for i in sorted(self.tree.query(region, predicate='covers'))]


def manifest(path, bbox, release):
    result = {'source': 'Overture Places', 'release': release, 'bbox': bbox,
              'recorded_at': datetime.now(timezone.utc).isoformat(),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'rows': pq.read_metadata(path).num_rows,
              'documentation': 'https://docs.overturemaps.org/guides/places/',
              'filters': 'BBox only; all statuses and confidence values retained'}
    path.with_suffix('.manifest.json').write_text(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    download = sub.add_parser('download')
    download.add_argument('--bbox', required=True, help='west,south,east,north; bounded local extract')
    download.add_argument('--release', required=True)
    download.add_argument('--output', type=Path, required=True)
    query = sub.add_parser('query')
    query.add_argument('geometry', type=Path)
    query.add_argument('--extract', type=Path, default=DEFAULT)
    query.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download':
        bounds = [float(x) for x in args.bbox.split(',')]
        if len(bounds) != 4:
            parser.error('bbox needs four coordinates')
        w, s, e, n = bounds
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90) or e-w > 2 or n-s > 2:
            parser.error('Use a local bbox, at most 2 degrees per side; large-area extraction needs tiling')
        if args.output.exists():
            parser.error('Output already exists; use a new path to preserve snapshots')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(Path(sys.executable).with_name('overturemaps')), 'download',
                        '--bbox='+args.bbox, '--release='+args.release, '--type=place',
                        '-f', 'geoparquet', '-o', str(args.output)], check=True)
        manifest(args.output, bounds, args.release)
    else:
        provider = Places(args.extract)
        raw = json.loads(args.geometry.read_text())
        rows = provider.query(raw.get('geometry', raw))
        result = {'source': provider.manifest, 'places': rows,
                  'categories': dict(Counter(r['category'] for r in rows)),
                  'note': 'Point containment supplies no named-area extent or salience score.'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({'places': len(rows), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
