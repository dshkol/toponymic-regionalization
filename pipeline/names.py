"""Name normalization, phrase extraction and the support cap.

One Python home for rules that cadmus has in TypeScript (demo/lib/lexical.ts,
"Lexical support v0.2") and partly in Python (demo/research/anchor_ranking.py,
scripts/prepare_data.py). The rules are copied, not redesigned, so a count here
means the same thing as a count there:

- a site is a coordinate rounded to 5 decimals (about 1 m), not an address or a
  building;
- a phrase's support in a zone is min(distinct normalized names, distinct sites),
  and min(..., distinct identities) when brands are known, where an identity is
  the declared brand if there is one, else the normalized name;
- a phrase needs MIN_SUPPORT units to count;
- rates use the number of distinct sites in the zone, with add-one smoothing.

This is a heuristic cap on stacked registrations and chains, not an estimate of
independent owners. Phrase extraction is ASCII-folded English and is not fit for
a bilingual city without review.
"""
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, NamedTuple, Optional

MIN_SUPPORT = 3

# Union of cadmus's two stop lists (prepare_data.py and anchor_ranking.GENERIC),
# plus the city names of the four study cities. A stopword may not start or end a
# phrase. "park", "street" and the like are generic here because the lexicon
# classifies streets and landmarks from geometry, not from suffixes.
STOP = set('''
the a an and of at in on to for by inc llc corp corporation company co ltd ltee
services service group dental dentistry consulting consultancy management
properties property real estate holdings holding trust family investment
investments construction restaurant cafe coffee shop market auto salon hair design
studio associates association partnership partners limited enterprise enterprises
medical center centre care san francisco california sf ca usa llp business
professional solutions systems technology technologies international global
plumbing electric electrical general contractor
park national state garden beach museum library university college school high
elementary train railway station monument historical landmark nature reserve
mountain public community branch playground st street ave avenue rd road blvd
boulevard dr drive
toronto ontario on vancouver bc british columbia chicago illinois il
'''.split())


class Record(NamedTuple):
    """One named place. `brand` is Overture's brand.names.primary when declared."""
    name: str
    x: float
    y: float
    brand: Optional[str] = None
    id: Optional[str] = None


def words(name: str) -> list[str]:
    """Casefold, strip accents, keep alphanumeric runs. 'Café Rêve 24' -> ['cafe', 'reve', '24'].

    Digits stay in the normalized name, so 'Local 1' and 'Local 2' are distinct
    names (cadmus compares the lowercased full string). Phrases drop them.
    """
    folded = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.findall(r'[a-z0-9]+', folded.casefold())


def normalize(name: str) -> str:
    return ' '.join(words(name))


def phrases(name: str, sizes=(1, 2, 3), min_chars=3) -> set[str]:
    """1-3-grams of letter tokens that neither start nor end with a stopword.

    Tokens with digits and tokens shorter than `min_chars` are excluded, as in
    cadmus/scripts/prepare_data.py and anchor_ranking.phrases.
    """
    tokens = words(name)
    out = set()
    for n in sizes:
        for i in range(len(tokens) - n + 1):
            span = tokens[i:i + n]
            if span[0] in STOP or span[-1] in STOP:
                continue
            if any(len(t) < min_chars or any(c.isdigit() for c in t) for t in span):
                continue
            out.add(' '.join(span))
    return out


def site_key(x: float, y: float) -> str:
    return f'{x:.5f},{y:.5f}'


@dataclass
class Support:
    """Evidence for one phrase in one zone."""
    records: int = 0
    names: set = field(default_factory=set)
    sites: set = field(default_factory=set)
    identities: set = field(default_factory=set)
    examples: list = field(default_factory=list)

    def add(self, record: Record):
        norm = normalize(record.name)
        self.records += 1
        self.names.add(norm)
        self.sites.add(site_key(record.x, record.y))
        self.identities.add(('brand', record.brand.casefold()) if record.brand else ('name', norm))
        if len(self.examples) < 5 and record.name not in self.examples:
            self.examples.append(record.name)

    @property
    def units(self) -> int:
        return min(len(self.names), len(self.sites), len(self.identities))


def zone_support(records: Iterable[Record], vocabulary: Optional[set] = None):
    """Per-phrase Support over one zone, plus the zone's distinct site count.

    With `vocabulary`, only those phrases are counted (cadmus's lexicon-hit mode).
    A record contributes once per distinct phrase, whatever its repetition in the name.
    """
    support = defaultdict(Support)
    sites = set()
    for r in records:
        sites.add(site_key(r.x, r.y))
        for p in phrases(r.name):
            if vocabulary is not None and p not in vocabulary:
                continue
            support[p].add(r)
    return support, len(sites)


def log_ratio(n: int, zone_sites: int, m: int, other_sites: int) -> float:
    """Smoothed log rate ratio, cadmus lexical.ts: log(((n+1)/(N+2)) / ((m+1)/(M+2)))."""
    return math.log(((n + 1) / (zone_sites + 2)) / ((m + 1) / (other_sites + 2)))


def eligible(support: Support, minimum: int = MIN_SUPPORT) -> bool:
    return support.units >= minimum
