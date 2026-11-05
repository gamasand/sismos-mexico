"""Ventanas de consulta. Fechas, cálculos y almacenamiento siempre en UTC.

Los círculos históricos son áreas exploratorias, no delimitaciones de ruptura ni
clasificaciones automáticas de réplicas.
"""

import calendar
import copy
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

WINDOWS = {
    "live": {
        "key": "live",
        "label": "Últimos 30 días",
        "title": "México y zonas vecinas · últimos 30 días",
        "kind": "live",
        "anchor": None,
    },
    "ometepec": {
        "key": "ometepec",
        "label": "Ometepec · 20 mar 2012",
        "title": "Ometepec, Guerrero–Oaxaca · 2012",
        "kind": "historical",
        "anchor": {
            "id": "usp000jghj",
            "time": datetime(2012, 3, 20, 18, 2, 47, 440000, tzinfo=UTC),
            "latitude": 16.493,
            "longitude": -98.231,
            "magnitude": 7.4,
            "depth_km": 20.0,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/usp000jghj",
            "magnitude_type": "mww",
        },
    },
    "mexicali": {
        "key": "mexicali",
        "label": "El Mayor–Cucapah · 4 abr 2010",
        "title": "El Mayor–Cucapah, Baja California · 2010",
        "kind": "historical",
        "anchor": {
            "id": "ci14607652",
            "time": datetime(2010, 4, 4, 22, 40, 42, 360000, tzinfo=UTC),
            "latitude": 32.2861667,
            "longitude": -115.2953333,
            "magnitude": 7.2,
            "depth_km": 9.987,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/ci14607652",
            "magnitude_type": "mw",
        },
    },
    "puebla": {
        "key": "puebla",
        "label": "Puebla–Morelos · 19 sep 2017",
        "title": "Puebla–Morelos · 2017",
        "kind": "historical",
        "anchor": {
            "id": "us2000ar20",
            "time": datetime(2017, 9, 19, 18, 14, 38, 90000, tzinfo=UTC),
            "latitude": 18.5499,
            "longitude": -98.4887,
            "magnitude": 7.1,
            "depth_km": 48.0,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us2000ar20",
            "magnitude_type": "mww",
        },
    },
}
WINDOW_ORDER = tuple(WINDOWS)


def shift_months(value, months):
    """Desplaza meses calendario conservando hora; recorta días inexistentes."""
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def get_window(clave, now=None):
    """Devuelve una copia de la ventana con fechas UTC aware.

    Los históricos abarcan un mes calendario antes y tres meses después de la
    hora del evento de referencia. Live siempre solicita 30 días exactos.
    """
    if clave not in WINDOWS:
        raise ValueError(f"Ventana desconocida: {clave}")
    ventana = copy.deepcopy(WINDOWS[clave])
    ventana["min_magnitude"] = 3.0
    if ventana["kind"] == "live":
        end = now if now is not None else datetime.now(UTC)
        if end.tzinfo is None:
            raise ValueError("now debe incluir zona horaria")
        end = end.astimezone(UTC)
        ventana.update(
            start=end - timedelta(days=30),
            end=end,
            latitude=None,
            longitude=None,
            radius_km=None,
            bbox={
                "minlatitude": 14.0,
                "maxlatitude": 33.0,
                "minlongitude": -118.0,
                "maxlongitude": -86.0,
            },
        )
    else:
        anchor = ventana["anchor"]
        radius = float(os.environ.get("HISTORICAL_RADIUS_KM", "250"))
        if not math.isfinite(radius) or not 0 < radius <= 2000:
            raise ValueError("HISTORICAL_RADIUS_KM debe estar entre 0 y 2000 km")
        ventana.update(
            start=shift_months(anchor["time"], -1),
            end=shift_months(anchor["time"], 3),
            latitude=anchor["latitude"],
            longitude=anchor["longitude"],
            radius_km=radius,
            bbox=None,
        )
    return ventana


def config_signature(ventana):
    """Identifica cambios de filtros; live omite fechas que cambian cada vez."""
    datos = {
        "version": 1,
        "key": ventana["key"],
        "min_magnitude": ventana["min_magnitude"],
        "bbox": ventana["bbox"],
        "latitude": ventana["latitude"],
        "longitude": ventana["longitude"],
        "radius_km": ventana["radius_km"],
    }
    if ventana["kind"] == "historical":
        datos.update(
            start=ventana["start"].isoformat(),
            end=ventana["end"].isoformat(),
            anchor_id=ventana["anchor"]["id"],
        )
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()
