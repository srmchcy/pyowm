import unittest
import json
import copy
from pyowm.stationsapi30.station import Station
from pyowm.stationsapi30.measurement import Measurement, AggregatedMeasurement
from pyowm.stationsapi30.buffer import Buffer
from pyowm.stationsapi30.stations_manager import StationsManager
from pyowm.commons.http_client import HttpClient
from pyowm.stationsapi30.station_parser import StationParser


class MockHttpClient(HttpClient):

    test_station_json = '''{"ID": "583436dd9643a9000196b8d6",
        "created_at": "2016-11-22T12:15:25.967Z",
        "updated_at": "2016-11-22T12:15:25.967Z",
        "external_id": "SF_TEST001",
        "name": "San Francisco Test Station",
        "longitude": -122.43,
        "latitude": 37.76,
        "altitude": 150,
        "rank": 0}'''

    def get_json(self, uri, params=None, headers=None):
        return 200, [json.loads(self.test_station_json)]

    def post(self, uri, params=None, data=None, headers=None):
        return 200, json.loads(self.test_station_json)

    def put(self, uri, params=None, data=None, headers=None):
        return 200, None

    def delete(self, uri, params=None, data=None, headers=None):
        return 204, None


class MockHttpClientOneStation(HttpClient):
    test_station_json = '''{"ID": "583436dd9643a9000196b8d6",
        "created_at": "2016-11-22T12:15:25.967Z",
        "updated_at": "2016-11-22T12:15:25.967Z",
        "external_id": "SF_TEST001",
        "name": "San Francisco Test Station",
        "longitude": -122.43,
        "latitude": 37.76,
        "altitude": 150,
        "rank": 0}'''

    def get_json(self, uri, params=None, headers=None):
        return 200, json.loads(self.test_station_json)


class MockHttpClientMeasurements(HttpClient):
    msmt1 = Measurement('test_station', 1378459200,
        temperature=dict(min=0, max=100), wind_speed=2.1, wind_gust=67,
        humidex=77, weather_other=dict(key='val1'))
    msmt2 = Measurement('test_station', 1878459999,
        temperature=dict(min=20, max=180), wind_speed=0.7, wind_gust=-7,
        humidex=12, weather_other=dict(key='val2'))
    aggr_msmt1 = AggregatedMeasurement('id1', 1200, 'd', temp=dict(max=9,min=1),
                                       precipitation=dict(min=8.2, max=44.8))
    aggr_msmt2 = AggregatedMeasurement('id1', 1500, 'd', temp=dict(max=8,min=-2))
    aggr_msmt3 = AggregatedMeasurement('id1', 3000, 'd', temp=dict(max=9,min=0))

    def get_json(self, uri, params=None, headers=None):
        items = [self.aggr_msmt1.to_dict(),
                 self.aggr_msmt2.to_dict(),
                 self.aggr_msmt3.to_dict()]
        for i in items:
            i['date'] = i['timestamp']
            i['type'] = i['aggregated_on']
            del i['timestamp']
            del i['aggregated_on']

        # filter on time-windos
        new_items = []
        for i in items:
            if params['from'] <= i['date'] <= params['to']:
                new_items.append(i)

        # check optional limit
        if 'limit' in params:
            return 200, new_items[:params['limit']]
        return 200, new_items

    def post(self, uri, params=None, data=None, headers=None):
        return 200, ''


class TestStationManager(unittest.TestCase):

    def factory(self, _kls):
        sm = StationsManager('APIKey')
        sm.http_client = _kls()
        return sm

    def test_instantiation_fails_without_api_key(self):
        self.assertRaises(AssertionError, StationsManager, None)

    def test_get_stations_api_version(self):
        instance = StationsManager('APIKey')
        result = instance.stations_api_version()
        self.assertIsInstance(result, tuple)

    def test_get_stations(self):
        instance = self.factory(MockHttpClient)
        results = instance.get_stations()
        self.assertEqual(1, len(results))
        s = results[0]
        self.assertIsInstance(s, Station)

    def test_get_station(self):
        instance = self.factory(MockHttpClientOneStation)
        result = instance.get_station('1234')
        self.assertIsInstance(result, Station)

    def test_create_stations(self):
        instance = self.factory(MockHttpClient)
        result = instance.create_station("TEST2", "test2", 37.76, -122.43)
        self.assertIsInstance(result, Station)

    def test_create_stations_fails_with_wrong_inputs(self):
        instance = self.factory(MockHttpClient)
        with self.assertRaises(AssertionError):
            instance.create_station(None, "test2", 37.76, -122.43)
        with self.assertRaises(AssertionError):
            instance.create_station("TEST2", None, 37.76, -122.43)
        with self.assertRaises(AssertionError):
            instance.create_station("TEST2", "test2", None, -122.43)
        with self.assertRaises(AssertionError):
            instance.create_station("TEST2", "test2", 37.76, None)
        with self.assertRaises(ValueError):
            instance.create_station("TEST2", "test2", 1678, -122.43)
        with self.assertRaises(ValueError):
            instance.create_station("TEST2", "test2", 37.76, -8122.43)
        with self.assertRaises(ValueError):
            instance.create_station("TEST2", "test2", 37.76, -122.43, alt=-3)

    def test_update_station(self):
        instance = self.factory(MockHttpClient)
        parser = StationParser()
        modified_station = parser.parse_JSON(MockHttpClient.test_station_json)
        modified_station.external_id = 'CHNG'
        result = instance.update_station(modified_station)
        self.assertIsNone(result)

    def test_update_station_fails_when_id_is_none(self):
        instance = self.factory(MockHttpClient)
        parser = StationParser()
        modified_station = parser.parse_JSON(MockHttpClient.test_station_json)
        modified_station.id = None
        with self.assertRaises(AssertionError):
            instance.update_station(modified_station)

    def test_delete_station(self):
        instance = self.factory(MockHttpClient)
        parser = StationParser()
        station = parser.parse_JSON(MockHttpClient.test_station_json)
        result = instance.delete_station(station)
        self.assertIsNone(result)

    def test_delete_station_fails_when_id_is_none(self):
        instance = self.factory(MockHttpClient)
        parser = StationParser()
        station = parser.parse_JSON(MockHttpClient.test_station_json)
        station.id = None
        with self.assertRaises(AssertionError):
            instance.delete_station(station)

    def test_send_measurement(self):
        instance = self.factory(MockHttpClientMeasurements)
        instance.send_measurement(MockHttpClientMeasurements.msmt1)

    def test_send_measurement_failing(self):
        instance = self.factory(MockHttpClientMeasurements)

        with self.assertRaises(AssertionError):
            instance.send_measurement(None)

        msmt = copy.deepcopy(MockHttpClientMeasurements.msmt1)
        msmt.station_id = None
        with self.assertRaises(AssertionError):
            instance.send_measurement(msmt)

    def test_send_measurements(self):
        instance = self.factory(MockHttpClientMeasurements)
        msmts = [MockHttpClientMeasurements.msmt1,
                 MockHttpClientMeasurements.msmt2]
        instance.send_measurements(msmts)

    def test_send_measurements_failing(self):
        instance = self.factory(MockHttpClientMeasurements)

        with self.assertRaises(AssertionError):
            instance.send_measurements(None)

        msmt_1 = copy.deepcopy(MockHttpClientMeasurements.msmt1)
        msmt_1.station_id = None
        msmt_2 = copy.deepcopy(MockHttpClientMeasurements.msmt2)
        msmt_2.station_id = None
        with self.assertRaises(AssertionError):
            instance.send_measurements([msmt_1, msmt_2])

    def test_get_measurements(self):
        instance = self.factory(MockHttpClientMeasurements)
        station_id = 'id1'
        from_ts = 1000
        to_ts = 4000
        results = instance.get_measurements(station_id, 'd', from_ts, to_ts)
        self.assertEqual(3, len(results))
        for item in results:
            self.assertTrue(isinstance(item, AggregatedMeasurement))
            self.assertEquals(item.station_id, station_id)
            self.assertTrue(from_ts <= item.timestamp <= to_ts)

    def test_get_measurements_cut_time_windows(self):
        instance = self.factory(MockHttpClientMeasurements)
        station_id = 'id1'
        from_ts = 100
        to_ts = 1300
        results = instance.get_measurements(station_id, 'd', from_ts, to_ts)
        self.assertEqual(1, len(results))
        item = results[0]
        self.assertTrue(isinstance(item, AggregatedMeasurement))
        self.assertEquals(item.station_id, station_id)
        self.assertTrue(from_ts <= item.timestamp <= to_ts)

    def test_get_measurements_with_limits(self):
        instance = self.factory(MockHttpClientMeasurements)
        station_id = 'id1'
        from_ts = 1000
        to_ts = 4000
        limit = 2
        results = instance.get_measurements(station_id, 'd', from_ts, to_ts,
                                            limit=limit)
        self.assertEqual(2, len(results))
        for item in results:
            self.assertTrue(isinstance(item, AggregatedMeasurement))
            self.assertEquals(item.station_id, station_id)
            self.assertTrue(from_ts <= item.timestamp <= to_ts)

    def test_get_measurements_failing(self):
        instance = self.factory(MockHttpClientMeasurements)
        with self.assertRaises(AssertionError):
            instance.get_measurements(None, 'm', 123, 456)
        with self.assertRaises(AssertionError):
            instance.get_measurements('test_station', None, 123, 456)
        with self.assertRaises(AssertionError):
            instance.get_measurements('test_station', 'm', None, 456)
        with self.assertRaises(AssertionError):
            instance.get_measurements('test_station', 'm', -123, 456)
        with self.assertRaises(AssertionError):
            instance.get_measurements('test_station', 'm', 123, None)
        with self.assertRaises(AssertionError):
            instance.get_measurements('test_station', 'm', 123, -456)
        with self.assertRaises(ValueError):
            instance.get_measurements('test_station', 'm', 123, 88)

    def test_send_buffer(self):
        instance = self.factory(MockHttpClientMeasurements)
        buffer = Buffer(MockHttpClientMeasurements.msmt1.station_id)
        buffer.append(MockHttpClientMeasurements.msmt1)
        instance.send_buffer(buffer)

    def test_send_buffer_failing(self):
        instance = self.factory(MockHttpClientMeasurements)

        with self.assertRaises(AssertionError):
            instance.send_buffer(None)
