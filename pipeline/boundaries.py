"""Ground-truth neighbourhood polygons per city, pinned under data/reference.

Official sources (HANDOFF.md) are the target. The cloud container cannot reach
the city open-data hosts, so only San Francisco is the official file (copied
from cadmus/data/neighborhoods.geojson, the original unsimplified DataSF
download of 2026-09-07). For the other three cities this module derives a
provisional set from Overture Divisions in the pinned release:

  Vancouver   macrohoods inside the Vancouver locality polygon: 22, and the
              names are the City's 22 local areas
  Chicago     macrohoods inside the Chicago locality polygon: 73 of the 77
              community areas (Logan Square, Humboldt Park, New City and Gage
              Park are absent in this release)
  Toronto     neighbourhoods inside the Toronto county polygon: 175 after
              deduplication by name, against the City's 158; the extra names
              need review against the official file

Each derived file records its provenance in a manifest. Replace it with the
official download when one is available and keep the manifest's `source` honest.

    python3 pipeline/boundaries.py            # writes all four, prints counts
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pyarrow.parquet as pq
from shapely import from_wkb

from fetch_overture import RELEASE

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'data' / 'reference'

OFFICIAL = {
    'sf': {'file': 'sf-analysis-neighborhoods-2026-09-07.geojson', 'name': 'nhood', 'count': 41,
           'source': 'DataSF Analysis Neighborhoods, https://data.sfgov.org/d/j2bu-swwd, '
                     'original geometry retrieved 2026-09-07 via cadmus/data/neighborhoods.geojson'},
}
# city -> (polygon that bounds the city, its subtype, the division subtype that holds the areas, official count)
DERIVED = {
    'toronto': ('Toronto', 'county', 'neighborhood', 158),
    'vancouver': ('Vancouver', 'locality', 'macrohood', 22),
    'chicago': ('Chicago', 'locality', 'macrohood', 77),
}


def _divisions(city):
    path = ROOT / 'data' / city / f'overture-division_area-{RELEASE}.parquet'
    t = pq.read_table(path, columns=['id', 'subtype', 'names', 'geometry', 'class', 'division_id'])
    rows = t.to_pylist()
    for r in rows:
        r['name'] = (r['names'] or {}).get('primary')
        r['geom'] = from_wkb(r['geometry'])
    return rows


def derive(city):
    boundary_name, boundary_sub, area_sub, _ = DERIVED[city]
    rows = _divisions(city)
    city_poly = [r for r in rows if r['subtype'] == boundary_sub and r['name'] == boundary_name
                 and r['class'] == 'land']
    if len(city_poly) != 1:
        raise ValueError(f'{city}: expected one {boundary_sub} polygon named {boundary_name}, got {len(city_poly)}')
    city_geom = city_poly[0]['geom']
    seen = set()
    feats = []
    for r in rows:
        if r['subtype'] != area_sub or not r['name']:
            continue
        if not r['geom'].representative_point().within(city_geom):
            continue
        if r['name'] in seen:   # Overture carries a few duplicate areas; keep the first
            continue
        seen.add(r['name'])
        feats.append({'name': r['name'], 'overture_id': r['id'], 'division_id': r['division_id'],
                      'geometry': r['geom']})
    gdf = gpd.GeoDataFrame(feats, geometry='geometry', crs='EPSG:4326')
    return gdf, city_geom


def write_derived(city):
    gdf, city_geom = derive(city)
    _, _, area_sub, official_count = DERIVED[city]
    out = REF / f'{city}-overture-{area_sub}-{RELEASE}.geojson'
    gdf.to_file(out, driver='GeoJSON')
    manifest = {
        'city': city, 'source': f'Overture Divisions {RELEASE}, subtype={area_sub}, '
                                f'representative point inside the {DERIVED[city][1]} polygon named {DERIVED[city][0]}',
        'status': 'provisional: derived, not the official city polygon set',
        'count': len(gdf), 'official_count': official_count,
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
        'invalid_geometries': int((~gdf.geometry.is_valid).sum()),
        'names': sorted(gdf['name']),
    }
    out.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return out, manifest


def load(city):
    """GeoDataFrame in EPSG:4326 with a `name` column, and the manifest or provenance dict."""
    if city in OFFICIAL:
        spec = OFFICIAL[city]
        gdf = gpd.read_file(REF / spec['file']).to_crs(4326).rename(columns={spec['name']: 'name'})
        return gdf, {'source': spec['source'], 'status': 'official', 'count': len(gdf)}
    area_sub = DERIVED[city][2]
    path = REF / f'{city}-overture-{area_sub}-{RELEASE}.geojson'
    if not path.exists():
        write_derived(city)
    gdf = gpd.read_file(path).to_crs(4326)
    return gdf, json.loads(path.with_suffix('.manifest.json').read_text())


if __name__ == '__main__':
    for city in ['sf'] + list(DERIVED):
        gdf, info = load(city)
        print(json.dumps({'city': city, 'count': len(gdf), 'status': info['status'],
                          'official_count': info.get('official_count', len(gdf)),
                          'invalid': int((~gdf.geometry.is_valid).sum())}))
