"""Persistencia por ventana, sin borrar los sismos del prototipo anterior."""

import json
import os
from datetime import datetime, timezone

import mysql.connector

from shared.catalogo import config_signature
from shared.esquema import SCHEMA

FIELDS = (
    "id", "fecha_utc", "lugar", "magnitud", "tipo_magnitud",
    "longitud", "latitud", "profundidad_km",
)

UPSERT = """
    INSERT INTO sismos (
        id, fecha_utc, lugar, magnitud, tipo_magnitud,
        longitud, latitud, profundidad_km
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) AS nuevo
    ON DUPLICATE KEY UPDATE
        fecha_utc=nuevo.fecha_utc, lugar=nuevo.lugar,
        magnitud=nuevo.magnitud, tipo_magnitud=nuevo.tipo_magnitud,
        longitud=nuevo.longitud, latitud=nuevo.latitud,
        profundidad_km=nuevo.profundidad_km
"""


def conectar():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql"),
        database=os.environ.get("DB_NAME", "sismos_db"),
        user=os.environ.get("DB_USER", "sismos_user"),
        password=os.environ["DB_PASSWORD"],
        connection_timeout=15,
        charset="utf8mb4",
    )


def utc_naive(value):
    """DATETIME guarda UTC sin etiqueta de zona; no se usan horas locales."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def inicializar_esquema():
    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            for sentencia in SCHEMA:
                cursor.execute(sentencia)
            # CREATE IF NOT EXISTS no añade columnas a tablas ya creadas.
            # ALTER sólo cuando falta la columna; nunca se reemplaza la tabla.
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ventanas_cargas'
                  AND COLUMN_NAME='parametros_json'
            """)
            if cursor.fetchone()[0] == 0:
                cursor.execute("ALTER TABLE ventanas_cargas ADD COLUMN parametros_json JSON")
        conexion.commit()
    finally:
        conexion.close()


def leer_ventana(clave):
    """Retorna filas y metadatos del último snapshot completo de la ventana."""
    conexion = conectar()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT * FROM ventanas_cargas WHERE ventana_key = %s", (clave,)
            )
            carga = cursor.fetchone()
            if carga is None:
                return [], None
            parametros = carga.get("parametros_json")
            if isinstance(parametros, (str, bytes, bytearray)):
                carga["parametros_json"] = json.loads(parametros)
            cursor.execute("""
                SELECT s.id, s.fecha_utc, s.lugar, s.magnitud, s.tipo_magnitud,
                       s.longitud, s.latitud, s.profundidad_km
                FROM sismos AS s
                JOIN ventana_sismos AS v ON v.sismo_id = s.id
                WHERE v.ventana_key = %s
                ORDER BY s.fecha_utc, s.id
            """, (clave,))
            return cursor.fetchall(), carga
    finally:
        conexion.close()


def necesita_carga(ventana, force=False):
    if force or ventana["kind"] == "live":
        return True
    conexion = conectar()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT ultima_consulta_utc, firma_config, estado, parametros_json "
                "FROM ventanas_cargas WHERE ventana_key=%s", (ventana["key"],)
            )
            carga = cursor.fetchone()
        return (
            not carga or carga["ultima_consulta_utc"] is None
            or carga.get("parametros_json") is None
            or carga["estado"] != "ok"
            or carga["firma_config"] != config_signature(ventana)
        )
    finally:
        conexion.close()


def iniciar_carga(ventana):
    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ventanas_cargas (
                    ventana_key, ultimo_intento_utc, estado,
                    solicitud_inicio_utc, solicitud_fin_utc
                ) VALUES (%s, %s, 'cargando', %s, %s) AS nuevo
                ON DUPLICATE KEY UPDATE
                    ultimo_intento_utc=nuevo.ultimo_intento_utc,
                    estado='cargando', error=NULL,
                    solicitud_inicio_utc=nuevo.solicitud_inicio_utc,
                    solicitud_fin_utc=nuevo.solicitud_fin_utc
            """, (
                ventana["key"], utc_naive(datetime.now(timezone.utc)),
                utc_naive(ventana["start"]), utc_naive(ventana["end"]),
            ))
        conexion.commit()
    finally:
        conexion.close()


def registrar_error(clave, mensaje):
    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE ventanas_cargas SET estado='error', error=%s "
                "WHERE ventana_key=%s", (str(mensaje)[:2000], clave)
            )
        conexion.commit()
    finally:
        conexion.close()


def guardar_snapshot(ventana, filas, consulta_utc=None):
    """Upsert y membresía atómicos: ningún error publica cargas parciales."""
    por_id = {fila["id"]: fila for fila in filas}
    consulta_utc = consulta_utc or datetime.now(timezone.utc)
    conexion = conectar()
    try:
        conexion.start_transaction()
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT ventana_key FROM ventanas_cargas "
                "WHERE ventana_key=%s FOR UPDATE", (ventana["key"],)
            )
            cursor.fetchone()
            for fila in por_id.values():
                valores = [fila[campo] for campo in FIELDS]
                valores[1] = utc_naive(valores[1])
                cursor.execute(UPSERT, tuple(valores))
            cursor.execute(
                "DELETE FROM ventana_sismos WHERE ventana_key=%s",
                (ventana["key"],),
            )
            if por_id:
                cursor.executemany(
                    "INSERT INTO ventana_sismos (ventana_key,sismo_id) "
                    "VALUES (%s,%s)",
                    [(ventana["key"], event_id) for event_id in por_id],
                )
            cursor.execute("""
                UPDATE ventanas_cargas SET inicio_utc=%s, fin_utc=%s,
                    ultima_consulta_utc=%s, total=%s, estado='ok', error=NULL,
                    firma_config=%s, parametros_json=%s WHERE ventana_key=%s
            """, (
                utc_naive(ventana["start"]), utc_naive(ventana["end"]),
                utc_naive(consulta_utc), len(por_id), config_signature(ventana),
                json.dumps(ventana, ensure_ascii=False,
                           default=lambda value: value.isoformat()),
                ventana["key"],
            ))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
    return len(por_id)
