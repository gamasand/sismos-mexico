import os
from datetime import datetime, timezone

import mysql.connector

from consultar_api import eventos

conexion = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    database=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    connection_timeout=10,
)

sql = """
    INSERT INTO sismos (
        id, fecha_utc, lugar, magnitud, tipo_magnitud,
        longitud, latitud, profundidad_km
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE id = sismos.id
"""

try:
    cursor = conexion.cursor()

    try:
        for sismo in eventos:
            propiedades = sismo["properties"]
            longitud, latitud, profundidad = sismo["geometry"]["coordinates"]

            fecha = datetime.fromtimestamp(
                propiedades["time"] / 1000,
                tz=timezone.utc,
            ).replace(tzinfo=None)

            datos = (
                sismo["id"],
                fecha,
                propiedades.get("place"),
                propiedades.get("mag"),
                propiedades.get("magType"),
                longitud,
                latitud,
                profundidad,
            )

            cursor.execute(sql, datos)

        conexion.commit()

        print("Eventos procesados:", len(eventos))
        cursor.execute("SELECT COUNT(*) FROM sismos")
        print("Total almacenado:", cursor.fetchone()[0])
    finally:
        cursor.close()
finally:
    conexion.close()