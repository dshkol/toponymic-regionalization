"""Vernacular neighbourhood polygons from the click_that_hood repository (GitHub, which the
cloud environment can reach, unlike the city portals). These are the Zillow-style and
older-official polygon sets the game uses; provenance is the repository commit, and the
manifest records the sha256, feature count and names so a rerun can be checked.

    python pipeline/fetch_reference.py            # all four cities
    python pipeline/fetch_reference.py --city chicago

Writes data/reference/<city>-clickthathood-<date>.geojson plus .manifest.json.
What each file is (checked by reading the names, 2026-10-08):
  san-francisco  37 polygons: the older SF Planning neighbourhoods (Seacliff, Nob Hill ...)
  chicago        98 polygons: vernacular neighbourhoods (Printers Row, Sheffield & DePaul,
                 Wrigleyville ...), not the 77 community areas
  toronto       140 polygons: the City of Toronto's pre-2021 official neighbourhoods
  vancouver      23 polygons: the 22 local areas plus Stanley Park
"""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/'
FILES = {'sf': 'san-francisco', 'chicago': 'chicago', 'toronto': 'toronto', 'vancouver': 'vancouver'}
DATE = '2026-10-08'


def fetch(city: str) -> Path:
    url = BASE + FILES[city] + '.geojson'
    dest = ROOT / 'data' / 'reference' / f'{city}-clickthathood-{DATE}.geojson'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r:
        raw = r.read()
    dest.write_bytes(raw)
    d = json.loads(raw)
    names = sorted(f['properties']['name'] for f in d['features'])
    manifest = {'city': city, 'source': url,
                'status': 'vernacular / older official polygons from the click_that_hood game data; not the city portal file',
                'count': len(names), 'recorded_at': datetime.now(timezone.utc).isoformat(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'names': names}
    dest.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'{city}: {len(names)} features -> {dest.relative_to(ROOT)}')
    return dest


def verify(path: Path) -> dict:
    manifest = json.loads(path.with_suffix('.manifest.json').read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError(f'{path} does not match its manifest sha256')
    return manifest


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--city', choices=FILES, default=None)
    a = ap.parse_args()
    for c in ([a.city] if a.city else FILES):
        fetch(c)
