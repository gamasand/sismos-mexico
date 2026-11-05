"""Cliente USGS con reintentos y división temporal para evitar truncamientos."""

import argparse
import math
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared.catalogo import WINDOWS, get_window

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/"
CHUNK_LIMIT = 5000


class CatalogError(RuntimeError):
    """Respuesta incompleta o no válida: no debe reemplazar el snapshot."""


def crear_sesion():
    session = requests.Session()
    retries = Retry(
        total=3, connect=3, read=3, backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",), respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers["User-Agent"] = "SismosMexico-EducationalPrototype/2.0"
    return session


def iso_utc(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


def parametros_ventana(ventana, inicio=None, fin=None):
    parametros = {
        "eventtype": "earthquake",
        "starttime": iso_utc(inicio or ventana["start"]),
        "endtime": iso_utc(fin or ventana["end"]),
        "minmagnitude": ventana["min_magnitude"],
    }
    if ventana["bbox"]:
        parametros.update(ventana["bbox"])
    else:
        parametros.update(
            latitude=ventana["latitude"], longitude=ventana["longitude"],
            maxradiuskm=ventana["radius_km"],
        )
    return parametros


def _get(session, endpoint, params):
    response = session.get(
        BASE_URL + endpoint, params=params, timeout=(10, 90)
    )
    response.raise_for_status()
    return response


def evento_a_fila(evento):
    """Valida antes de escribir: una carga inválida no reemplaza la anterior."""
    try:
        props = evento["properties"]
        lon, lat, depth = evento["geometry"]["coordinates"]
        event_id = evento["id"]
        mag = props["mag"]
        if not event_id or len(event_id) > 50:
            raise ValueError("Identificador vacío o demasiado largo")
        if any(value is None or not math.isfinite(float(value))
               for value in (lon, lat, depth, mag)):
            raise ValueError("Coordenadas o magnitud ausentes/no finitas")
        fecha = datetime.fromtimestamp(props["time"] / 1000, timezone.utc)
        return {
            "id": event_id, "fecha_utc": fecha,
            "lugar": props.get("place"), "magnitud": float(mag),
            "tipo_magnitud": props.get("magType"),
            "longitud": float(lon), "latitud": float(lat),
            "profundidad_km": float(depth),
        }
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise CatalogError("Evento USGS inválido; se conserva la carga anterior") from exc


def descargar_ventana(ventana, session=None):
    """Descarga todo el intervalo y deduplica límites inclusivos por id.

    /count permite dividir bloques de 5000 eventos. Si más eventos coinciden
    en un milisegundo se pagina ese bloque. Toda petición debe completarse.
    """
    propia = session is None
    session = session or crear_sesion()
    por_id = {}

    def descargar(inicio, fin):
        params = parametros_ventana(ventana, inicio, fin)
        count_response = _get(session, "count", params)
        try:
            cantidad = int(count_response.text.strip())
        except (TypeError, ValueError) as exc:
            raise CatalogError("USGS no devolvió un conteo válido") from exc
        if cantidad < 0:
            raise CatalogError("USGS devolvió un conteo negativo")
        if cantidad == 0:
            return
        if cantidad >= CHUNK_LIMIT and fin - inicio > timedelta(milliseconds=1):
            milliseconds = int((fin - inicio).total_seconds() * 1000)
            medio = inicio + timedelta(milliseconds=milliseconds // 2)
            descargar(inicio, medio)
            descargar(medio, fin)
            return
        offset = 1
        recibidos = 0
        while True:
            query = dict(params, format="geojson", orderby="time-asc",
                         limit=CHUNK_LIMIT, offset=offset, nodata=204)
            try:
                response = _get(session, "query", query)
                features = [] if response.status_code == 204 else response.json()["features"]
            except (ValueError, KeyError, TypeError) as exc:
                raise CatalogError("USGS no devolvió una colección GeoJSON válida") from exc
            if not isinstance(features, list):
                raise CatalogError("La lista de eventos USGS no es válida")
            for feature in features:
                fila = evento_a_fila(feature)
                por_id[fila["id"]] = fila
            recibidos += len(features)
            if len(features) < CHUNK_LIMIT:
                if recibidos < cantidad:
                    raise CatalogError("El catálogo cambió o llegó incompleto; repite la carga")
                break
            offset += CHUNK_LIMIT

    try:
        descargar(ventana["start"], ventana["end"])
        # USGS incluye ambos extremos. El prototipo publica [inicio, fin),
        # como las series y el mapa horario. Se filtra después de comprobar
        # la completitud para no confundir ese evento de borde con una falta.
        filas = [fila for fila in por_id.values()
                 if ventana["start"] <= fila["fecha_utc"] < ventana["end"]]
        return sorted(filas, key=lambda fila: (fila["fecha_utc"], fila["id"]))
    finally:
        if propia:
            session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ventana", choices=tuple(WINDOWS), default="live")
    args = parser.parse_args()
    ventana = get_window(args.ventana)
    filas = descargar_ventana(ventana)
    print(f"Ventana: {ventana['label']}")
    print(f"Periodo UTC: {iso_utc(ventana['start'])} a {iso_utc(ventana['end'])}")
    print(f"Eventos recibidos: {len(filas)}")
    for fila in filas[:10]:
        print(f"{fila['id']} | Magnitud: {fila['magnitud']} | Lugar: {fila['lugar']}")


if __name__ == "__main__":
    main()
