"""Comprobaciones de agregación y representación temporal, sin conexión a MySQL."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figuras import construir_figuras, matriz_horaria, preparar_datos, serie
from shared.catalogo import get_window


def registro(identifier, fecha, magnitud=3.5):
    return dict(id=identifier, fecha_utc=fecha, lugar="Ejemplo", magnitud=magnitud,
                tipo_magnitud="ml", longitud=-115.2, latitud=32.2, profundidad_km=8.0)


class HourlyTests(unittest.TestCase):
    def test_counts_and_empty_hours_in_partial_days(self):
        inicio, fin = pd.Timestamp("2020-01-01T12:30Z"), pd.Timestamp("2020-01-02T14:10Z")
        datos = preparar_datos([
            registro("excluded", "2020-01-01T12:29Z"),
            registro("a", inicio), registro("b", "2020-01-01T12:59Z"),
            registro("c", "2020-01-02T14:09Z"), registro("excluded-end", fin),
        ])
        dias, matriz = matriz_horaria(datos, inicio, fin)
        self.assertEqual(matriz.shape, (2, 24))
        self.assertEqual(np.nansum(matriz), 3)
        self.assertEqual(matriz[0, 12], 2)
        self.assertEqual(matriz[1, 14], 1)
        self.assertEqual(matriz[0, 13], 0)
        self.assertTrue(np.isnan(matriz[0, 11]))
        self.assertTrue(np.isnan(matriz[1, 15]))

    def test_midnight_end_does_not_add_an_unobserved_day(self):
        dias, matriz = matriz_horaria(preparar_datos([]), "2020-01-01T00:00Z", "2020-01-03T00:00Z")
        self.assertEqual(len(dias), 2)
        self.assertEqual(np.nansum(matriz), 0)
        self.assertFalse(np.isnan(matriz).any())

    def test_each_window_builds_five_serializable_figures_with_matching_counts(self):
        for key in ("live", "ometepec", "mexicali", "puebla"):
            with self.subTest(key=key):
                window = get_window(key)
                instant = window["anchor"]["time"] if window["anchor"] else window["start"]
                rows = [registro("inside", instant), registro("outside", window["end"])]
                figures = construir_figuras(preparar_datos(rows), window,
                    pd.Timestamp(window["start"]), pd.Timestamp(window["end"]))
                self.assertEqual(len(figures), 5)
                for figure in figures:
                    figure.to_json()
                self.assertEqual(len(figures[0].data[0].lat), 1)
                self.assertEqual(len(figures[1].data[0].x), 1)
                self.assertEqual(np.nansum(figures[2].data[0].z), 1)
                self.assertEqual(sum(len(trace.x) for trace in figures[3].data), 1)
                self.assertEqual(figures[4].layout.yaxis.autorange, "reversed")

    def test_empty_complete_window_has_zero_counts_but_failed_load_has_no_heatmap(self):
        window = get_window("mexicali")
        empty = preparar_datos([])
        figures = construir_figuras(empty, window, window["start"], window["end"])
        self.assertEqual(np.nansum(figures[2].data[0].z), 0)
        unavailable = construir_figuras(empty, window, window["start"], window["end"], disponible=False)
        self.assertTrue(all(len(fig.data) == 0 for fig in unavailable))

    def test_main_event_is_identified_even_if_origin_time_is_revised(self):
        window = get_window("mexicali")
        anchor = window["anchor"]
        datos = preparar_datos([
            registro(anchor["id"], pd.Timestamp(anchor["time"]) + pd.Timedelta(seconds=1)),
            registro("same-time-different-event", anchor["time"]),
        ])
        figure = serie(datos, window, window["start"], window["end"], "magnitud")
        traces = {trace.name: trace for trace in figure.data}
        self.assertEqual(len(traces["Referencia"].x), 1)
        self.assertEqual(len(traces["Después"].x), 1)


if __name__ == "__main__":
    unittest.main()
