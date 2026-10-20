import os
import mysql.connector

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
        cursor.execute("SELECT COUNT(*) FROM sismos")
        cantidad = cursor.fetchone()[0]

        print("Conexión a MySQL correcta.")
        print("Sismos almacenados:", cantidad)
    finally:
        cursor.close()
finally:
    conexion.close()