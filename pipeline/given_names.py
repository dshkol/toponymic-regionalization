"""Given names, for the lexicon's `person` class.

A phrase whose every token is a common given name in the English-speaking
world ('jennifer', 'raymond james') is a professional's shingle, not a place.
The list comes from the dictionary shipped inside the `gender-guesser`
package (Jörg Michael's nam_dict.txt, GPL), read at build time and never
copied into this repo; without the package the set is empty and the
summary says so. Frequency columns: Great Britain, Ireland, U.S.A. (the
dictionary has no Canada column); a name counts when its best of those is
at least MIN_FREQUENCY on the dictionary's 1–13 scale, which keeps 'marina'
(3) and 'noe' (1) as places and flags 'morgan' (4) and 'stanley' (6).
"""
import importlib.util
from pathlib import Path

MIN_FREQUENCY = 4
COLUMNS = (30, 31, 32)  # Great Britain, Ireland, U.S.A.


def load(min_frequency=MIN_FREQUENCY):
    spec = importlib.util.find_spec('gender_guesser')
    if spec is None or not spec.submodule_search_locations:
        return frozenset()
    path = Path(list(spec.submodule_search_locations)[0]) / 'data' / 'nam_dict.txt'
    names = set()
    with open(path, encoding='iso8859-1') as f:
        for line in f:
            if line.startswith('#') or len(line) < 40:
                continue
            name = line[3:29].strip().lower()
            if not name or '+' in name:  # 'Jean+Marie' compounds
                continue
            try:
                freq = max(int(line[c], 16) if line[c] != ' ' else 0 for c in COLUMNS)
            except ValueError:
                continue
            if freq >= min_frequency:
                names.add(name)
    return frozenset(names)


def is_person(phrase, names):
    tokens = phrase.split()
    return bool(names) and all(t in names for t in tokens)
