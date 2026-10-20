import json
from pathlib import Path
from datetime import datetime, timezone

# Buscaremos el JSON en la misma carpeta que este script:
ruta = Path(__file__).parent / "ejemplo_sismo.json"

with ruta.open(encoding="utf-8") as archivo:
    respuesta = json.load(archivo)

# Accedemos a la lista de lso eventos:
eventos = respuesta["features"]

# Si no hay nada:
if not eventos:
    print("La consulta no consultó.")
else:
    sismo = eventos[0]
    propiedades = sismo["properties"]

    longitud, latitud, profundidad = sismo["geometry"]["coordinates"]

    fecha = datetime.fromtimestamp(
        propiedades["time"] / 1000,
        tz = timezone.utc,
    )

    print("Identificador:", sismo["id"])
    print("Lugar:", propiedades["place"])
    print("Magnitud:", propiedades["mag"])
    print("Fecha UTC:", fecha.isoformat())
    print("Longitud:", longitud)
    print("Latitud:", latitud)
    print("Profundidad (en km):", profundidad)