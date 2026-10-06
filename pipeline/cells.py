"""H3 cells for a city and the places inside each cell.

Cells are H3 at `resolution` (9 by default, about 0.1 km²) covering the study
area. The study area is the union of the ground-truth polygons when they exist,
else the extract bbox. Cells with no places are kept: they are territory, and the
contiguity graph needs them. Water is left in; the regionalization step decides
what to do with empty cells.

Places become `names.Record`s. Closed and unnamed records are dropped, as in
cadmus/demo/research/overture_evidence.py; everything else is kept, including low
confidence. Filtering by confidence is a hypothesis to test, not a default.
"""
from dataclasses import dataclass

import h3
import pyarrow.parquet as pq
from shapely import from_wkb
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import unary_union

from names import Record

RESOLUTION = 9


@dataclass
class Place:
    record: Record
    cell: str
    category: str
    group: str  # top of taxonomy.hierarchy, e.g. geographic_entities, retail
    confidence: float


def load_places(path, resolution=RESOLUTION):
    """Read an Overture place extract into Places with their H3 cell."""
    table = pq.read_table(path, columns=['id', 'geometry', 'names', 'categories', 'taxonomy',
                                         'confidence', 'brand', 'operating_status'])
    out = []
    for row in table.to_pylist():
        name = (row.get('names') or {}).get('primary')
        if not name or row.get('operating_status') == 'closed':
            continue
        pt = from_wkb(row['geometry'])
        tax = row.get('taxonomy') or {}
        cat = tax.get('primary') or (row.get('categories') or {}).get('primary') or 'unknown'
        hierarchy = tax.get('hierarchy') or [cat]
        brand = ((row.get('brand') or {}).get('names') or {}).get('primary')
        out.append(Place(Record(name, pt.x, pt.y, brand, row['id']),
                         h3.latlng_to_cell(pt.y, pt.x, resolution),
                         cat, hierarchy[0], row.get('confidence') or 0.0))
    return out


def study_cells(area, resolution=RESOLUTION):
    """All H3 cells whose footprint intersects `area` (a shapely Polygon or MultiPolygon).

    h3.geo_to_cells gives cells whose centre is inside; a one-ring expansion then
    a footprint intersection test adds the edge cells, so the boundary is covered.
    """
    polys = [area] if isinstance(area, Polygon) else list(area.geoms)
    centre_in = set()
    for p in polys:
        centre_in |= set(h3.geo_to_cells(h3.geo_to_h3shape(mapping(p)), resolution))
    candidates = set(centre_in)
    for c in centre_in:
        candidates |= set(h3.grid_ring(c, 1))
    cells = set()
    for c in candidates:
        if c in centre_in or shape(h3.cells_to_geo([c])).intersects(area):
            cells.add(c)
    return sorted(cells)


def bbox_area(bbox):
    return box(*bbox)


def boundary_area(gdf):
    """Union of a ground-truth GeoDataFrame in EPSG:4326."""
    return unary_union(list(gdf.to_crs(4326).geometry))


def cell_polygon(cell):
    return shape(h3.cells_to_geo([cell]))
