# -*- coding: utf-8 -*-
"""
    ratp_tests
    ==========
    Test the ratp application

"""
import os
import unittest

import ratp


class RatpTest(unittest.TestCase):

    def setUp(self):

        here = os.path.abspath(os.path.dirname(__file__))
        self.stops = os.path.join(here, 'data/stops_axs.xls')
        self.routes = os.path.join(here, 'data/routes_axs.xls')
        self.db_url = 'sqlite:///:memory:'
        #self.db_url = 'sqlite:///test.db'

    def tearDown(self):
        pass

    def test_import(self):

        with ratp.DataImporter(
                self.stops, self.routes, db_url=self.db_url) as dh:
            dh.import_routes()  # import routes
            dh.import_stops()  # import stops

            route_query = dh.session.query(ratp.BusRoute)
            total_routes = route_query.count()
            self.assertTrue(total_routes > 1)

            stops_query = dh.session.query(ratp.BusStop)
            total_stops = stops_query.count()
            self.assertTrue(total_stops > 1)

            route_54 = route_query.filter(ratp.BusRoute.name == '54').one()
            self.assertIsNotNone(route_54)
            self.assertEqual(u'1001000540001', route_54.stif_code)
            self.assertEqual(u'GABRIEL PERI-METRO', route_54.origin)

            route_54_stops = stops_query.filter(
                ratp.BusStop.route_stif_code == route_54.stif_code).all()
            self.assertTrue(route_54_stops > 1)

if __name__ == '__main__':
    unittest.main()
