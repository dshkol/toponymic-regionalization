import math
import unittest

from lexicon import classify, name_parts, strip_generic


def row(**kw):
    base = {'support': 30, 'records': 32, 'cells': 10, 'locality': 5.0, 'morans_i': 0.3, 'sd_km': 1.0,
            'brand_share': 0.0, 'landmark_share': 0.0, 'is_street': False, 'is_division': False}
    base.update(kw)
    return base


class Names(unittest.TestCase):
    def test_strip_generic_drops_road_words(self):
        self.assertEqual(strip_generic('Valencia Street'), 'valencia')
        self.assertEqual(strip_generic('Mission Dolores Park'), 'mission dolores')

    def test_name_parts_splits_joined_official_names(self):
        # 'market' is a stopword in names.STOP, so phrases never contain it and the
        # match terms must not either: 'Upper Market' reduces to 'upper'.
        self.assertEqual(name_parts('Castro/Upper Market'), {'castro upper', 'castro', 'upper'})
        self.assertIn('ingleside', name_parts('Oceanview/Merced/Ingleside'))
        self.assertIn('bayview hunters point', name_parts('Bayview Hunters Point'))


class Classify(unittest.TestCase):
    def test_chain_by_declared_brand_or_collapsed_support(self):
        self.assertEqual(classify(row(records=90, brand_share=0.4)), 'brand')
        self.assertEqual(classify(row(support=4, records=86)), 'brand')
        self.assertNotEqual(classify(row(support=4, records=4, brand_share=0.25)), 'brand')  # too few records

    def test_generic_by_locality_or_city_scale_spread(self):
        self.assertEqual(classify(row(locality=0.5)), 'generic')
        self.assertEqual(classify(row(locality=float('nan'))), 'generic')
        self.assertEqual(classify(row(sd_km=3.5)), 'generic')

    def test_street_division_mixed(self):
        self.assertEqual(classify(row(is_street=True)), 'street')
        self.assertEqual(classify(row(is_division=True)), 'division')
        self.assertEqual(classify(row(is_street=True, is_division=True)), 'mixed')

    def test_landmark_point_area(self):
        self.assertEqual(classify(row(landmark_share=0.6)), 'landmark')
        self.assertEqual(classify(row(cells=1)), 'point')
        self.assertEqual(classify(row()), 'area')


if __name__ == '__main__':
    unittest.main()
