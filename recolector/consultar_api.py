from datetime import datetime, timedelta, timezone

import requests

url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

fin = datetime.now(timezone.utc)
inicio = fin - timedelta(days=30)

parametros = {
    "format": "geojson",
    "eventtype": "earthquake",
    "starttime": inicio.isoformat(),
    "endtime": fin.isoformat(),
    "minlatitude": 14,
    "maxlatitude": 33,
    "minlongitude": -118,
    "maxlongitude": -86,
    "minmagnitude": 3,
    "orderby": "time",
    "limit": 10000,
}

respuesta = requests.get(url, params=parametros, timeout=30)
respuesta.raise_for_status()

datos = respuesta.json()
eventos = datos["features"]

print("Eventos recibidos:", len(eventos))

for sismo in eventos:
    propiedades = sismo["properties"]

    print(
        sismo["id"],
        "| Magnitud:", propiedades.get("mag"),
        "| Lugar:", propiedades.get("place"),
    )