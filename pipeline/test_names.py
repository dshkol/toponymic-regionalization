"""Regression cases ported from cadmus/demo/tests/lexical.test.ts, plus normalization."""
import math
import unittest

from names import Record, Support, eligible, log_ratio, normalize, phrases, site_key, words, zone_support


class Normalization(unittest.TestCase):
    def test_words_fold_accents_and_drop_digits(self):
        self.assertEqual(words('Café Rêve 24 St-Laurent'), ['cafe', 'reve', '24', 'st', 'laurent'])
        self.assertEqual(normalize('Local 1'), 'local 1')
        self.assertEqual(phrases('Local 1'), {'local'})

    def test_phrases_skip_stopword_edges_and_short_tokens(self):
        self.assertEqual(phrases('Mission Dolores Park'), {'mission', 'dolores', 'mission dolores'})
        self.assertNotIn('st', phrases('Valencia St Public Parklet'))
        self.assertIn('valencia', phrases('Valencia St Public Parklet'))

    def test_site_key_matches_cadmus_precision(self):
        self.assertEqual(site_key(-122.4456255, 37.763685), '-122.44563,37.76369')


class SupportCap(unittest.TestCase):
    # Four 'Green Strategies' name variants at one coordinate: one support unit, excluded.
    def test_stacked_names_at_one_site_count_once(self):
        stacked = [Record(n, -122.4456255, 37.763685) for n in
                   ['Go For The Green Strategies', 'Best Green Strategies',
                    'Go For Green Strategies', 'Smart Green Strategies']]
        support, sites = zone_support(stacked)
        t = support['green strategies']
        self.assertEqual((t.records, len(t.names), len(t.sites), t.units), (4, 4, 1, 1))
        self.assertEqual(sites, 1)
        self.assertFalse(eligible(t))

    def test_identical_name_across_sites_stays_capped(self):
        rows = [Record('Same Brand', -122.445 + i * .001, 37.765) for i in range(4)]
        support, _ = zone_support(rows)
        self.assertEqual((support['same brand'].units, len(support['same brand'].sites)), (1, 4))

    def test_distinct_names_at_distinct_sites_qualify_and_colocated_aliases_add_nothing(self):
        rows = [Record(f'Local {i}', -122.445 + i * .001, 37.765) for i in range(3)]
        base, _ = zone_support(rows)
        extra = rows + [Record(f'Extra {i} Local', -122.445, 37.765) for i in range(20)]
        added, _ = zone_support(extra)
        self.assertEqual(base['local'].units, 3)
        self.assertEqual(added['local'].units, 3)
        self.assertTrue(eligible(added['local']))

    def test_declared_brand_caps_identities(self):
        rows = [Record(f'Starbucks #{i}', -122.445 + i * .001, 37.765, brand='Starbucks') for i in range(5)]
        support, _ = zone_support(rows)
        self.assertEqual(support['starbucks'].units, 1)

    def test_log_ratio_formula(self):
        self.assertAlmostEqual(log_ratio(3, 10, 1, 100), math.log((4 / 12) / (2 / 102)))
        self.assertEqual(log_ratio(0, 0, 0, 0), 0.0)


if __name__ == '__main__':
    unittest.main()
