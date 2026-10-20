import os

import mysql.connector
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1("Actividad sísmica en México y zonas vecinas"),
        html.P(
            "Fuente: USGS · Área de consulta: latitud 14° a 33° N "
            "y longitud 118° a 86° O · Magnitud mínima de consulta: 3. "
            "Los datos se conservan entre cargas."
        ),
        html.Button("Consultar base de datos", id="consultar", n_clicks=0),
        html.P(id="resumen"),
        html.P(
            "Tamaño del círculo: magnitud · Color: profundidad del hipocentro (km). "
            "El tamaño usa una escala visual; no representa energía ni área afectada.",
            style={"fontSize": "14px", "color": "#555"},
        ),
        dcc.Graph(id="mapa"),
        dcc.Graph(id="grafica"),
    ],
    style={
        "maxWidth": "1000px",
        "margin": "40px auto",
        "padding": "20px",
        "fontFamily": "Arial, sans-serif",
    },
)


def leer_sismos():
    conexion = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connection_timeout=10,
    )

    try:
        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id, fecha_utc, lugar, magnitud, tipo_magnitud,
                       longitud, latitud, profundidad_km
                FROM sismos
                ORDER BY fecha_utc
            """)
            filas = cursor.fetchall()
        finally:
            cursor.close()
    finally:
        conexion.close()

    return pd.DataFrame(
        filas,
        columns=[
            "id", "fecha_utc", "lugar", "magnitud", "tipo_magnitud",
            "longitud", "latitud", "profundidad_km",
        ],
    )


@app.callback(
    Output("mapa", "figure"),
    Output("grafica", "figure"),
    Output("resumen", "children"),
    Input("consultar", "n_clicks"),
)
def actualizar(_):
    datos = leer_sismos()
    mapa = px.scatter_geo(
        datos,
        lat="latitud",
        lon="longitud",
        color="profundidad_km",
        hover_name="lugar",
        hover_data={
            "magnitud": True,
            "tipo_magnitud": True,
            "fecha_utc": True,
            "latitud": ":.3f",
            "longitud": ":.3f",
            "profundidad_km": ":.1f",
        },
        labels={
            "magnitud": "Magnitud",
            "tipo_magnitud": "Tipo de magnitud",
            "fecha_utc": "Fecha UTC",
            "profundidad_km": "Profundidad (km)",
        },
        color_continuous_scale="Viridis",
        title="Ubicación de los eventos almacenados",
    )

    tamanos = ((datos["magnitud"] - 3) * 10 + 8).clip(
        lower=8,
        upper=40,
    )

    mapa.update_traces(
        marker={
            "size": tamanos.tolist(),
            "sizemode": "diameter",
            "opacity": 0.75,
            "line": {"width": 0.7, "color": "white"},
        }
    )

    mapa.update_geos(
        projection_type="mercator",
        showcountries=True,
        showland=True,
        landcolor="#eeeeee",
        showocean=True,
        oceancolor="#dceef8",
        lonaxis_range=[-125, -84],
        lataxis_range=[12, 40],
    )

    mapa.update_layout(height=550, margin={"l": 0, "r": 0, "t": 50, "b": 0})

    figura = px.histogram(
        datos,
        x="magnitud",
        nbins=10,
        title="Distribución de magnitudes registradas",
        labels={"magnitud": "Magnitud reportada"},
    )

    figura.update_layout(
        template="plotly_white",
        yaxis_title="Número de eventos",
        bargap=0.1,
    )

    if datos.empty:
        resumen = "No hay eventos almacenados."
    else:
        primera_fecha = datos["fecha_utc"].min()
        ultima_fecha = datos["fecha_utc"].max()

        resumen = (
            f"Eventos almacenados: {len(datos)} · "
            f"Desde: {primera_fecha:%d/%m/%Y %H:%M} UTC · "
            f"Hasta: {ultima_fecha:%d/%m/%Y %H:%M} UTC"
        )

    return mapa, figura, resumen


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)

