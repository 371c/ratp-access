# -*- coding: utf-8 -*-
"""
    ratp
    ====

    A simple command line application that displays the accessibility
    of ratp bus stops and bus routes

"""

import os
import xlrd
import logging
import argparse

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler('ratp.log'))

db_file = 'ratp.db'
db_url = 'sqlite:///{}'.format(db_file)
Base = declarative_base()

axs_value_mappings = dict(
    ann_nextstop_vocal=u'Annonce sonore prochain arrêt',
    ann_nextstop_visual=u'Annonce visuelle prochain arrêt',
    ann_nextbus_vocal=u'Annonce sonore prochain passage',
    ann_nextbus_visual=u'Annonce visuelle prochain passage',
    ann_problem_visual=u'Annonce visuelle situations pertubées',
    ann_problem_vocal=u'Annonce sonore situations pertubées',
    wheelchair_axs=u'Accessible en fauteuil roulant')


class BusStop(Base):
    """Represents an RATP bus stop"""
    __tablename__ = 'bus_stops'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode)
    description = sa.Column(sa.Unicode)
    direction = sa.Column(sa.Unicode)
    route_stif_code = sa.Column(sa.Unicode)
    #route_id = sa.Column(sa.Integer, sa.ForeignKey('bus_routes.id'))
    accessibility = sa.orm.relationship('AxsValue')

    def __str__(self):
        axs_values = u','.join((a.description for a in self.accessibility))
        _me = u'Arret {}, Direction: {}, Accessibilité: {}'.format(
            self.name, u'Aller' if self.direction == u'A' else u'Retour',
            axs_values)
        return _me.encode('utf-8')


class BusRoute(Base):
    """Represents an RATP bus route"""
    __tablename__ = 'bus_routes'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode)
    description = sa.Column(sa.Unicode)
    origin = sa.Column(sa.Unicode)
    destination = sa.Column(sa.Unicode)
    stif_code = sa.Column(sa.Unicode)
    accessibility = sa.orm.relationship('AxsValue')

    def __str__(self):
        axs_values = u','.join((a.description for a in self.accessibility))
        _me = u'Ligne {}, {} -> {}, Accessibilité: {}'.format(
            self.name, self.origin, self.destination, axs_values)
        return _me.encode('utf-8')


class AxsValue(Base):
    """Represents the accessibility of a bus stop or bus route"""
    __tablename__ = 'accessibility'

    id = sa.Column(sa.Integer, primary_key=True)
    description = sa.Column(sa.Unicode)
    route_id = sa.Column(sa.Integer, sa.ForeignKey('bus_routes.id'))
    stop_id = sa.Column(sa.Integer, sa.ForeignKey('bus_stops.id'))


class DataImporter(object):
    """Handles importing of ratp data into the database"""

    def __init__(self, stops_file, routes_file, db_url=None):
        self.stops_file = stops_file
        self.routes_file = routes_file

        # init db
        self.db_url = db_url or 'sqlite:///ratp.db'
        self.session = None

    def __enter__(self):
        """Create db session and return the datahandler instance"""
        # create db session
        logger.info("__enter__")
        sa_engine = sa.create_engine(self.db_url, echo=True)
        Base.metadata.create_all(sa_engine)

        self.session = sa.orm.scoped_session(
            sa.orm.sessionmaker(bind=sa_engine))

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Close the database connection"""
        logger.info("__exit__")
        self.session.commit()
        self.session.remove()

    def import_routes(self):
        """Fetch routes data from the xls file and store in the database"""
        sheet = self._sheet_from_file(
            self.routes_file, u'Accessibilité Lignes')

        for row in xrange(0, sheet.nrows):

            if 0 == row:  # skip the titles row
                continue

            # retrieve route data from row
            dest = (sheet.cell(row, 3).value or u'').strip()
            origin = (sheet.cell(row, 2).value or u'').strip()
            route_number_raw = sheet.cell(row, 1).value or u''
            route_number = u'{0:.0f}'.format(route_number_raw)\
                           if not isinstance(route_number_raw, unicode)\
                              else route_number_raw.strip()
            stif_code = u'{0:.0f}'.format(sheet.cell(row, 0).value or u'-1')

            # axs values
            wheelchair_axs = int(sheet.cell(row, 4).value or 0)
            ann_nextstop_vocal = int(sheet.cell(row, 7).value or 0)
            ann_nextstop_visual = int(sheet.cell(row, 8).value or 0)

            # create bus route instance
            bus_route = BusRoute(
                name=route_number.upper(),
                description=int(stif_code),
                stif_code=stif_code,
                origin=origin, destination=dest
            )
            # create accessibility values
            axs_values = [
                AxsValue(description=axs_value_mappings.get(k)) for
                k, v in (('wheelchair_axs', wheelchair_axs),
                         ('ann_nextstop_visual', ann_nextstop_visual),
                         ('ann_nextstop_vocal', ann_nextstop_vocal))
                if v == 1]
            bus_route.accessibility.extend(axs_values)

            # add stop to session
            self.session.add(bus_route)

        # commit session
        self.session.commit()

    def import_stops(self):
        "Fetch stops data and store in the database"
        sheet = self._sheet_from_file(
            self.stops_file, u'Bus')

        for row in xrange(0, sheet.nrows):

            if row == 0:  # skip the titles row
                continue

            name_raw = sheet.cell(row, 2).value
            if not isinstance(name_raw, unicode):
                continue
            name = name_raw.strip()
            wheelchair_axs = int(sheet.cell(row, 6).value or 0)
            ann_nextbus_vocal = int(sheet.cell(row, 7).value or 0)
            ann_nextbus_visual = int(sheet.cell(row, 8).value or 0)
            ann_problem_vocal = int(sheet.cell(row, 9).value or 0)
            ann_problem_visual = (sheet.cell(row, 10).value or 0)
            stif_code = u'{0:.0f}'.format(sheet.cell(row, 15).value or u'-1')
            direction = (sheet.cell(row, 16).value or u'').strip()

            # create a bus stop instance
            bus_stop = BusStop(
                name=name, direction=direction,
                route_stif_code=stif_code)

            # create the accessibility values
            axs_values = [
                AxsValue(description=axs_value_mappings.get(k)) for
                k, v in (('wheelchair_axs', wheelchair_axs),
                         ('ann_nextbus_visual', ann_nextbus_visual),
                         ('ann_nextbus_vocal', ann_nextbus_vocal),
                         ('ann_problem_vocal', ann_problem_vocal),
                         ('ann_problem_visual', ann_problem_visual))
                if v == 1]
            bus_stop.accessibility.extend(axs_values)

            # add to session
            self.session.add(bus_stop)

        # commit sessions
        self.session.commit()

    def _sheet_from_file(self, file_path, sheet_name):
        """Return the xls sheet in the xls file at *file_path*"""
        if not file_path or not sheet_name:
            return

        book = xlrd.open_workbook(file_path)
        logger.info("##sheet names: {}".format(book.sheet_names()))
        sheet = book.sheet_by_name(sheet_name)
        return sheet


class DataManager(object):
    """Provides handy methods for data retrieval from the database"""

    def __init__(self, db_url):
        self.db_url = db_url
        self.session = None

    def __enter__(self):
        """Create db session and return the datahandler instance"""
        # create db session
        sa_engine = sa.create_engine(self.db_url, echo=False)
        self.session = sa.orm.scoped_session(
            sa.orm.sessionmaker(bind=sa_engine))
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Close the database connection"""
        self.session.remove()

    def fetch_routes(self, limit):
        """Return available ratp routes"""
        #logger.info("fetching {} routes".format(limit))
        routes_q = self.session.query(BusRoute)
        if limit > 0:
            routes_q = routes_q.limit(limit)
        return routes_q

    def fetch_stops(self, route_number, limit):
        """Return stops in the route identified by route number"""

        stops_q = self.session.query(BusStop).join(
            BusRoute, BusStop.route_stif_code == BusRoute.stif_code).filter(
                BusRoute.name == unicode(route_number or ''))
        if limit > 0:
            stops_q = stops_q.limit(limit)
        return stops_q


def import_data():
    """Read the xls data sources and build the corresponding database"""
    here = os.path.abspath(os.path.dirname(__file__))
    logger.info('here: {}'.format(here))

    bus_stops = os.path.join(here, 'data/stops_axs.xls')
    bus_routes = os.path.join(here, 'data/routes_axs.xls')

    # remove db file is one already exists
    db_path = os.path.join(here, db_file)
    try:
        logger.info('Removing existing db: {}'.format(db_path))
        os.remove(db_path)
        logger.info('Removed existing db: {}'.format(db_path))
    except OSError, why:
        logger.error('Error removing file: {} -- {}'.format(db_path, why))

    # import data
    with DataImporter(bus_stops, bus_routes, db_url=db_url) as dh:
        # import routes
        dh.import_routes()

        # import stops
        dh.import_stops()


def process_args(parser):
    """Execute an action depending on the parsed arguments"""
    args = parser.parse_args()
    if args.do_import:  # import routes and stops
        import_data()
    elif args.list_routes:  # list available routes
        with DataManager(db_url) as dm:
            routes = dm.fetch_routes(args.limit)
            logger.info('\nLignes\n----------')
            for route in routes:
                logger.info(route)
    elif args.route_number:  # list stops in specified route
        with DataManager(db_url) as dm:
            stops = dm.fetch_stops(args.route_number, args.limit)
            logger.info(u"\nArrêts sur la ligne {}\n-----------".format(
                args.route_number))
            for stop in stops:
                logger.info(stop)
    else:  # usage
        parser.print_help()


def main():

    # usage
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', action='store_true', dest='list_routes',
                        help='List available routes')
    parser.add_argument('-s', action='store', dest='route_number',
                        help='List the stops in the specified route ex. 54')
    parser.add_argument('-i', action='store_true', default=False,
                        dest='do_import',
                        help=('If True, import data in the xls files and '
                              '(re)build the database. '
                              'If the datadbase exists already, it will '
                              ' be destroyed then recreated'))
    parser.add_argument('--limit', action='store', dest='limit',
                        default=5, type=int,
                        help=('Limit the number of displayed values. '
                              'Use -1 to display all.'))

    process_args(parser)


if __name__ == '__main__':
    main()
