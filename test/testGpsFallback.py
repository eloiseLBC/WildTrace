"""Tests sans appels OCI, géocodage ou météo réels."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServiceError(Exception):
    pass


class RequestException(Exception):
    pass


def modules():
    geo = types.ModuleType("utils.geoUtils")
    names = (
        "get_altitude get_city_country get_hemisphere get_distance_from_equator "
        "get_coastline_distance get_pressure get_temperature_humidity get_co2 "
        "get_luminosity get_location_coordinates"
    )
    for name in names.split():
        setattr(geo, name, Mock())
    geo.constants = {}
    log = types.ModuleType("utils.loggerUtils")
    log.logger, log.log_file, log.timestamp_str = Mock(), "", "now"
    data = types.ModuleType("utils.dataUtils")
    data.get_formatted_ddmmyyyy = lambda s: s[:10]
    data.is_night, data.get_season = Mock(return_value=False), Mock(return_value="Summer")
    oci = types.ModuleType("oci")
    oci.exceptions = types.SimpleNamespace(ServiceError=ServiceError, RequestException=RequestException)
    return {"utils.geoUtils": geo, "utils.loggerUtils": log,
            "utils.dataUtils": data, "oci": oci}


class GpsFallbackCase(unittest.TestCase):
    def setUp(self):
        dependencies = modules()
        self.context = patch.dict(sys.modules, dependencies)
        self.context.start()
        self.addCleanup(self.context.stop)
        self.gps = load_module("utils.gpsUtils", "src/utils/gpsUtils.py")
        sys.modules["utils.gpsUtils"] = self.gps
        self.compute = load_module("utils.computingUtils", "src/utils/computingUtils.py")
        self.history = load_module("storage.environmentalHistory", "src/storage/environmentalHistory.py")
        sys.modules["storage.environmentalHistory"] = self.history
        self.backfill = load_module("storage.environmentalBackfill", "src/storage/environmentalBackfill.py")
        sys.modules["storage.environmentalBackfill"] = self.backfill
        self.gps.get_location_coordinates.return_value = {
            "latitude": 48.8, "longitude": 2.3, "altitude": 50,
        }
        self.compute.get_altitude.return_value = 50
        self.compute.get_pressure.return_value = 1000
        self.compute.get_city_country.return_value = {"city": "Paris", "country": "France"}
        self.compute.get_temperature_humidity.return_value = (20, "api", 60, "api")
        self.compute.get_co2.return_value = (420, "api")
        self.compute.get_luminosity.return_value = {"luminosity": 100, "luminosity_source": "computed"}
        self.compute.get_distance_from_equator.return_value = {}
        self.compute.get_coastline_distance.return_value = {}
        self.compute.get_hemisphere.return_value = "North"
        self.row = {
            "local_timestamp": "2026-10-12 12:00:00", "timezone": "Europe/Paris",
            "temperature": 20, "humidity": 60, "concentration_co2": 420,
            "luminosity": 100, "latitude": None, "longitude": None,
            "altitude_m": 50,
        }
        self.biological = {"date": "2026-10-12", "city_country": {"city": "Lyon", "country": "France"}}

    def run_compute(self, previous=(), bio=None, row=None):
        return self.compute.compute_data(
            [self.row if row is None else row],
            get_previous_files=lambda: iter(previous),
            get_biological_day=lambda d: bio if d == "2026-10-12" else None,
        )

    def test_previous_file_has_priority(self):
        self.row["altitude_m"] = None
        result = self.run_compute([
            {"latitude": 43.7, "longitude": 7.2, "altitude": 12}
        ], self.biological)
        self.assertEqual(result[0]["gps_coordinates"], "computed")
        self.assertEqual((result[0]["latitude"], result[0]["longitude"],
                          result[0]["altitude"]), (43.7, 7.2, 12))
        self.gps.get_location_coordinates.assert_not_called()
        self.compute.get_altitude.assert_not_called()

    def test_fifth_file_is_considered(self):
        result = self.run_compute([None] * 4 + [
            {"latitude": 43.7, "longitude": 7.2, "altitude": 12}
        ], self.biological)
        self.assertEqual(result[0]["latitude"], 43.7)
        self.gps.get_location_coordinates.assert_not_called()

    def test_sixth_file_is_excluded(self):
        self.run_compute([None] * 5 + [
            {"latitude": 43.7, "longitude": 7.2, "altitude": 12}
        ], self.biological)
        self.gps.get_location_coordinates.assert_called_once_with("Lyon, France")

    def test_incomplete_position_uses_older_file(self):
        result = self.run_compute([
            {"latitude": 43.7, "longitude": None, "altitude": 12},
            [{"latitude": 10, "longitude": 20, "altitude_m": 0}]
        ])
        self.assertEqual((result[0]["latitude"], result[0]["longitude"]), (10, 20))
        self.gps.get_location_coordinates.assert_not_called()

    def test_missing_altitude_uses_older_file(self):
        self.row["altitude_m"] = None
        result = self.run_compute([
            {"latitude": 43.7, "longitude": 7.2, "altitude": None},
            {"latitude": 10, "longitude": 20, "altitude": -10}
        ])
        self.assertEqual(result[0]["altitude"], -10)
        self.gps.get_location_coordinates.assert_not_called()

    def test_city_country_without_coordinates_does_not_geocode_history(self):
        self.run_compute([{"city": "Nice", "country": "France"}], self.biological)
        self.gps.get_location_coordinates.assert_called_once_with("Lyon, France")

    def test_biological_day(self):
        self.run_compute(bio=self.biological)
        self.gps.get_location_coordinates.assert_called_once_with("Lyon, France")

    def test_wrong_biological_day_uses_timezone(self):
        self.run_compute(bio={**self.biological, "date": "2026-10-11"})
        self.gps.get_location_coordinates.assert_called_once_with("Paris, France")

    def test_timezone_uses_country_capital_not_timezone_city(self):
        self.row["timezone"] = "America/Los_Angeles"
        self.run_compute()
        self.gps.get_location_coordinates.assert_called_once_with("Washington, United States")

    def test_country_timezone_alias(self):
        self.assertEqual(self.gps.timezone_capital("France"), "Paris, France")
        self.assertEqual(self.gps.timezone_capital("Asia/Ho_Chi_Minh"), "Hanoi, Vietnam")

    def test_no_location_keeps_file(self):
        self.row["timezone"] = None
        self.assertEqual(self.run_compute(), "")
        self.compute.get_temperature_humidity.assert_not_called()
        self.gps.logger.warning.assert_called()

    def test_unusable_timezone_keeps_file(self):
        self.row["timezone"] = "UTC"
        self.assertEqual(self.run_compute(), "")

    def test_failed_geocoding_keeps_file(self):
        self.gps.get_location_coordinates.return_value = {"latitude": None, "longitude": None}
        self.assertEqual(self.run_compute(bio=self.biological), "")

    def test_sensor_zero_is_valid(self):
        self.row.update(latitude=0, longitude=0)
        result = self.run_compute()
        self.assertEqual(result[0]["gps_coordinates"], "sensor")
        self.gps.get_location_coordinates.assert_not_called()

    def test_only_missing_coordinate_is_replaced(self):
        self.row["latitude"] = 10
        result = self.run_compute()
        self.assertEqual(result[0]["latitude"], 10)
        self.assertEqual(result[0]["longitude"], 2.3)
        self.assertEqual(result[0]["latitude_source"], "sensor")
        self.assertEqual(result[0]["longitude_source"], "computed")

    def test_weather_uses_resolved_coordinates_before_gps_fields(self):
        self.row.update(temperature=None, humidity=None, luminosity=None, concentration_co2=None)
        result = self.run_compute()
        self.assertEqual(result[0]["temperature"], 20)
        self.assertEqual(self.compute.get_temperature_humidity.call_args.args[:2], (48.8, 2.3))
        self.assertEqual(self.compute.get_luminosity.call_args.args[:2], (48.8, 2.3))
        self.assertEqual(self.compute.get_co2.call_args.args[:2], (48.8, 2.3))

    def test_sources_reset_for_each_row(self):
        sensor = {**self.row, "latitude": 1, "longitude": 2}
        result = self.compute.compute_data([self.row, sensor])
        self.assertEqual([r["gps_coordinates"] for r in result], ["computed", "sensor"])
        self.assertEqual(result[1]["latitude_source"], "sensor")

    def test_history_pagination_archives_limit_and_no_future_files(self):
        ns = types.SimpleNamespace
        current = ns(name="collected/to_compute/collect_12-10-2026-12-00-00.json")
        names = [f"collected/computed/archives/collect_{d:02}-10-2026-12-00-00.json"
                 for d in range(1, 14)]
        client = Mock()
        def listing(n, b, **kw):
            if kw["prefix"] == "collected/to_compute/":
                objects, next_start = [current], None
            elif "start" not in kw:
                objects, next_start = [ns(name=n) for n in names[:6]], "next"
            else:
                objects, next_start = [ns(name=n) for n in names[6:]], None
            return ns(data=ns(objects=objects, next_start_with=next_start))
        client.list_objects.side_effect = listing
        client.get_object.side_effect = lambda n, b, key: ns(data=ns(
            content=json.dumps({"name": key}).encode(), close=Mock()))
        result = list(self.history.previous_environmental_files(client, "ns", "bucket", current))
        self.assertEqual([r["name"] for r in result], list(reversed(names[6:11])))
        self.assertEqual(client.get_object.call_count, 5)

    def backfill_client(self, documents):
        import io
        ns = types.SimpleNamespace
        client = Mock()
        client.list_objects.side_effect = lambda n, b, **kw: ns(data=ns(
            objects=[ns(name=name) for name in documents if name.startswith(kw["prefix"])],
            next_start_with=None))
        client.get_object.side_effect = lambda n, b, name: ns(
            data=ns(content=json.dumps(documents[name]).encode(), close=Mock(),
                    raw=io.BytesIO(json.dumps(documents[name]).encode())),
            headers={"etag": "v1"})
        def put(n, b, name, payload, **kw):
            if hasattr(payload, "read"):
                payload = payload.read()
            documents[name] = json.loads(payload)
        client.put_object.side_effect = put
        return client

    def test_backfill_missing_day_at_local_noon(self):
        docs = {}
        client = self.backfill_client(docs)
        bio = {**self.biological, "timezone": "Europe/Paris"}
        self.backfill.backfill_environmental_days(client, "ns", {"2026-10-12": bio})
        name = "collected/to_compute/environmental_daily_2026-10-12.json"
        row = docs[name][0]
        self.assertEqual(row["local_timestamp"], "2026-10-12 12:00:00")
        self.assertEqual(row["latitude"], 48.8)
        self.assertEqual(row["gps_coordinates"], "computed")
        self.assertEqual(row["city_country"], bio["city_country"])
        self.assertEqual(client.put_object.call_args.kwargs["if_none_match"], "*")

    def test_backfill_counts_archived_and_pending_days_and_is_idempotent(self):
        for prefix in ("collected/computed/archives/", "collected/computed/", "collected/to_compute/"):
            docs = {prefix + "source.json": [{"timestamp": "2026-10-12 07:00:00"}]}
            client = self.backfill_client(docs)
            self.backfill.backfill_environmental_days(client, "ns", {"2026-10-12": self.biological})
            client.put_object.assert_not_called()
        docs = {}
        client = self.backfill_client(docs)
        bio = {**self.biological, "timezone": "Europe/Paris"}
        self.backfill.backfill_environmental_days(client, "ns", {"2026-10-12": bio})
        self.backfill.backfill_environmental_days(client, "ns", {"2026-10-12": bio})
        self.assertEqual(client.put_object.call_count, 1)

    def test_backfill_checks_json_dates_not_filename(self):
        docs = {"collected/computed/source_01-01-2000.json": [
            {"timestamp": "2026-10-11 07:00:00"}, {"timestamp": "2026-10-12 07:00:00"}]}
        client = self.backfill_client(docs)
        self.backfill.backfill_environmental_days(client, "ns", {
            "2026-10-11": {**self.biological, "date": "2026-10-11"},
            "2026-10-12": self.biological})
        client.put_object.assert_not_called()

    def test_backfill_requires_city_country_and_timezone(self):
        for bio in (self.biological,
                    {**self.biological, "timezone": "Europe/Paris", "city_country": {}},
                    {**self.biological, "timezone": "Invalid/Zone"}):
            client = self.backfill_client({})
            self.backfill.backfill_environmental_days(client, "ns", {"2026-10-12": bio})
            client.put_object.assert_not_called()

    def test_backfill_stops_on_unreadable_environmental_file(self):
        client = self.backfill_client({"collected/computed/source.json": "invalid"})
        self.backfill.backfill_environmental_days(client, "ns", {
            "2026-10-12": {**self.biological, "timezone": "Europe/Paris"}})
        client.put_object.assert_not_called()

    def test_reconstructed_unavailable_weather_is_null_and_not_sensor(self):
        self.row["reconstruction"] = {"sampling": "local_noon"}
        self.row.update(latitude=48.8, longitude=2.3, temperature=None,
                        humidity=None, concentration_co2=None, luminosity=None)
        self.compute.get_temperature_humidity.return_value = None
        self.compute.get_co2.return_value = None
        self.compute.get_luminosity.return_value = {"luminosity": None, "luminosity_source": None}
        result = self.run_compute(bio=self.biological)[0]
        self.assertIsNone(result["temperature"])
        self.assertIsNone(result["concentration_co2"])
        self.assertEqual(result["gps_coordinates"], "computed")
        self.assertEqual(result["latitude_source"], "computed")
        self.assertEqual(result["reconstruction"]["sampling"], "local_noon")

    def test_pressure_uses_requested_historical_city_and_hour(self):
        import ast
        import math
        source = ast.parse((ROOT / "src/utils/geoUtils.py").read_text())
        function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "get_pressure")
        request = Mock()
        request.RequestException = RequestException
        request.get.return_value.json.return_value = {"hourly": {
            "time": ["2026-10-12T11:00", "2026-10-12T12:00"],
            "surface_pressure": [1000, 1001]}}
        env = {"requests": request, "math": math, "logger": Mock()}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "geoUtils.py", "exec"), env)
        self.assertEqual(env["get_pressure"](48.8, 2.3, "2026-10-12", 12, "Europe/Paris"), 1001)
        params = request.get.call_args.kwargs["params"]
        self.assertEqual((params["latitude"], params["longitude"]), (48.8, 2.3))
        self.assertEqual(params["timezone"], "Europe/Paris")
        self.assertIn("archive-api", request.get.call_args.args[0])

    def test_backfill_runs_without_existing_to_compute_files_and_uploads_computed(self):
        sys.modules["utils.computingUtils"] = self.compute
        writer = types.ModuleType("utils.writeUtils")
        secrets = types.ModuleType("my_secrets.secrets")
        with tempfile.TemporaryDirectory() as directory:
            for field in ("config_oci_path", "computed_data_dir_to_send", "collected_uploaded_data_dir",
                          "tmp_to_compute_dir", "computed_data_dir_uploaded"):
                path = Path(directory) / field
                path.mkdir()
                setattr(secrets, field, str(path))
            writer.write_json = lambda data, stamp, options, name: (
                Path(secrets.computed_data_dir_to_send) / name
            ).write_text(json.dumps(data))
            with patch.dict(sys.modules, {"utils.writeUtils": writer, "my_secrets.secrets": secrets}):
                bucket = load_module("storage.bucket", "src/storage/bucket.py")
            docs = {}
            client = self.backfill_client(docs)
            client.delete_object.side_effect = lambda n, b, key: docs.pop(key)
            bucket.connect_to_bucket = lambda: (client, "ns")
            bio = {**self.biological, "timezone": "Europe/Paris", "summary": {"steps_total": 500}}
            bucket.computing_biological = Mock(return_value={"2026-10-12": bio})
            bucket.get_biological_daily = lambda *args: bio if args[-1] == "2026-10-12" else None
            bucket.computing_collected(types.SimpleNamespace(computed=True))
            name = "collected/computed/environmental_daily_2026-10-12.json"
            self.assertIn(name, docs)
            self.assertNotIn(name.replace("/computed/", "/to_compute/"), docs)
            self.assertEqual(docs[name][0]["gps_coordinates"], "computed")
            self.assertEqual(docs[name][0]["biological"]["summary"]["steps_total"], 500)
            self.assertEqual(docs[name][0]["timestamp"], "2026-10-12 12:00:00")

    def test_compute_dispatch_uploads_only_when_gps_resolved(self):
        sys.modules["utils.computingUtils"] = self.compute
        sys.modules["storage.environmentalHistory"] = self.history
        writer = types.ModuleType("utils.writeUtils")
        writer.write_json = Mock()
        secrets = types.ModuleType("my_secrets.secrets")
        with tempfile.TemporaryDirectory() as directory:
            for field in ("config_oci_path", "computed_data_dir_to_send", "collected_uploaded_data_dir",
                          "tmp_to_compute_dir", "computed_data_dir_uploaded"):
                setattr(secrets, field, directory)
            with patch.dict(sys.modules, {"utils.writeUtils": writer, "my_secrets.secrets": secrets}):
                bucket = load_module("storage.bucket", "src/storage/bucket.py")
            name = "collect_12-10-2026-12-00-00.json"
            path = Path(directory) / name
            client = Mock()
            client.list_objects.return_value = types.SimpleNamespace(data=types.SimpleNamespace(
                objects=[types.SimpleNamespace(name="collected/to_compute/" + name)],
                next_start_with=None))
            bucket.connect_to_bucket = lambda: (client, "ns")
            bucket.computing_biological = Mock(return_value={})
            bucket.get_biological_daily = lambda *args: None
            bucket.previous_environmental_files = lambda *args: iter([])
            bucket.upload_to_bucket_single_file = Mock()
            path.write_text(json.dumps([self.row]))
            bucket.computing_collected(types.SimpleNamespace(computed=True))
            bucket.upload_to_bucket_single_file.assert_called_once()
            writer.write_json.assert_called_once()
            bucket.upload_to_bucket_single_file.reset_mock()
            writer.write_json.reset_mock()
            path.write_text(json.dumps([{**self.row, "timezone": None}]))
            bucket.computing_collected(types.SimpleNamespace(computed=True))
            bucket.upload_to_bucket_single_file.assert_not_called()
            writer.write_json.assert_not_called()
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
