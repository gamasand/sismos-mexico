"""Transformaciones y figuras puras. Todas las fechas son UTC."""
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

INK = "#24324A"
MUTED = "#738098"
CORAL = "#CA614A"
PURPLE = "#7760AE"
TEAL = "#287F83"
GOLD = "#C49A44"
GRID = "#E9ECF1"
COLUMNS = ["id", "fecha_utc", "lugar", "magnitud", "tipo_magnitud", "longitud", "latitud", "profundidad_km"]


def preparar_datos(filas):
    datos = pd.DataFrame(filas, columns=COLUMNS)
    datos["fecha_utc"] = pd.to_datetime(datos["fecha_utc"], utc=True)
    for c in ["magnitud", "longitud", "latitud", "profundidad_km"]:
        datos[c] = pd.to_numeric(datos[c], errors="coerce")
    return datos.sort_values(["fecha_utc", "id"]).reset_index(drop=True)


def estilo(figura, height=370):
    figura.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Segoe UI, Arial, sans-serif", "size": 12, "color": INK}, height=height,
        margin={"l": 58, "r": 25, "t": 25, "b": 62},
        hoverlabel={"bgcolor": "#17243B", "font_color": "#FFFFFF"},
        legend={"orientation": "h", "y": 1.14, "x": 0, "font_size": 11})
    figura.update_xaxes(gridcolor=GRID, zeroline=False, showline=False, title_font_size=12)
    figura.update_yaxes(gridcolor=GRID, zeroline=False, showline=False, title_font_size=12)
    return figura


def figura_vacia(mensaje):
    fig = estilo(go.Figure())
    fig.add_annotation(text=mensaje, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font={"size": 14, "color": MUTED})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def matriz_horaria(datos, inicio, fin):
    """Horas que intersectan [inicio, fin). Fuera de la consulta: NaN."""
    inicio, fin = pd.to_datetime(inicio, utc=True), pd.to_datetime(fin, utc=True)
    dias = pd.date_range(inicio.floor("D"), fin.floor("D"), freq="D")
    if fin == fin.floor("D"):
        dias = dias[:-1]
    matriz = np.zeros((len(dias), 24), dtype=float)
    for i, dia in enumerate(dias):
        for hora in range(24):
            bucket = dia + pd.Timedelta(hours=hora)
            if bucket >= fin or bucket + pd.Timedelta(hours=1) <= inicio:
                matriz[i, hora] = np.nan
    seleccion = datos[(datos["fecha_utc"] >= inicio) & (datos["fecha_utc"] < fin)]
    if not seleccion.empty:
        grupos = seleccion.groupby([seleccion["fecha_utc"].dt.floor("D"), seleccion["fecha_utc"].dt.hour]).size()
        posiciones = {dia: i for i, dia in enumerate(dias)}
        for (dia, hora), n in grupos.items():
            matriz[posiciones[dia], hora] = n
    return dias, matriz


def _circulo(lat, lon, radio_km):
    lat1, lon1, arco = math.radians(lat), math.radians(lon), radio_km / 6371.0088
    puntos = []
    for grado in range(0, 361, 3):
        az = math.radians(grado)
        lat2 = math.asin(math.sin(lat1) * math.cos(arco) + math.cos(lat1) * math.sin(arco) * math.cos(az))
        lon2 = lon1 + math.atan2(math.sin(az) * math.sin(arco) * math.cos(lat1), math.cos(arco) - math.sin(lat1) * math.sin(lat2))
        puntos.append((math.degrees(lon2), math.degrees(lat2)))
    return list(zip(*puntos))


def mapa_eventos(datos, ventana):
    fig = estilo(go.Figure(), 460)
    validos = datos.dropna(subset=["latitud", "longitud"])
    hover = [[r.id, r.lugar or "Sin descripción", r.magnitud, r.tipo_magnitud or "", r.fecha_utc.strftime("%d/%m/%Y %H:%M UTC"), r.profundidad_km] for r in validos.itertuples()]
    profundidad_max = validos["profundidad_km"].max()
    fig.add_trace(go.Scattergeo(lat=validos["latitud"], lon=validos["longitud"], mode="markers", name="Eventos",
        marker={"size": ((validos["magnitud"].fillna(3) - 3) * 5 + 7).clip(7, 31), "sizemode": "diameter", "opacity": 0.82,
            "color": validos["profundidad_km"], "colorscale": "Cividis", "cmin": 0,
            "cmax": max(float(profundidad_max), 1) if pd.notna(profundidad_max) else 1,
            "colorbar": {"title": {"text": "Profundidad<br>(km)", "font_size": 11}, "thickness": 10, "len": 0.72, "x": 1.01},
            "line": {"color": "white", "width": 0.6}}, customdata=hover,
        hovertemplate="<b>%{customdata[1]}</b><br>M %{customdata[2]:.2f} %{customdata[3]}<br>%{customdata[4]}<br>Profundidad: %{customdata[5]:.1f} km<extra></extra>", showlegend=False))
    anchor = ventana.get("anchor")
    if anchor:
        lons, lats = _circulo(anchor["latitude"], anchor["longitude"], ventana["radius_km"])
        fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode="lines", line={"color": "#A9A0BB", "width": 1, "dash": "dot"}, hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scattergeo(lon=[anchor["longitude"]], lat=[anchor["latitude"]], mode="markers", marker={"symbol": "star", "size": 20, "color": GOLD, "line": {"color": "#17243B", "width": 1}}, name="Referencia USGS", hovertemplate=f"<b>Evento de referencia</b><br>M {anchor['magnitude']:.1f}<extra></extra>", showlegend=False))
        lat_pad = ventana["radius_km"] / 111.2 * 1.3
        lon_pad = lat_pad / math.cos(math.radians(anchor["latitude"]))
        lon_range = [anchor["longitude"] - lon_pad, anchor["longitude"] + lon_pad]
        lat_range = [anchor["latitude"] - lat_pad, anchor["latitude"] + lat_pad]
    else:
        lon_range, lat_range = [-120, -84], [12, 35]
    fig.update_geos(projection_type="mercator", showland=True, landcolor="#F2F0EA", showocean=True, oceancolor="#E6EEF2", showcountries=True, countrycolor="#B8BEC7", showcoastlines=True, coastlinecolor="#A6AFBA", showframe=False, lonaxis_range=lon_range, lataxis_range=lat_range, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(margin={"l": 6, "r": 76, "t": 8, "b": 8}, uirevision=ventana["key"])
    return fig


def histograma(datos):
    valores = datos["magnitud"].dropna()
    if valores.empty:
        return figura_vacia("No hay magnitudes disponibles.")
    fig = estilo(go.Figure(), 460)
    fig.add_trace(go.Histogram(x=valores, xbins={"start": math.floor(valores.min() * 4) / 4, "end": math.ceil(valores.max() * 4) / 4 + 0.25, "size": 0.25},
        marker={"color": CORAL, "line": {"color": "#F8F7F4", "width": 1}}, hovertemplate="Magnitud: %{x}<br>Eventos: %{y}<extra></extra>"))
    fig.update_layout(bargap=0.12)
    fig.update_xaxes(title="Magnitud reportada")
    fig.update_yaxes(title="Eventos", rangemode="tozero", dtick=1 if len(valores) < 30 else None)
    return fig


def heatmap(datos, inicio, fin):
    dias, matriz = matriz_horaria(datos, inicio, fin)
    maximo = max(1, float(np.nanmax(matriz))) if matriz.size else 1
    inicio_utc, fin_utc = pd.to_datetime(inicio, utc=True), pd.to_datetime(fin, utc=True)
    cobertura = [["Hora parcial en el límite del intervalo" if
                  dia + pd.Timedelta(hours=h) < inicio_utc or dia + pd.Timedelta(hours=h + 1) > fin_utc
                  else "Hora completa" for h in range(24)] for dia in dias]
    escala = [[0, "#F4F2F8"], [0.18, "#DAD2EB"], [0.45, "#AD96CC"], [0.72, "#7955A3"], [1, "#392651"]]
    fig = estilo(go.Figure(go.Heatmap(x=list(range(24)), y=[d.strftime("%Y-%m-%d") for d in dias], z=matriz,
        zmin=0, zmax=maximo, colorscale=escala, xgap=2, ygap=0.4,
        colorbar={"title": "Eventos", "thickness": 10, "len": 0.85, "tickformat": ".0f", "dtick": 1 if maximo <= 6 else None}, hoverongaps=False, customdata=cobertura,
        hovertemplate="%{y}<br>Hora: %{x}:00 UTC<br>Eventos: %{z:.0f}<br>%{customdata}<extra></extra>")), 420)
    fig.update_xaxes(title="Hora del día (UTC)", tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{h:02d}" for h in range(0, 24, 3)], tickangle=0, showgrid=False)
    fig.update_yaxes(title="Fecha UTC", type="date", autorange="reversed", tickformat="%d %b", nticks=9, showgrid=False)
    return fig


def serie(datos, ventana, inicio, fin, columna):
    fig = estilo(go.Figure(), 370)
    anchor = ventana.get("anchor")
    grupos = [("Eventos", TEAL, datos)]
    if anchor:
        momento = pd.Timestamp(anchor["time"])
        principal = datos["id"] == anchor["id"]
        grupos = [("Antes", PURPLE, datos[~principal & (datos["fecha_utc"] < momento)]),
                  ("Después", CORAL, datos[~principal & (datos["fecha_utc"] >= momento)]),
                  ("Referencia", GOLD, datos[principal])]
    for etiqueta, color, grupo in grupos:
        grupo = grupo.dropna(subset=[columna])
        if grupo.empty:
            continue
        fig.add_trace(go.Scatter(x=grupo["fecha_utc"], y=grupo[columna], mode="markers", name=etiqueta,
            marker={"size": 7 if etiqueta != "Referencia" else 13, "color": color, "opacity": 0.75, "line": {"width": 0.5, "color": "white"}, "symbol": "diamond" if etiqueta == "Referencia" else "circle"},
            customdata=[[r.lugar or "Sin descripción", r.tipo_magnitud or ""] for r in grupo.itertuples()],
            hovertemplate="<b>%{customdata[0]}</b><br>%{x|%d/%m/%Y %H:%M} UTC<br>Valor: %{y:.2f}<extra>%{fullData.name}</extra>"))
    if anchor:
        instante = pd.Timestamp(anchor["time"]).isoformat()
        fig.add_shape(type="line", x0=instante, x1=instante, y0=0, y1=1, yref="paper", line={"color": GOLD, "width": 1.5, "dash": "dot"})
    fig.update_xaxes(title="Fecha UTC", range=[inicio.isoformat(), fin.isoformat()], type="date", tickformat="%d %b")
    fig.update_yaxes(title="Magnitud reportada" if columna == "magnitud" else "Profundidad (km)")
    if columna == "profundidad_km":
        fig.update_yaxes(autorange="reversed")
    fig.update_layout(showlegend=bool(anchor))
    return fig


def construir_figuras(datos, ventana, inicio, fin, disponible=True):
    if not disponible:
        return tuple(figura_vacia("Sin descarga completa para esta ventana.") for _ in range(5))
    datos = datos[(datos["fecha_utc"] >= inicio) & (datos["fecha_utc"] < fin)]
    return (mapa_eventos(datos, ventana), histograma(datos), heatmap(datos, inicio, fin),
            serie(datos, ventana, inicio, fin, "magnitud"), serie(datos, ventana, inicio, fin, "profundidad_km"))
