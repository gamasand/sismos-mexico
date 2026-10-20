import json
import os
from datetime import datetime, timezone
from pathlib import Path

import mysql.connector

ruta = Path(__file__).parent / "ejemplo_sismo.json"

with ruta.open(encoding="utf-8") as archivo:
    respuesta = json.load(archivo)

eventos = respuesta["features"]

if not eventos:
    raise SystemExit("El archivo no contiene eventos.")

sismo = eventos[0]
propiedades = sismo["properties"]
longitud, latitud, profundidad = sismo["geometry"]["coordinates"]

# Convertimos a UTC y quitamos la etiqueta de zona para DATETIME.
# El valor que guardamos sigue representando una fecha UTC.
fecha_utc = datetime.fromtimestamp(
    propiedades["time"] / 1000,
    tz=timezone.utc,
).replace(tzinfo=None)

datos = (
    sismo["id"],
    fecha_utc,
    propiedades.get("place"),
    propiedades.get("mag"),
    propiedades.get("magType"),
    longitud,
    latitud,
    profundidad,
)

sql = """
    INSERT INTO sismos (
        id, fecha_utc, lugar, magnitud, tipo_magnitud,
        longitud, latitud, profundidad_km
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE id = sismos.id
"""

conexion = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    database=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    connection_timeout=10,
)

try:
    cursor = conexion.cursor()

    try:
        cursor.execute(sql, datos)
        conexion.commit()

        print("Evento procesado:", sismo["id"])

        cursor.execute("SELECT COUNT(*) FROM sismos")
        print("Sismos almacenados:", cursor.fetchone()[0])
    finally:
        cursor.close()
finally:
    conexion.close()