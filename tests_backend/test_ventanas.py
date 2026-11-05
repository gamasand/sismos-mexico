"""Pruebas offline de fechas, descargas completas y rollback de publicación."""

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "recolector"))

from shared.catalogo import WINDOWS, config_signature, get_window, shift_months
from consultar_api import CatalogError, descargar_ventana, evento_a_fila, parametros_ventana

UTC = timezone.utc


def feature(event_id, fecha):
    return {
        "id": event_id,
        "properties": {"time": int(fecha.timestamp() * 1000), "mag": 3.2,
                       "magType": "ml", "place": "Ejemplo"},
        "geometry": {"coordinates": [-115.0, 32.0, 10.0]},
    }


class Response:
    def __init__(self, text="", payload=None):
        self.status_code = 200
        self.text = text
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class CatalogSession:
    def __init__(self, eventos):
        self.eventos = eventos
        self.queries = []

    def get(self, url, params, timeout):
        inicio = datetime.fromisoformat(params["starttime"]).replace(tzinfo=UTC)
        fin = datetime.fromisoformat(params["endtime"]).replace(tzinfo=UTC)
        eventos = [e for e in self.eventos
                   if inicio.timestamp() * 1000 <= e["properties"]["time"]
                   <= fin.timestamp() * 1000]
        if url.endswith("count"):
            return Response(text=str(len(eventos)))
        if params.get("nodata", 204) not in (204, 404):
            raise AssertionError("USGS sólo admite nodata=204 o 404")
        self.queries.append(params)
        first = params["offset"] - 1
        return Response(payload={"features": eventos[first:first + params["limit"]]})


class WindowDatesTests(unittest.TestCase):
    def test_live_is_exactly_thirty_days_and_normalizes_utc(self):
        now = datetime(2026, 10, 21, 9, 15, tzinfo=timezone(timedelta(hours=-7)))
        ventana = get_window("live", now)
        self.assertEqual(ventana["end"].hour, 16)
        self.assertEqual(ventana["end"] - ventana["start"], timedelta(days=30))
        self.assertIsNone(ventana["anchor"])

    def test_historical_windows_are_calendar_months_from_exact_anchor(self):
        expected = {
            "ometepec": ((2012, 2, 20), (2012, 6, 20)),
            "mexicali": ((2010, 3, 4), (2010, 7, 4)),
            "puebla": ((2017, 8, 19), (2017, 12, 19)),
        }
        for key, (start, end) in expected.items():
            window = get_window(key)
            self.assertEqual((window["start"].year, window["start"].month,
                              window["start"].day), start)
            self.assertEqual((window["end"].year, window["end"].month,
                              window["end"].day), end)
            self.assertEqual(window["start"].time(), window["anchor"]["time"].time())
            self.assertEqual(window["end"].tzinfo, UTC)

    def test_calendar_end_of_month_is_clipped_in_leap_year(self):
        self.assertEqual(
            shift_months(datetime(2024, 1, 31, 12, tzinfo=UTC), 1),
            datetime(2024, 2, 29, 12, tzinfo=UTC),
        )

    def test_config_is_copied_and_radius_change_invalidates_historical_cache(self):
        first = get_window("mexicali")
        first["anchor"]["latitude"] = 0
        self.assertNotEqual(get_window("mexicali")["anchor"]["latitude"], 0)
        with patch.dict("os.environ", {"HISTORICAL_RADIUS_KM": "300"}):
            second = get_window("mexicali")
        self.assertNotEqual(config_signature(get_window("mexicali")), config_signature(second))

    def test_historical_query_uses_circle_not_the_live_box(self):
        params = parametros_ventana(get_window("puebla"))
        self.assertIn("maxradiuskm", params)
        self.assertNotIn("minlatitude", params)
        self.assertEqual(params["minmagnitude"], 3)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2020, 1, 1, tzinfo=UTC)
        self.window = get_window("live", self.start + timedelta(seconds=4))
        self.window["start"] = self.start

    def test_split_inclusive_boundaries_are_deduplicated(self):
        eventos = [feature(str(i), self.start + timedelta(seconds=i)) for i in range(5)]
        session = CatalogSession(eventos)
        with patch("consultar_api.CHUNK_LIMIT", 2):
            filas = descargar_ventana(self.window, session)
        # El evento 2 está en el límite inclusivo de dos subconsultas y se
        # conserva una vez. El evento 4 está en fin y debe excluirse.
        self.assertEqual([r["id"] for r in filas], [str(i) for i in range(4)])
        self.assertGreater(len(session.queries), 1)
        self.assertTrue(all(q["limit"] == 2 for q in session.queries))

    def test_many_events_in_same_millisecond_use_pagination(self):
        self.window["end"] = self.start + timedelta(milliseconds=1)
        session = CatalogSession([feature(str(i), self.start) for i in range(5)])
        with patch("consultar_api.CHUNK_LIMIT", 2):
            filas = descargar_ventana(self.window, session)
        self.assertEqual(len(filas), 5)
        self.assertEqual([q["offset"] for q in session.queries], [1, 3, 5])

    def test_incomplete_download_is_rejected(self):
        session = MagicMock()
        session.get.side_effect = [Response(text="2"), Response(payload={
            "features": [feature("one", self.start)]
        })]
        with self.assertRaises(CatalogError):
            descargar_ventana(self.window, session)

    def test_missing_coordinates_refuses_entire_snapshot(self):
        event = feature("bad", self.start)
        event["geometry"]["coordinates"][2] = None
        with self.assertRaises(CatalogError):
            evento_a_fila(event)

    def test_usgs_inclusive_end_is_excluded_without_false_truncation_error(self):
        session = CatalogSession([feature("end", self.window["end"])])
        self.assertEqual(descargar_ventana(self.window, session), [])


@unittest.skipUnless(importlib.util.find_spec("mysql.connector"), "Requiere mysql-connector-python")
class TransactionTests(unittest.TestCase):
    def test_failure_after_membership_delete_rolls_back_instead_of_publishing(self):
        from shared.datos import guardar_snapshot
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.executemany.side_effect = RuntimeError("Fallo simulado durante escritura")
        fila = evento_a_fila(feature("new", datetime(2020, 1, 1, tzinfo=UTC)))
        with patch("shared.datos.conectar", return_value=connection):
            with self.assertRaises(RuntimeError):
                guardar_snapshot(get_window("live"), [fila])
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
