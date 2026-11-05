"""Exploración de snapshots sísmicos almacenados en MySQL."""
import logging

import pandas as pd
from dash import Dash, Input, Output, dcc, html

from shared.catalogo import WINDOWS, config_signature, get_window
from shared.datos import leer_ventana
from figuras import construir_figuras, figura_vacia, preparar_datos

logging.basicConfig(level=logging.INFO)
app = Dash(__name__, title="Caracterización de Actividad Sismológica")
server = app.server
GRAPH_CONFIG = {"displaylogo": False, "responsive": True,
                "toImageButtonOptions": {"format": "png", "scale": 2}}


def panel(numero, titulo, descripcion, graph_id, clase=""):
    return html.Section([
        html.Div([html.Span(numero, className="panel-number"),
                  html.Div([html.H2(titulo), html.P(descripcion)])], className="panel-heading"),
        dcc.Graph(id=graph_id, config=GRAPH_CONFIG,
                  style={"height": "460px" if graph_id in ("mapa", "histograma") else "420px" if graph_id == "horas" else "370px"},
                  figure=figura_vacia("Cargando la ventana seleccionada…")),
    ], className=f"chart-panel {clase}")


app.layout = html.Div([
    html.Header(html.Div([
        html.A(html.Span("Caracterización de Actividad Sismológica", className="brand-name"), href="#", className="brand"),
        html.Span("Exploración del catálogo regional", className="header-description"),
        html.A("Fuente: USGS ↗", href="https://earthquake.usgs.gov/fdsnws/event/1/", target="_blank", rel="noopener noreferrer", className="source-link"),
    ], className="header-inner")),
    html.Main([
        html.Div([
            html.Div([
                html.P("CATÁLOGO SÍSMICO · MÉXICO Y ZONAS CERCANAS", className="eyebrow"),
                html.H1("Actividad sísmica en perspectiva"),
                html.P("Explora el presente y tres ventanas históricas alrededor de grandes eventos. "
                       "Ubicación, magnitud y profundidad, con el tiempo como referencia.", className="hero-description"),
            ], className="hero-copy"),
            html.Div([html.Span("04", className="hero-number"), html.Span("ventanas de observación", className="hero-caption")], className="hero-aside"),
        ], className="hero"),
        html.Section([
            html.Div([
                html.Label("VENTANA DE ANÁLISIS", htmlFor="ventana"),
                dcc.Dropdown(id="ventana", options=[{"label": v["label"], "value": k} for k, v in WINDOWS.items()], value="live", clearable=False, searchable=False),
            ], className="window-control"),
            html.Div([html.Span("REFERENCIA HORARIA"), html.Strong("UTC"), html.Small("La misma en todas las vistas")], className="timezone-control"),
            html.Button([html.Span("↻", **{"aria-hidden": "true"}), " Actualizar vista"], id="consultar", n_clicks=0, className="refresh-button"),
        ], className="controls"),
        html.Div(id="estado", className="status-banner", role="status"),
        html.Section(id="contexto", className="window-context"),
        html.Div(id="metricas", className="metrics-grid"),
        dcc.Loading(color="#C75C43", type="circle", children=html.Div([
            html.Div([
                panel("01", "Geografía de los eventos", "Tamaño: magnitud. Color: profundidad. Estrella: evento de referencia.", "mapa", "map-panel"),
                panel("02", "Distribución de magnitudes", "Conteos por intervalos de 0.25 unidades de magnitud reportada.", "histograma"),
            ], className="charts-top"),
            panel("03", "Ritmo de actividad por hora", "Cada celda cruza una fecha con una de las 24 horas UTC. El color indica el conteo.", "horas", "heatmap-panel"),
            html.Div([
                panel("04", "Magnitud a través del tiempo", "Un punto por evento. La línea vertical marca el instante de referencia.", "magnitudes"),
                panel("05", "Profundidad a través del tiempo", "Profundidad hipocentral en kilómetros. El eje crece hacia abajo.", "profundidades"),
            ], className="charts-bottom"),
        ], className="chart-area")),
        html.Section([
            html.Div([html.Span("CÓMO LEER ESTOS DATOS", className="eyebrow"), html.H2("Patrones registrados, con su contexto")]),
            html.Div([
                html.P("Las ventanas históricas cubren un mes calendario antes y tres después del evento, dentro de 250 km del epicentro por defecto. El evento principal se incluye en los conteos y se distingue en el mapa y las series."),
                html.P("Un cero indica que la consulta completa no devolvió eventos que cumplan los filtros para esa celda. No demuestra ausencia de sismicidad ni cobertura completa. Las celdas fuera del intervalo no tienen dato."),
                html.P("M ≥ 3 en todas las ventanas. Se conservan los tipos de magnitud reportados. La proximidad al evento de referencia no identifica automáticamente réplicas. El tamaño de los símbolos no representa energía ni área afectada."),
            ], className="method-copy"),
        ], className="method-section"),
        html.Footer([
            html.Div([html.Strong("Caracterización de Actividad Sismológica"), html.Span("Docker · Python · MySQL · Dash")]),
            html.Details([
                html.Summary("Fuentes y referencias de diseño"),
                html.P("Diseño propio. Composición y color informados por IBM Carbon. Gráficas construidas con Plotly. Cividis representa profundidad."),
                html.Ul([html.Li(html.A(label, href=url, target="_blank", rel="noopener noreferrer")) for label, url in [
                    ("Catálogo de USGS", "https://earthquake.usgs.gov/fdsnws/event/1/"),
                    ("IBM Carbon: paletas para visualización", "https://www.carbondesignsystem.com/building-blocks/data-visualization/color-palettes/"),
                    ("Plotly: mapas de calor", "https://plotly.com/python/heatmaps/"),
                    ("Plotly: histogramas", "https://plotly.com/python/histograms/"),
                    ("Plotly: series temporales", "https://plotly.com/python/time-series/"),
                    ("Cividis: Nuñez, Anderton y Renslow (2018)", "https://doi.org/10.1371/journal.pone.0199239"),
                ]]),
            ]),
        ]),
        dcc.Interval(id="reloj", interval=60_000, n_intervals=0),
    ], className="page-shell"),
])


def fecha_texto(valor):
    return pd.to_datetime(valor, utc=True).strftime("%d/%m/%Y %H:%M UTC") if valor is not None else "Sin carga registrada"


def tarjeta(etiqueta, valor, detalle, acento=""):
    return html.Div([html.P(etiqueta, className="metric-label"), html.Strong(valor, className="metric-value"), html.P(detalle, className="metric-detail")], className=f"metric {acento}")


@app.callback(
    Output("mapa", "figure"), Output("histograma", "figure"), Output("horas", "figure"),
    Output("magnitudes", "figure"), Output("profundidades", "figure"),
    Output("metricas", "children"), Output("contexto", "children"),
    Output("estado", "children"), Output("estado", "className"),
    Input("ventana", "value"), Input("consultar", "n_clicks"), Input("reloj", "n_intervals"),
)
def actualizar(clave, _clics, _intervalos):
    clave = clave if clave in WINDOWS else "live"
    ventana = get_window(clave)
    try:
        filas, carga = leer_ventana(clave)
    except Exception:
        logging.exception("No se pudo leer la ventana %s", clave)
        vacias = [figura_vacia("No se pudo consultar MySQL. Intenta actualizar la vista.")] * 5
        return (*vacias, [], [], "La base de datos no está disponible.", "status-banner status-error")
    firma_solicitada = config_signature(ventana)
    # Los gráficos y los rótulos describen la última carga exitosa, incluso si
    # se cambian filtros y USGS no está disponible para sustituirla.
    if carga and isinstance(carga.get("parametros_json"), dict):
        ventana.update(carga["parametros_json"])
    inicio = pd.to_datetime(carga["inicio_utc"], utc=True) if carga and carga.get("inicio_utc") else pd.Timestamp(ventana["start"])
    fin = pd.to_datetime(carga["fin_utc"], utc=True) if carga and carga.get("fin_utc") else pd.Timestamp(ventana["end"])
    datos = preparar_datos(filas)
    datos = datos[(datos["fecha_utc"] >= inicio) & (datos["fecha_utc"] < fin)]
    completa = bool(carga and carga.get("ultima_consulta_utc") is not None)
    figuras = construir_figuras(datos, ventana, inicio, fin, disponible=completa)
    anchor = ventana.get("anchor")
    contexto = [html.Div([html.Span("PERIODO SOLICITADO", className="context-label"), html.Strong(f"{fecha_texto(inicio)} — {fecha_texto(fin)}")], className="period-context")]
    if anchor:
        contexto.append(html.Div([
            html.Span("EVENTO DE REFERENCIA", className="context-label"),
            html.Strong(f"M {anchor['magnitude']:.1f} · {fecha_texto(anchor['time'])}"),
            html.Small(f"Epicentro: {anchor['latitude']:.3f}°, {anchor['longitude']:.3f}° · Radio de consulta: {ventana['radius_km']:g} km"),
            html.A("Ficha USGS ↗", href=anchor["url"], target="_blank", rel="noopener noreferrer"),
        ], className="anchor-context"))
    else:
        contexto.append(html.Div([html.Span("ÁREA DE CONSULTA", className="context-label"), html.Strong("México y zonas vecinas"), html.Small("14°–33° N · 118°–86° O · M ≥ 3")], className="anchor-context"))
    n = len(datos)
    max_mag = datos["magnitud"].max() if n else float("nan")
    median_depth = datos["profundidad_km"].median() if n else float("nan")
    dias = datos["fecha_utc"].dt.floor("D").nunique() if n else 0
    metricas = [
        tarjeta("EVENTOS EN LA VENTANA", f"{n:,}".replace(",", " ") if completa else "—", "Consulta delimitada, sin duplicados", "metric-primary"),
        tarjeta("MAGNITUD MÁXIMA", f"{max_mag:.2f}" if pd.notna(max_mag) else "—", "Valor reportado por el catálogo"),
        tarjeta("PROFUNDIDAD MEDIANA", f"{median_depth:.1f} km" if pd.notna(median_depth) else "—", "Eventos con profundidad disponible"),
        tarjeta("DÍAS CON REGISTROS", str(dias) if completa else "—", "Días UTC con al menos un evento"),
    ]
    if not completa:
        estado = "Esta ventana aún no tiene una descarga completa. Ejecuta la carga del recolector."
        clase = "status-banner status-warning"
    elif carga.get("estado") == "error":
        estado = f"Se conserva la última carga válida del {fecha_texto(carga['ultima_consulta_utc'])}. El último intento de descarga falló."
        clase = "status-banner status-warning"
    elif carga.get("estado") == "cargando":
        estado = f"Consulta a USGS en curso. Se muestra la última carga válida del {fecha_texto(carga['ultima_consulta_utc'])}."
        clase = "status-banner status-warning"
    else:
        estado = f"Última consulta a USGS: {fecha_texto(carga['ultima_consulta_utc'])}. Actualizar vista vuelve a leer MySQL."
        clase = "status-banner"
    if completa and carga.get("firma_config") != firma_solicitada:
        estado += " Se muestran los filtros de la carga anterior; falta completar la descarga con la configuración nueva."
        clase = "status-banner status-warning"
    return (*figuras, metricas, contexto, estado, clase)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
