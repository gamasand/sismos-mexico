# Diseño, datos y fuentes

Este documento registra las fuentes primarias y decisiones de la ampliación del dashboard a cuatro ventanas. Referencias consultadas el **21 de octubre de 2026**.

## Procedencia de los eventos

La fuente es el catálogo [ANSS Comprehensive Earthquake Catalog, ComCat](https://earthquake.usgs.gov/data/comcat/), que integra contribuciones de redes sismológicas. El recolector utiliza la [API FDSN de USGS](https://earthquake.usgs.gov/fdsnws/event/1/) y recibe [GeoJSON](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php).

Los valores siguientes se comprobaron mediante la API. Son los parámetros preferidos devueltos en la consulta, que pueden diferir de estimaciones iniciales, nombres periodísticos o coordenadas de centros urbanos.

| Caso del menú | ID USGS | Instante UTC | Epicentro: latitud, longitud | Profundidad | Magnitud y tipo |
|---|---|---|---|---|---|
| Ometepec, Guerrero–Oaxaca | `usp000jghj` | 2012-03-20 18:02:47.440 | 16.493, −98.231 | 20 km | 7.4 `mww` |
| El Mayor–Cucapah, Baja California | `ci14607652` | 2010-04-04 22:40:42.360 | 32.2861667, −115.2953333 | 9.987 km | 7.2 `mw` |
| Puebla–Morelos | `us2000ar20` | 2017-09-19 18:14:38.090 | 18.5499, −98.4887 | 48 km | 7.1 `mww` |

### Fichas y respuestas verificables

- Ometepec: [ficha USGS](https://earthquake.usgs.gov/earthquakes/eventpage/usp000jghj) y [respuesta GeoJSON](https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid=usp000jghj). El lugar preferido es “6 km E of Santiago Llano Grande, Mexico”. El identificador antiguo `usc0008m6h` figura entre sus alias.
- El Mayor–Cucapah: [ficha USGS](https://earthquake.usgs.gov/earthquakes/eventpage/ci14607652) y [respuesta GeoJSON](https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid=ci14607652).
- Puebla–Morelos: [ficha USGS](https://earthquake.usgs.gov/earthquakes/eventpage/us2000ar20) y [respuesta GeoJSON](https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid=us2000ar20). Corresponde al **19 de septiembre de 2017**, no de 2019. Su epicentro no es el centro de la ciudad de Puebla; el lugar preferido es “1 km S of Matzaco, Mexico”.

## Definición de las ventanas

Las reglas se centralizan en [`shared/catalogo.py`](../shared/catalogo.py).

- `live`: 30 días exactos hasta el momento de carga, dentro del rectángulo 14°–33° N y 118°–86° O.
- Históricos: un mes calendario antes y tres meses calendario después del instante de referencia, dentro de un círculo de 250 km por defecto.
- Magnitud mínima 3 para los cuatro casos.
- Todas las horas en UTC, conservando milisegundos en MySQL.
- Intervalo `[inicio, fin)`; las horas inicial y final pueden contener solo una fracción de hora consultada.

USGS admite búsquedas circulares con `latitude`, `longitude` y `maxradiuskm`. El radio es un criterio exploratorio configurable, no la extensión de una falla o un área afectada. Las fechas históricas usan meses calendario; las ventanas anterior y posterior tienen distinta duración.

Se eligió UTC para mantener una referencia común entre regiones y años, sin aplicar offsets locales fijos que podrían ignorar cambios históricos de horario. Las etiquetas explicitan la zona.

## Decisiones visuales y referencias de diseño

La composición y las hojas de estilo son **diseño propio de este proyecto**. No se descargó una plantilla ni se copiaron capturas de un diseño ajeno. Las fuentes siguientes informan la elección de componentes, tipos de gráfica y uso semántico del color.

| Referencia | Aplicación en este proyecto |
|---|---|
| [Dash: Layout](https://dash.plotly.com/layout) | Componentes declarativos, selector, indicadores y paneles; estilos CSS locales. |
| [IBM Carbon: Color palettes](https://www.carbondesignsystem.com/building-blocks/data-visualization/color-palettes/) | Diferenciar cantidades continuas de categorías y usar acentos sobre neutros. Orienta el diseño; nuestra paleta exacta no se atribuye a Carbon. |
| [Plotly: Histograms](https://plotly.com/python/histograms/) | Frecuencias con intervalos explícitos de 0.25 unidades. |
| [Plotly: Heatmaps](https://plotly.com/python/heatmaps/) | Matriz fecha × hora, etiquetas y escala de conteos. |
| [Plotly: Time series and date axes](https://plotly.com/python/time-series/) | Ejes de fecha y presentación temporal de eventos individuales. |
| [Plotly: Scatter plots on maps](https://plotly.com/python/scatter-plots-on-maps/) | Puntos geográficos, atributos visuales y cartografía de contexto. |
| [Plotly: Continuous color scales](https://plotly.com/python/colorscales/) | Mapeo de cantidades a escalas continuas y barras de color. |
| [Nuñez, Anderton y Renslow, 2018](https://doi.org/10.1371/journal.pone.0199239) | Fundamenta Cividis como escala diseñada para uniformidad perceptual y lectura con deficiencias de visión rojo-verde. |

### Composición y paleta

El diseño combina cabecera azul marino, fondo claro, paneles con bordes discretos y separación consistente. Los indicadores preceden a las gráficas para mostrar periodo, cantidad y disponibilidad antes de explorar.

El coral identifica el histograma y los eventos posteriores a la referencia; el púrpura distingue los anteriores. El dorado marca el terremoto de referencia y el verde azulado identifica la serie reciente. El mapa de calor usa una secuencia lavanda. La profundidad emplea Cividis, independiente de los colores categóricos.

No se atribuye uniformidad perceptual a toda la paleta del producto: el fundamento publicado de Cividis corresponde a esa escala. La tipografía usa fuentes del equipo, sin descargas externas.

### Mapa de eventos

- Tamaño: magnitud mediante una escala visual acotada, no energía ni área afectada.
- Color: profundidad hipocentral en km; la barra especifica la escala de la selección.
- Estrella: referencia histórica. Contorno circular: radio de consulta.
- Al pasar el cursor: lugar, magnitud, tipo, fecha UTC y profundidad.

El rango de color se adapta a la ventana. Un mismo color en dos ventanas no garantiza igual profundidad: hay que leer la barra. Los puntos superpuestos pueden ocultarse parcialmente.

### Histograma

Los intervalos de **0.25 unidades de magnitud** mantienen una resolución común. El eje vertical cuenta eventos, no estima una tasa temporal. Se conserva la mezcla de tipos de magnitud y debe considerarse al comparar distribuciones.

### Mapa de calor horario

Las columnas son las 24 horas UTC y las filas son fechas. Cada celda cuenta los eventos que cumplen los filtros durante esa intersección.

Se construye la rejilla completa para distinguir cero eventos de falta de dato. **Cero** significa que una descarga completa no devolvió eventos para esa celda; no demuestra ausencia de sismicidad ni cobertura completa. Las celdas fuera del intervalo no tienen dato; las que intersectan parcialmente sus extremos incluyen solo la fracción consultada. Sin una carga válida se muestra un aviso, no una rejilla de ceros presentada como observación.

La cobertura y los umbrales de detección pueden variar entre redes, regiones y épocas. El patrón horario describe el catálogo descargado, no demuestra periodicidad del proceso sísmico.

La misma cautela aplica a un histórico con pocos eventos: un conteo reducido en Puebla–Morelos, por ejemplo, describe esta extracción de USGS con radio y magnitud mínima determinados; no prueba ausencia de réplicas ni sustituye una consulta a una red local más completa.

### Series temporales

Se muestran **puntos**, sin unir sucesivos sismos con líneas que sugieran trayectoria o interpolación entre eventos. Una línea vertical marca el instante del terremoto principal. La profundidad aumenta hacia abajo para facilitar su lectura física.

“Antes”, “Después” y “Referencia” no equivalen a clasificar precursores o réplicas. Para comparar tasas entre periodos de uno y tres meses hay que normalizar por duración y considerar cobertura, umbral y tipos de magnitud.

## Carga, revisión y metadatos

Solo el recolector consulta la API. Las cinco gráficas se construyen con MySQL. Cambiar el desplegable o pulsar **Actualizar vista** no inicia una descarga.

La carga publica una selección por ventana y registra periodo, fecha de consulta, conteo, estado, último intento y filtros. Las membresías conservan los eventos globales sin mostrarlos todos en cada vista. Una transacción evita que una escritura parcial reemplace la selección anterior.

El *upsert* incorpora revisiones recibidas al descargar de nuevo un identificador. `live` se descarga en cada ejecución general y los históricos válidos se reutilizan salvo cambio de configuración, error o `--forzar-historicos`. No se conserva un historial inmutable de todas las revisiones: `sismos` contiene los parámetros más recientes descargados.

## Certificados de confianza en contenedores

La configuración opcional de certificados locales sigue la [documentación oficial de Docker sobre autoridades certificadoras](https://docs.docker.com/engine/network/ca-certs/): una imagen Linux puede necesitar la raíz del proxy o antivirus que inspecciona HTTPS, aunque Windows ya confíe en ella. Los Dockerfile incorporan las raíces `.crt` locales y actualizan el almacén del sistema. Se conserva la validación TLS de las conexiones.

Estos certificados de entorno se guardan en `certs/` y se excluyen del repositorio; solo se versiona el marcador de carpeta. En otra máquina se configura su propia raíz de confianza cuando corresponda. No se distribuyen claves privadas ni se desactiva la verificación para resolver errores de conexión.

## Referencia bibliográfica de Cividis

Nuñez, J. R., Anderton, C. R., & Renslow, R. S. (2018). *Optimizing colormaps with consideration for color vision deficiency to enable accurate interpretation of scientific data*. PLOS ONE, 13(7), e0199239. [https://doi.org/10.1371/journal.pone.0199239](https://doi.org/10.1371/journal.pone.0199239).
