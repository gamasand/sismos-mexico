"""Sincroniza USGS; errores de API conservan la última carga completa.

Sin argumentos: actualiza live y carga históricos ausentes o modificados.
--ventana live: sólo actualiza últimos 30 días.
--forzar-historicos: vuelve a descargar los históricos aunque exista caché.
"""

import argparse
import sys

import mysql.connector
import requests

from consultar_api import CatalogError, descargar_ventana, iso_utc
from shared.catalogo import WINDOWS, get_window
from shared.datos import (
    guardar_snapshot, inicializar_esquema, iniciar_carga,
    necesita_carga, registrar_error,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ventana", choices=("todas", *WINDOWS), default="todas")
    parser.add_argument("--forzar-historicos", action="store_true",
                        help="Vuelve a consultar históricos aunque exista caché")
    args = parser.parse_args(argv)
    inicializar_esquema()
    claves = tuple(WINDOWS) if args.ventana == "todas" else (args.ventana,)
    errores = 0
    for clave in claves:
        ventana = get_window(clave)
        if not necesita_carga(ventana, force=args.forzar_historicos):
            print(f"[{clave}] Histórico disponible; se reutiliza la carga guardada.", flush=True)
            continue
        print(f"[{clave}] Consulta UTC: {iso_utc(ventana['start'])} a "
              f"{iso_utc(ventana['end'])}", flush=True)
        iniciar_carga(ventana)
        try:
            filas = descargar_ventana(ventana)
        except (requests.RequestException, CatalogError) as exc:
            mensaje = f"{type(exc).__name__}: {str(exc)}"
            registrar_error(clave, mensaje)
            print(f"[{clave}] No se pudo completar la consulta. "
                  "Se conserva la carga anterior.", file=sys.stderr, flush=True)
            errores += 1
            continue
        total = guardar_snapshot(ventana, filas)
        print(f"[{clave}] Eventos procesados: {len(filas)} | "
              f"Total en esta ventana: {total}", flush=True)
    if errores:
        print(f"{errores} ventana(s) con error de API. Revisa los avisos del dashboard.", flush=True)
    # La indisponibilidad de USGS no impide abrir snapshots ya guardados.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except mysql.connector.Error as exc:
        print(f"No se pudo preparar o escribir MySQL ({type(exc).__name__}). "
              "Revisa el estado de la base y su configuración.", file=sys.stderr)
        raise SystemExit(1)
