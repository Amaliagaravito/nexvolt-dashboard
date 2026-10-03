import os
import json
import base64
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ====================================================================
# 1. CARGA Y UNIÓN DE LAS BASES
# ====================================================================
print("Cargando datos...")
historico = pd.read_excel('histórico_filtrado_proc.xlsx')
equipos = pd.read_excel('equipos_proc.xlsx')

datos = pd.merge(historico, equipos, on='Equipo', how='left')

print('Registros:', len(datos))
print('Avisos:', datos['Aviso'].nunique())
print('Equipos:', datos['Equipo'].nunique())

# ====================================================================
# 2. PREPARACIÓN DEL MAPA DEPARTAMENTAL
# ====================================================================
with open('departamentos_colombia.geojson', 'r', encoding='utf-8') as archivo:
    geojson_colombia = json.load(archivo)

datos['Departamento_mapa'] = datos['Departamento'].str.upper().str.strip()

departamentos = pd.DataFrame([
    elemento['properties']['dpto_cnmbr']
    for elemento in geojson_colombia['features']
], columns=['Departamento_mapa'])

avisos_departamento = (
    datos.dropna(subset=['Departamento_mapa'])
    .groupby('Departamento_mapa')['Aviso']
    .count()
    .reset_index(name='Total avisos')
)

mapa_departamentos = departamentos.merge(
    avisos_departamento, on='Departamento_mapa', how='left'
)

# ====================================================================
# 3. PREPARACIÓN DE LA CAPA MUNICIPAL
# ====================================================================
print("Cargando capa municipal...")
ruta_municipios = 'capa_municipios/Limite_Municipal_2016.shp'
municipios = gpd.read_file(ruta_municipios)

# Estandarización de nombres
datos['Municipio_mapa'] = datos['Municipio'].str.upper().str.strip()

equivalencias_municipios = {
    'TIBANA': 'TIBANÁ', 'UMBITA': 'ÚMBITA', 'SUPIA': 'SUPÍA',
    'VILLAMARIA': 'VILLAMARÍA', 'INZA': 'INZÁ', 'EL PEÑON': 'EL PEÑÓN',
    'IMUES': 'IMUÉS', 'ARMERO': 'ARMERO (GUAYABAL)',
    'SAN SEBASTIÁN DE MARIQUITA': 'MARIQUITA', 'PATÍA': 'PATÍA (EL BORDO)',
    'SAN JUAN DE RIO SECO': 'SAN JUAN DE RIOSECO'
}

datos['Municipio_mapa'] = datos['Municipio_mapa'].replace(equivalencias_municipios)

municipios['Municipio_mapa'] = (
    municipios['NOM_MUNICI']
    .str.upper().str.strip().str.replace(r'\s+', ' ', regex=True)
)
municipios['Departamento_mapa'] = municipios['NOM_DEPART'].str.upper().str.strip()

# Listas para los filtros geográficos
lista_departamentos = sorted(datos['Departamento_mapa'].dropna().unique())
lista_municipios = sorted(datos['Municipio_mapa'].dropna().unique())

# Reproyección de la capa municipal para Plotly
municipios_4326 = municipios.to_crs(epsg=4326)

# GeoJSON municipal separado por departamento
geojson_municipios_departamento = {}
for departamento in municipios_4326['Departamento_mapa'].dropna().unique():
    municipios_depto = municipios_4326[municipios_4326['Departamento_mapa'] == departamento]
    geojson_municipios_departamento[departamento] = json.loads(municipios_depto.to_json())

# ====================================================================
# 4. PALETA DE COLORES E IMAGEN
# ====================================================================
AZUL_FONDO = '#061525'
AZUL_TARJETA = '#0B2035'
AZUL_BORDE = '#124A6B'
CIAN = '#19BDF2'
BLANCO = '#FFFFFF'
GRIS_TEXTO = '#A9BDD0'

total_avisos = datos['Aviso'].nunique()
total_equipos = datos['Equipo'].nunique()
total_departamentos = datos['Departamento'].nunique()
total_tipos = datos['Tipo de aviso'].nunique()

if 'Año' in datos.columns:
    año_min = int(datos['Año'].min())
    año_max = int(datos['Año'].max())
else:
    año_min, año_max = 2008, 2023 # Valores por defecto si la columna no existe

ruta_imagen = 'assets/hero_nexvolt.png'
with open(ruta_imagen, 'rb') as archivo:
    imagen_codificada = base64.b64encode(archivo.read()).decode()
hero_imagen = 'data:image/png;base64,' + imagen_codificada


# ====================================================================
# 5. FIGURAS BASE INICIALES
# ====================================================================
resumen_tipos = datos.groupby('Tipo de aviso')['Días abierto'].agg(['count', 'mean', 'median', 'std']).reset_index()
fig_error = px.scatter(
    resumen_tipos, x='Tipo de aviso', y='mean', error_y='std',
    title='Tiempo promedio de los avisos según tipo',
    labels={'Tipo de aviso': 'Tipo de aviso', 'mean': 'Promedio de días abierto', 'std': 'Desviación estándar'}
)
fig_error.update_traces(marker={'size': 12, 'color': CIAN})
fig_error.update_layout(paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA, font_color=BLANCO, title_font_size=18, margin=dict(l=60, r=30, t=70, b=60))
fig_error.update_xaxes(gridcolor=AZUL_BORDE)
fig_error.update_yaxes(rangemode='tozero', gridcolor=AZUL_BORDE)

mapa_sin_datos = mapa_departamentos[mapa_departamentos['Total avisos'].isna()]
mapa_con_datos = mapa_departamentos[mapa_departamentos['Total avisos'].notna()]

fig_mapa_nexvolt = px.choropleth_map(
    mapa_con_datos, geojson=geojson_colombia, locations='Departamento_mapa',
    featureidkey='properties.dpto_cnmbr', color='Total avisos',
    color_continuous_scale=[[0, '#B8E3F2'], [0.5, '#258AC4'], [1, '#06466D']],
    map_style='carto-darkmatter', center={'lat': 4.5, 'lon': -74}, zoom=4.2, opacity=0.9,
    hover_name='Departamento_mapa', hover_data={'Departamento_mapa': False, 'Total avisos': True}
)

fig_sin_datos = px.choropleth_map(
    mapa_sin_datos, geojson=geojson_colombia, locations='Departamento_mapa',
    featureidkey='properties.dpto_cnmbr', color_discrete_sequence=['#4B5563'],
    map_style='carto-darkmatter', center={'lat': 4.5, 'lon': -74}, zoom=4.2
)
for traza in fig_sin_datos.data:
    fig_mapa_nexvolt.add_trace(traza)

fig_mapa_nexvolt.update_layout(
    title='Distribución de avisos por departamento', paper_bgcolor=AZUL_TARJETA,
    plot_bgcolor=AZUL_TARJETA, font_color=BLANCO, margin=dict(l=0, r=0, t=50, b=0),
    coloraxis_colorbar=dict(title='Avisos')
)

avisos_tipo_inicial = datos.dropna(subset=['Tipo de aviso']).groupby('Tipo de aviso')['Aviso'].count().reset_index(name='Total avisos').sort_values('Total avisos')
fig_tipo_territorio = px.bar(avisos_tipo_inicial, x='Total avisos', y='Tipo de aviso', orientation='h', text='Total avisos')
fig_tipo_territorio.update_traces(marker_color=CIAN, textposition='outside')
fig_tipo_territorio.update_layout(
    title={'text': 'Avisos por tipo', 'font': {'size': 16, 'color': BLANCO}},
    paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA, font_color=BLANCO,
    margin=dict(l=10, r=20, t=50, b=30), xaxis_title='Avisos', yaxis_title='', showlegend=False
)
fig_tipo_territorio.update_xaxes(gridcolor=AZUL_BORDE)
fig_tipo_territorio.update_yaxes(gridcolor=AZUL_TARJETA)

# ====================================================================
# 6. INICIALIZACIÓN DE LA APLICACIÓN Y SERVIDOR (PARA RENDER)
# ====================================================================
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# ====================================================================
# 7. DISEÑO DE LA APLICACIÓN (LAYOUTS Y MENÚS)
# ====================================================================
menu_lateral = html.Div(className='menu-lateral', children=[
    html.Div([
        html.H1(['NEX', html.Span('VOLT', style={'color': CIAN})], style={'color': BLANCO, 'marginBottom': '5px'}),
        html.P('Energía · Infraestructura · Eficiencia', style={'color': GRIS_TEXTO, 'fontSize': '12px', 'marginTop': '0px'})
    ]),
    html.Div([
        dcc.Link('⌂  Inicio', href='/', style={'display': 'block', 'padding': '14px', 'marginTop': '10px', 'marginBottom': '5px', 'color': BLANCO, 'textDecoration': 'none', 'borderRadius': '8px'}),
        dcc.Link('▣  Mapa coroplético', href='/territorial', style={'display': 'block', 'padding': '14px', 'marginBottom': '5px', 'color': GRIS_TEXTO, 'textDecoration': 'none', 'borderRadius': '8px'}),
        dcc.Link('▥  Gráfico de errores', href='/tiempos', style={'display': 'block', 'padding': '14px', 'marginBottom': '5px', 'color': GRIS_TEXTO, 'textDecoration': 'none', 'borderRadius': '8px'})
    ]),
    html.Div(className='info-desarrolladores', children=[
        html.P('DESARROLLADO POR', style={'color': CIAN, 'fontSize': '9px', 'letterSpacing': '1.5px', 'margin': '0px 0px 6px 0px'}),
        
        # Contenedor Amalia
        html.Div([
            html.Img(src='/assets/foto_amalia.png', style={'width': '24px', 'height': '24px', 'borderRadius': '50%', 'objectFit': 'cover', 'marginRight': '8px'}),
            html.P('Amalia Garavito Guerrero', style={'color': BLANCO, 'fontSize': '11px', 'margin': '0px'})
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'}),

        # Contenedor Francy
        html.Div([
            html.Img(src='/assets/foto_francy.png', style={'width': '24px', 'height': '24px', 'borderRadius': '50%', 'objectFit': 'cover', 'marginRight': '8px'}),
            html.P('Francy Julieth Buitrago', style={'color': BLANCO, 'fontSize': '11px', 'margin': '0px'})
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
        
        html.P('Energía confiable para un futuro sostenible.', style={'color': GRIS_TEXTO, 'fontSize': '10px', 'lineHeight': '1.3', 'margin': '0px'})
    ], style={'position': 'absolute', 'bottom': '25px', 'width': '190px'})
])

pagina_inicio = html.Div([
    html.Div(className='caja-flexible', style={'alignItems': 'center', 'paddingTop': '12px', 'paddingBottom': '14px'}, children=[
        html.Div([
            html.P('INFRAESTRUCTURA ELÉCTRICA PARA UN PAÍS QUE AVANZA', style={'color': CIAN, 'fontSize': '11px', 'letterSpacing': '2px', 'margin': '0px 0px 8px 0px'}),
            html.H1(['Energía que conecta ', html.Span('territorios', style={'color': CIAN})], style={'color': BLANCO, 'fontSize': '32px', 'margin': '0px 0px 10px 0px'}),
            html.P(
                'NEXVOLT es un tablero interactivo para el análisis de '
                'avisos asociados a equipos e infraestructura eléctrica. '
                'Integra información operativa y territorial para '
                'identificar su distribución espacial y analizar los '
                'tiempos de atención registrados.', 
                style={'color': GRIS_TEXTO, 'fontSize': '14px', 'lineHeight': '1.45', 'margin': '0px 0px 8px 0px', 'maxWidth': '610px'}
            ),
            html.P(
                'Mediante filtros e interacciones como hover y click, '
                'el usuario puede explorar los datos por ubicación, '
                'periodo, tipo y estado del aviso, y profundizar en '
                'los patrones identificados mediante visualizaciones '
                'relacionadas.',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px',
                    'lineHeight': '1.4',
                    'maxWidth': '610px',
                    'margin': '0px'
                }
            )
        ], style={'flex': '1 1 300px', 'paddingRight': '15px'}),
        html.Div([
            html.Img(src=hero_imagen, style={'width': '100%', 'height': '220px', 'objectFit': 'cover', 'borderRadius': '10px'})
        ], style={'flex': '1 1 300px'})
    ]),
    
    html.Div(className='caja-flexible', style={'marginBottom': '16px'}, children=[
        html.Div([html.H2(f'{total_avisos:,}'.replace(',', '.'), style={'color': CIAN, 'fontSize': '23px', 'margin': '0'}), html.P('Avisos registrados', style={'color': GRIS_TEXTO, 'fontSize': '12px', 'margin': '0'})], style={'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '8px', 'padding': '11px 15px', 'flex': '1 1 150px'}),
        html.Div([html.H2(f'{total_equipos:,}'.replace(',', '.'), style={'color': CIAN, 'fontSize': '23px', 'margin': '0'}), html.P('Equipos monitoreados', style={'color': GRIS_TEXTO, 'fontSize': '12px', 'margin': '0'})], style={'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '8px', 'padding': '11px 15px', 'flex': '1 1 150px'}),
        html.Div([html.H2(str(total_departamentos), style={'color': CIAN, 'fontSize': '23px', 'margin': '0'}), html.P('Departamentos', style={'color': GRIS_TEXTO, 'fontSize': '12px', 'margin': '0'})], style={'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '8px', 'padding': '11px 15px', 'flex': '1 1 150px'}),
        html.Div([html.H2(f'{año_min}–{año_max}', style={'color': CIAN, 'fontSize': '23px', 'margin': '0'}), html.P('Periodo analizado', style={'color': GRIS_TEXTO, 'fontSize': '12px', 'margin': '0'})], style={'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '8px', 'padding': '11px 15px', 'flex': '1 1 150px'})
    ]),

    html.Div(className='caja-flexible', children=[
        html.Div([
            html.P('MAPA COROPLÉTICO', style={'color': CIAN, 'fontSize': '10px', 'letterSpacing': '1.5px', 'margin': '0px 0px 5px 0px'}),
            html.H3('¿Dónde se concentran los avisos?', style={'color': BLANCO, 'fontSize': '19px', 'margin': '0px 0px 7px 0px'}),
            dcc.Link('Explorar territorio →', href='/territorial', style={'color': CIAN, 'fontSize': '13px', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ], style={'flex': '1 1 300px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '9px', 'padding': '16px'}),
        html.Div([
            html.P('GRÁFICO DE ERRORES', style={'color': CIAN, 'fontSize': '10px', 'letterSpacing': '1.5px', 'margin': '0px 0px 5px 0px'}),
            html.H3('¿Cómo varían los tiempos de atención?', style={'color': BLANCO, 'fontSize': '19px', 'margin': '0px 0px 7px 0px'}),
            dcc.Link('Analizar tiempos →', href='/tiempos', style={'color': CIAN, 'fontSize': '13px', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ], style={'flex': '1 1 300px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '9px', 'padding': '16px'})
    ])
])

pagina_territorial = html.Div([
    html.Div(className='caja-flexible', style={'alignItems': 'center', 'marginBottom': '10px'}, children=[
        html.Div([
            html.P('MONITOREO OPERACIONAL', style={'color': CIAN, 'fontSize': '10px', 'letterSpacing': '2px', 'margin': '0'}),
            html.H1('Mapa coroplético', style={'color': BLANCO, 'fontSize': '27px', 'margin': '0'}),
        ], style={'flex': '2 1 300px'}),
        html.Div([
            html.P('TOTAL DE AVISOS', style={'color': CIAN, 'fontSize': '9px', 'letterSpacing': '1.5px', 'margin': '0px'}),
            html.H2('3.118 avisos', id='total-avisos-mapa', style={'color': BLANCO, 'fontSize': '22px', 'margin': '2px 0px'})
        ], style={'flex': '1 1 150px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '9px', 'padding': '7px 12px'})
    ]),

    html.Div(className='caja-flexible', style={'marginBottom': '10px'}, children=[
        html.Div([html.Label('Nivel', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-nivel', options=[{'label': 'Departamento', 'value': 'Departamento'}, {'label': 'Municipio', 'value': 'Municipio'}], value='Departamento', clearable=False)], style={'flex': '1 1 150px'}),
        html.Div([html.Label('Departamento', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-departamento', options=[{'label': dep.title(), 'value': dep} for dep in lista_departamentos], placeholder='Todos', clearable=True)], style={'flex': '1 1 150px'}),
        html.Div([html.Label('Municipio', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-municipio', options=[{'label': mun.title(), 'value': mun} for mun in lista_municipios], placeholder='Todos', clearable=True)], style={'flex': '1 1 150px'}),
        html.Div([html.Label('Año', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-año', options=[{'label': 'Todos', 'value': None}] + [{'label': str(año), 'value': año} for año in sorted(datos['Año'].dropna().unique())] if 'Año' in datos.columns else [], value=None)], style={'flex': '1 1 100px'}),
        html.Div([html.Label('Tipo', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-tipo', options=[{'label': 'Todos', 'value': None}] + [{'label': tipo, 'value': tipo} for tipo in sorted(datos['Tipo de aviso'].dropna().unique())], value=None)], style={'flex': '1 1 150px'}),
        html.Div([html.Label('Estado', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-estado', options=[{'label': 'Todos', 'value': None}] + [{'label': est, 'value': est} for est in sorted(datos['Estado aviso'].dropna().unique())] if 'Estado aviso' in datos.columns else [], value=None)], style={'flex': '1 1 150px'})
    ]),

    html.Div(className='caja-flexible', children=[
        html.Div(className='grafico-principal', style={'height': '430px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '10px', 'padding': '4px', 'overflow': 'hidden'}, children=[
            dcc.Graph(id='mapa-avisos', figure=fig_mapa_nexvolt, config={'displayModeBar': False, 'responsive': True}, style={'height': '100%', 'width': '100%'})
        ]),
        html.Div(className='grafico-secundario', style={'height': '430px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '10px', 'padding': '10px', 'overflow': 'hidden'}, children=[
            html.P('DETALLE DEL TERRITORIO', style={'color': CIAN, 'fontSize': '9px', 'letterSpacing': '1.5px', 'margin': '0 0 5px 0'}),
            dcc.Graph(id='grafico-tipo-territorio', figure=fig_tipo_territorio, config={'displayModeBar': False, 'responsive': True}, style={'height': '90%', 'width': '100%'})
        ])
    ])
])

pagina_tiempos = html.Div([
    html.Div(className='caja-flexible', style={'alignItems': 'center', 'marginBottom': '10px'}, children=[
        html.Div([
            html.P('GESTIÓN OPERACIONAL', style={'color': CIAN, 'fontSize': '10px', 'letterSpacing': '2px', 'margin': '0'}),
            html.H1('Gráfico de errores', style={'color': BLANCO, 'fontSize': '27px', 'margin': '0'}),
        ], style={'flex': '2 1 300px'}),
        html.Div([
            html.P('HALLAZGO', style={'color': CIAN, 'fontSize': '9px', 'letterSpacing': '1.5px', 'margin': '0px'}),
            html.P('Los avisos de Construcciones presentan el mayor tiempo promedio.', id='hallazgo-tiempos', style={'color': BLANCO, 'fontSize': '11px', 'margin': '5px 0 0 0'})
        ], style={'flex': '1 1 200px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '9px', 'padding': '8px 12px'})
    ]),

    html.Div(className='caja-flexible', style={'marginBottom': '10px'}, children=[
        html.Div([html.Label('Año', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-año-tiempos', options=[{'label': 'Todos', 'value': None}] + [{'label': str(año), 'value': año} for año in sorted(datos['Año'].dropna().unique())] if 'Año' in datos.columns else [], value=None)], style={'flex': '1 1 150px'}),
        html.Div([html.Label('Departamento', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-departamento-tiempos', options=[{'label': 'Todos', 'value': None}] + [{'label': dep.title(), 'value': dep} for dep in lista_departamentos], value=None)], style={'flex': '1 1 150px'}),
        html.Div([html.Label('Estado', style={'color': GRIS_TEXTO, 'fontSize': '11px'}), dcc.Dropdown(id='filtro-estado-tiempos', options=[{'label': 'Todos', 'value': None}] + [{'label': est, 'value': est} for est in sorted(datos['Estado aviso'].dropna().unique())] if 'Estado aviso' in datos.columns else [], value=None)], style={'flex': '1 1 150px'})
    ]),

    html.Div(className='caja-flexible', children=[
        html.Div(className='grafico-principal', style={'height': '430px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '10px', 'padding': '4px', 'overflow': 'hidden'}, children=[
            dcc.Graph(id='grafico-error', figure=fig_error, config={'displayModeBar': False, 'responsive': True}, style={'height': '100%', 'width': '100%'})
        ]),
        html.Div(className='grafico-secundario', style={'height': '430px', 'backgroundColor': AZUL_TARJETA, 'border': f'1px solid {AZUL_BORDE}', 'borderRadius': '10px', 'padding': '10px', 'overflow': 'hidden'}, children=[
            html.P('DETALLE DEL TIPO DE AVISO', style={'color': CIAN, 'fontSize': '10px', 'letterSpacing': '1.5px', 'margin': '0 0 5px 0'}),
            html.Div('Haz clic sobre un punto del gráfico para consultar el detalle.', id='detalle-aviso', style={'color': GRIS_TEXTO, 'fontSize': '11px', 'minHeight': '50px'}),
            dcc.Graph(id='grafico-evolucion-tiempos', config={'displayModeBar': False, 'responsive': True}, style={'height': '300px', 'width': '100%'})
        ])
    ])
])

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    menu_lateral,
    html.Div(className='contenido-principal', children=[
        html.Div(pagina_inicio, id='contenedor-inicio'),
        html.Div(pagina_territorial, id='contenedor-territorial', style={'display': 'none'}),
        html.Div(pagina_tiempos, id='contenedor-tiempos', style={'display': 'none'})
    ])
], style={'fontFamily': 'Arial, sans-serif', 'margin': '0', 'overflowX': 'hidden'})

# ====================================================================
# 8. CALLBACKS DE NAVEGACIÓN Y FUNCIONALIDAD
# ====================================================================
@app.callback(
    Output('contenedor-inicio', 'style'),
    Output('contenedor-territorial', 'style'),
    Output('contenedor-tiempos', 'style'),
    Input('url', 'pathname')
)
def mostrar_pagina(pathname):
    if pathname == '/territorial':
        return ({'display': 'none'}, {'display': 'block'}, {'display': 'none'})
    if pathname == '/tiempos':
        return ({'display': 'none'}, {'display': 'none'}, {'display': 'block'})
    return ({'display': 'block'}, {'display': 'none'}, {'display': 'none'})

@app.callback(
    Output('filtro-municipio', 'options'),
    Output('filtro-municipio', 'value'),
    Input('filtro-departamento', 'value')
)
def actualizar_municipios(departamento):
    if departamento is None:
        municipios_disponibles = datos['Municipio_mapa'].dropna().unique()
    else:
        municipios_disponibles = datos[datos['Departamento_mapa'] == departamento]['Municipio_mapa'].dropna().unique()
    municipios_disponibles = sorted(municipios_disponibles)
    opciones = [{'label': municipio.title(), 'value': municipio} for municipio in municipios_disponibles]
    return opciones, None

@app.callback(
    Output('mapa-avisos', 'figure'),
    Output('total-avisos-mapa', 'children'),
    Input('filtro-nivel', 'value'),
    Input('filtro-departamento', 'value'),
    Input('filtro-municipio', 'value'),
    Input('filtro-año', 'value'),
    Input('filtro-tipo', 'value'),
    Input('filtro-estado', 'value')
)
def actualizar_mapa(nivel, departamento, municipio, año, tipo, estado):
    datos_filtrados = datos.copy()
    if departamento is not None:
        datos_filtrados = datos_filtrados[datos_filtrados['Departamento_mapa'] == departamento]
    if nivel == 'Municipio' and municipio is not None:
        datos_filtrados = datos_filtrados[datos_filtrados['Municipio_mapa'] == municipio]
    if año is not None and 'Año' in datos_filtrados.columns:
        datos_filtrados = datos_filtrados[datos_filtrados['Año'] == año]
    if tipo is not None:
        datos_filtrados = datos_filtrados[datos_filtrados['Tipo de aviso'] == tipo]
    if estado is not None and 'Estado aviso' in datos_filtrados.columns:
        datos_filtrados = datos_filtrados[datos_filtrados['Estado aviso'] == estado]

    if nivel == 'Departamento':
        avisos_filtrados = datos_filtrados.dropna(subset=['Departamento_mapa']).groupby('Departamento_mapa')['Aviso'].count().reset_index(name='Total avisos')
        if departamento is not None:
            avisos_filtrados = avisos_filtrados[avisos_filtrados['Departamento_mapa'] == departamento]
        departamentos_seleccionados = set(avisos_filtrados['Departamento_mapa'])
        geojson_departamentos_filtrado = {'type': 'FeatureCollection', 'features': [elemento for elemento in geojson_colombia['features'] if elemento['properties']['dpto_cnmbr'] in departamentos_seleccionados]}
        
        figura = px.choropleth_map(
            avisos_filtrados, geojson=geojson_departamentos_filtrado, locations='Departamento_mapa',
            featureidkey='properties.dpto_cnmbr', color='Total avisos',
            color_continuous_scale=[[0, '#B8E3F2'], [0.5, '#258AC4'], [1, '#06466D']],
            map_style='carto-darkmatter', center={'lat': 4.5, 'lon': -74}, zoom=4.2, opacity=0.9,
            hover_name='Departamento_mapa', hover_data={'Departamento_mapa': False, 'Total avisos': True}
        )
        titulo = 'Distribución de avisos por departamento'
        if departamento is not None:
            departamento_geo = municipios_4326[municipios_4326['Departamento_mapa'] == departamento]
            if len(departamento_geo) > 0:
                centro = departamento_geo.geometry.union_all().centroid
                figura.update_layout(map_center={'lat': centro.y, 'lon': centro.x}, map_zoom=7)
    else:
        if departamento is None:
            figura = go.Figure()
            figura.add_annotation(text='Selecciona un departamento para visualizar sus municipios', x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False, font=dict(size=20, color=BLANCO))
            figura.update_xaxes(visible=False)
            figura.update_yaxes(visible=False)
            titulo = ''
        else:
            avisos_filtrados = datos_filtrados.dropna(subset=['Departamento_mapa', 'Municipio_mapa']).groupby(['Departamento_mapa', 'Municipio_mapa'])['Aviso'].count().reset_index(name='Total avisos')
            municipios_seleccionados = municipios_4326[municipios_4326['Departamento_mapa'] == departamento]
            geojson_seleccionado = geojson_municipios_departamento[departamento]
            if municipio is not None:
                municipios_seleccionados = municipios_seleccionados[municipios_seleccionados['Municipio_mapa'] == municipio]
            
            municipios_mapa = municipios_seleccionados[['Departamento_mapa', 'Municipio_mapa', 'COD_MUN']].copy()
            mapa_filtrado = municipios_mapa.merge(avisos_filtrados, on=['Departamento_mapa', 'Municipio_mapa'], how='left')
            mapa_con_datos = mapa_filtrado[mapa_filtrado['Total avisos'].notna()]
            mapa_sin_datos = mapa_filtrado[mapa_filtrado['Total avisos'].isna()]

            figura = px.choropleth_map(
                mapa_con_datos, geojson=geojson_seleccionado, locations='COD_MUN',
                featureidkey='properties.COD_MUN', color='Total avisos',
                color_continuous_scale=[[0, '#B8E3F2'], [0.5, '#258AC4'], [1, '#06466D']],
                map_style='carto-darkmatter', center={'lat': 4.5, 'lon': -74}, zoom=4.2, opacity=0.9,
                hover_name='Municipio_mapa', hover_data={'Municipio_mapa': False, 'Departamento_mapa': True, 'Total avisos': True, 'COD_MUN': False}
            )
            figura_sin_datos = px.choropleth_map(
                mapa_sin_datos, geojson=geojson_seleccionado, locations='COD_MUN',
                featureidkey='properties.COD_MUN', color_discrete_sequence=['#4B5563'],
                map_style='carto-darkmatter', center={'lat': 4.5, 'lon': -74}, zoom=4.2
            )
            for traza in figura_sin_datos.data:
                figura.add_trace(traza)
            titulo = 'Distribución de avisos por municipio'
            
            if municipio is not None and len(municipios_seleccionados) > 0:
                centro = municipios_seleccionados.geometry.union_all().centroid
                figura.update_layout(map_center={'lat': centro.y, 'lon': centro.x}, map_zoom=10)
            elif len(municipios_seleccionados) > 0:
                centro = municipios_seleccionados.geometry.union_all().centroid
                figura.update_layout(map_center={'lat': centro.y, 'lon': centro.x}, map_zoom=7)

    figura.update_layout(
        title=titulo, paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA,
        font_color=BLANCO, margin=dict(l=0, r=0, t=50, b=0), coloraxis_colorbar=dict(title='Avisos')
    )
    texto_total = f'{len(datos_filtrados):,}'.replace(',', '.') + ' avisos'
    return figura, texto_total

@app.callback(
    Output('grafico-tipo-territorio', 'figure'),
    Input('mapa-avisos', 'clickData'),
    Input('filtro-nivel', 'value'),
    Input('filtro-departamento', 'value'),
    Input('filtro-municipio', 'value'),
    Input('filtro-año', 'value'),
    Input('filtro-tipo', 'value'),
    Input('filtro-estado', 'value')
)
def actualizar_grafico_territorio(clickData, nivel, departamento, municipio, año, tipo, estado):
    datos_grafico = datos.copy()
    if departamento is not None:
        datos_grafico = datos_grafico[datos_grafico['Departamento_mapa'] == departamento]
    if nivel == 'Municipio' and municipio is not None:
        datos_grafico = datos_grafico[datos_grafico['Municipio_mapa'] == municipio]
    if año is not None and 'Año' in datos_grafico.columns:
        datos_grafico = datos_grafico[datos_grafico['Año'] == año]
    if tipo is not None:
        datos_grafico = datos_grafico[datos_grafico['Tipo de aviso'] == tipo]
    if estado is not None and 'Estado aviso' in datos_grafico.columns:
        datos_grafico = datos_grafico[datos_grafico['Estado aviso'] == estado]

    territorio = 'Todos los territorios'
    if clickData is not None:
        territorio_click = clickData['points'][0]['location']
        if nivel == 'Departamento':
            datos_grafico = datos_grafico[datos_grafico['Departamento_mapa'] == territorio_click]
            territorio = territorio_click.title()
        else:
            municipio_click = municipios_4326[municipios_4326['COD_MUN'].astype(str) == str(territorio_click)]
            if len(municipio_click) > 0:
                nombre_municipio = municipio_click.iloc[0]['Municipio_mapa']
                datos_grafico = datos_grafico[datos_grafico['Municipio_mapa'] == nombre_municipio]
                territorio = nombre_municipio.title()
    else:
        if nivel == 'Municipio' and municipio is not None:
            territorio = municipio.title()
        elif departamento is not None:
            territorio = departamento.title()

    resumen = datos_grafico.dropna(subset=['Tipo de aviso']).groupby('Tipo de aviso')['Aviso'].count().reset_index(name='Total avisos').sort_values('Total avisos')
    figura = px.bar(resumen, x='Total avisos', y='Tipo de aviso', orientation='h', text='Total avisos')
    figura.update_traces(marker_color=CIAN, textposition='outside', hovertemplate='<b>%{y}</b><br>Avisos: %{x}<extra></extra>')
    figura.update_layout(
        title={'text': f'Avisos por tipo · {territorio}', 'font': {'size': 15, 'color': BLANCO}},
        paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA, font_color=BLANCO,
        margin=dict(l=10, r=25, t=55, b=35), xaxis_title='Avisos', yaxis_title='', showlegend=False, transition_duration=400
    )
    figura.update_xaxes(gridcolor=AZUL_BORDE)
    figura.update_yaxes(gridcolor=AZUL_TARJETA)
    return figura

@app.callback(
    Output('grafico-error', 'figure'),
    Output('hallazgo-tiempos', 'children'),
    Input('filtro-año-tiempos', 'value'),
    Input('filtro-departamento-tiempos', 'value'),
    Input('filtro-estado-tiempos', 'value')
)
def actualizar_grafico_error(año, departamento, estado):
    datos_tiempos = datos.copy()
    if año is not None and 'Año' in datos_tiempos.columns:
        datos_tiempos = datos_tiempos[datos_tiempos['Año'] == año]
    if departamento is not None:
        datos_tiempos = datos_tiempos[datos_tiempos['Departamento_mapa'] == departamento]
    if estado is not None and 'Estado aviso' in datos_tiempos.columns:
        datos_tiempos = datos_tiempos[datos_tiempos['Estado aviso'] == estado]

    resumen_filtrado = datos_tiempos.groupby('Tipo de aviso')['Días abierto'].agg(['count', 'mean', 'median', 'std']).reset_index()
    resumen_filtrado['std'] = resumen_filtrado['std'].fillna(0)

    if len(resumen_filtrado) > 0:
        mayor_promedio = resumen_filtrado.loc[resumen_filtrado['mean'].idxmax()]
        tipo_destacado = mayor_promedio['Tipo de aviso']
        resumen_filtrado['color'] = resumen_filtrado['Tipo de aviso'].apply(lambda x: CIAN if x == tipo_destacado else '#6B7F91')
        resumen_filtrado['tamaño'] = resumen_filtrado['Tipo de aviso'].apply(lambda x: 16 if x == tipo_destacado else 10)
    else:
        tipo_destacado = None
        resumen_filtrado['color'] = CIAN
        resumen_filtrado['tamaño'] = 10

    figura = px.scatter(
        resumen_filtrado, x='Tipo de aviso', y='mean', error_y='std',
        hover_data={'count': True, 'median': ':.0f', 'std': ':.0f', 'mean': ':.0f', 'color': False, 'tamaño': False},
        title='Tiempo promedio de los avisos según tipo',
        labels={'Tipo de aviso': 'Tipo de aviso', 'mean': 'Promedio de días abierto', 'median': 'Mediana de días abierto', 'std': 'Desviación estándar', 'count': 'Número de avisos'}
    )
    figura.update_traces(marker={'color': resumen_filtrado['color'], 'size': resumen_filtrado['tamaño']})
    figura.update_layout(paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA, font_color=BLANCO, title_font_size=18, transition_duration=500, margin=dict(l=60, r=30, t=70, b=60))
    figura.update_xaxes(gridcolor=AZUL_BORDE)
    figura.update_yaxes(rangemode='tozero', gridcolor=AZUL_BORDE)

    hallazgo = f"Los avisos de {mayor_promedio['Tipo de aviso']} presentan el mayor tiempo promedio de apertura, con {mayor_promedio['mean']:.0f} días." if len(resumen_filtrado) > 0 else 'No se encontraron avisos para los filtros seleccionados.'
    return figura, hallazgo

@app.callback(
    Output('detalle-aviso', 'children'),
    Input('grafico-error', 'clickData'),
    Input('filtro-año-tiempos', 'value'),
    Input('filtro-departamento-tiempos', 'value'),
    Input('filtro-estado-tiempos', 'value')
)
def mostrar_detalle_aviso(clickData, año, departamento, estado):
    if clickData is None:
        return 'Haz clic sobre un punto del gráfico para consultar el detalle del tipo de aviso.'
    tipo_aviso = clickData['points'][0]['x']
    datos_detalle = datos.copy()
    if año is not None and 'Año' in datos_detalle.columns:
        datos_detalle = datos_detalle[datos_detalle['Año'] == año]
    if departamento is not None:
        datos_detalle = datos_detalle[datos_detalle['Departamento_mapa'] == departamento]
    if estado is not None and 'Estado aviso' in datos_detalle.columns:
        datos_detalle = datos_detalle[datos_detalle['Estado aviso'] == estado]

    datos_detalle = datos_detalle[datos_detalle['Tipo de aviso'] == tipo_aviso]
    total = datos_detalle['Aviso'].count()
    promedio = datos_detalle['Días abierto'].mean()
    mediana = datos_detalle['Días abierto'].median()
    desviacion = datos_detalle['Días abierto'].std()

    return html.Div([
        html.H3(tipo_aviso, style={'color': BLANCO, 'fontSize': '13px', 'margin': '0px 0px 6px 0px'}),
        html.Div([
            html.Div([html.P('Número de avisos', style={'color': GRIS_TEXTO, 'fontSize': '9px', 'margin': '0px'}), html.P(f'{total}', style={'color': CIAN, 'fontSize': '13px', 'fontWeight': 'bold', 'margin': '2px 0px'})]),
            html.Div([html.P('Promedio', style={'color': GRIS_TEXTO, 'fontSize': '9px', 'margin': '0px'}), html.P(f'{promedio:.0f} días', style={'color': CIAN, 'fontSize': '13px', 'fontWeight': 'bold', 'margin': '2px 0px'})]),
            html.Div([html.P('Mediana', style={'color': GRIS_TEXTO, 'fontSize': '9px', 'margin': '0px'}), html.P(f'{mediana:.0f} días', style={'color': CIAN, 'fontSize': '13px', 'fontWeight': 'bold', 'margin': '2px 0px'})]),
            html.Div([html.P('Desviación estándar', style={'color': GRIS_TEXTO, 'fontSize': '9px', 'margin': '0px'}), html.P(f'{desviacion:.0f} días', style={'color': CIAN, 'fontSize': '13px', 'fontWeight': 'bold', 'margin': '2px 0px'})])
        ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'columnGap': '18px', 'rowGap': '5px'})
    ])

@app.callback(
    Output('grafico-evolucion-tiempos', 'figure'),
    Input('grafico-error', 'clickData'),
    Input('filtro-departamento-tiempos', 'value'),
    Input('filtro-estado-tiempos', 'value')
)
def actualizar_evolucion_tiempos(clickData, departamento, estado):
    datos_evolucion = datos.copy()
    if departamento is not None:
        datos_evolucion = datos_evolucion[datos_evolucion['Departamento_mapa'] == departamento]
    if estado is not None and 'Estado aviso' in datos_evolucion.columns:
        datos_evolucion = datos_evolucion[datos_evolucion['Estado aviso'] == estado]

    if clickData is None or 'Año' not in datos.columns:
        figura = go.Figure()
        mensaje = 'Selecciona un tipo de aviso<br>para consultar su evolución' if 'Año' in datos.columns else 'La base de datos no contiene la columna "Año".'
        figura.add_annotation(text=mensaje, x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False, font=dict(size=13, color=GRIS_TEXTO))
        figura.update_xaxes(visible=False)
        figura.update_yaxes(visible=False)
        figura.update_layout(paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA, margin=dict(l=10, r=10, t=20, b=20))
        return figura

    tipo_aviso = clickData['points'][0]['x']
    datos_evolucion = datos_evolucion[datos_evolucion['Tipo de aviso'] == tipo_aviso]
    evolucion = datos_evolucion.dropna(subset=['Año', 'Días abierto']).groupby('Año')['Días abierto'].mean().reset_index().sort_values('Año')

    figura = px.line(evolucion, x='Año', y='Días abierto', markers=True)
    figura.update_traces(line=dict(color=CIAN, width=2), marker=dict(size=6), hovertemplate='<b>Año %{x}</b><br>Promedio: %{y:.0f} días<extra></extra>')
    figura.update_layout(
        title={'text': f'Evolución · {tipo_aviso}', 'font': {'size': 14, 'color': BLANCO}},
        paper_bgcolor=AZUL_TARJETA, plot_bgcolor=AZUL_TARJETA, font_color=BLANCO,
        margin=dict(l=45, r=15, t=50, b=40), xaxis_title='Año', yaxis_title='Promedio de días', showlegend=False, transition_duration=400
    )
    figura.update_xaxes(gridcolor=AZUL_BORDE, tickfont=dict(size=9))
    figura.update_yaxes(gridcolor=AZUL_BORDE, tickfont=dict(size=9))
    return figura

# ====================================================================
# 9. EJECUTAR LA APLICACIÓN
# ====================================================================
if __name__ == '__main__':
    app.run(debug=False, port=8050)