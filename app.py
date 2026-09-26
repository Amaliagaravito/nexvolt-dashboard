



import os
import json
import base64
import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# Paleta de colores NEXVOLT
AZUL_FONDO = '#061525'
AZUL_TARJETA = '#0B2035'
AZUL_BORDE = '#124A6B'
CIAN = '#19BDF2'
BLANCO = '#FFFFFF'
GRIS_TEXTO = '#A9BDD0'


RUTA = os.path.dirname(os.path.abspath(__file__))

historico = pd.read_excel(f'{RUTA}/histórico_filtrado_proc.xlsx')
equipos = pd.read_excel(f'{RUTA}/equipos_proc.xlsx')

datos = pd.merge(
    historico,
    equipos,
    on='Equipo',
    how='left'
)

print('Registros:', len(datos))
print('Avisos:', datos['Aviso'].nunique())
print('Equipos:', datos['Equipo'].nunique())


print('Registros sin departamento:', datos['Departamento'].isna().sum())
print('Registros sin municipio:', datos['Municipio'].isna().sum())

with open(
    f'{RUTA}/departamentos_colombia.geojson',
    'r',
    encoding='utf-8'
) as archivo:
    geojson_colombia = json.load(archivo)

print('Departamentos en GeoJSON:', len(geojson_colombia['features']))

datos['Departamento_mapa'] = (
    datos['Departamento']
    .str.upper()
    .str.strip()
)

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
    avisos_departamento,
    on='Departamento_mapa',
    how='left'
)

print('Departamentos con avisos:', mapa_departamentos['Total avisos'].notna().sum())



ruta_municipios = f'{RUTA}/capa_municipios/Limite_Municipal_2016.shp'
municipios = gpd.read_file(ruta_municipios)

print('Polígonos municipales:', len(municipios))
print('Sistema de referencia original:', municipios.crs)


# Estandarización de nombres para relacionar la base con la capa municipal

datos['Municipio_mapa'] = (
    datos['Municipio']
    .str.upper()
    .str.strip()
)

equivalencias_municipios = {
    'TIBANA': 'TIBANÁ',
    'UMBITA': 'ÚMBITA',
    'SUPIA': 'SUPÍA',
    'VILLAMARIA': 'VILLAMARÍA',
    'INZA': 'INZÁ',
    'EL PEÑON': 'EL PEÑÓN',
    'IMUES': 'IMUÉS',
    'ARMERO': 'ARMERO (GUAYABAL)',
    'SAN SEBASTIÁN DE MARIQUITA': 'MARIQUITA',
    'PATÍA': 'PATÍA (EL BORDO)',
    'SAN JUAN DE RIO SECO': 'SAN JUAN DE RIOSECO'
}

datos['Municipio_mapa'] = datos['Municipio_mapa'].replace(
    equivalencias_municipios
)

municipios['Municipio_mapa'] = (
    municipios['NOM_MUNICI']
    .str.upper()
    .str.strip()
    .str.replace(r'\s+', ' ', regex=True)
)
municipios['Departamento_mapa'] = (
    municipios['NOM_DEPART']
    .str.upper()
    .str.strip()
)



municipios[
    municipios['NOM_MUNICI'].str.contains(
        'PAT',
        case=False,
        na=False
    )
][['NOM_DEPART', 'NOM_MUNICI', 'COD_MUN']]

municipios[
    municipios['NOM_MUNICI'].str.contains(
        'PATÍA',
        case=False,
        na=False
    )
][['NOM_MUNICI', 'Municipio_mapa']]

# Comparar exactamente el nombre de Patía en ambas fuentes

nombre_datos = [
    x for x in datos['Municipio_mapa'].dropna().unique()
    if 'PATÍA' in x
]

nombre_capa = [
    x for x in municipios['Municipio_mapa'].dropna().unique()
    if 'PATÍA' in x
]

print('En la base:', nombre_datos)
print('En la capa:', nombre_capa)

print('Base:', repr(nombre_datos[0]))
print('Capa:', repr(nombre_capa[0]))

print('¿Son iguales?', nombre_datos[0] == nombre_capa[0])

# Verificación de correspondencia municipal
municipios_datos = set(datos['Municipio_mapa'].dropna())
municipios_capa = set(municipios['Municipio_mapa'].dropna())
no_coinciden = municipios_datos.difference(municipios_capa)

print('Municipios diferentes en la base:', len(municipios_datos))
print('Municipios que coinciden:', len(municipios_datos.intersection(municipios_capa)))
print('Municipios que NO coinciden:', len(no_coinciden))
print('No coinciden:', sorted(no_coinciden))

# Listas para los filtros geográficos

lista_departamentos = sorted(
    datos['Departamento_mapa']
    .dropna()
    .unique()
)

lista_municipios = sorted(
    datos['Municipio_mapa']
    .dropna()
    .unique()
)

print('Departamentos:', len(lista_departamentos))
print('Municipios:', len(lista_municipios))

# Reproyección para Plotly y conversión a GeoJSON
municipios_4326 = municipios.to_crs(epsg=4326)
geojson_municipios = json.loads(municipios_4326.to_json())

print('CRS para el mapa:', municipios_4326.crs)
print('Municipios en GeoJSON:', len(geojson_municipios['features']))

# Conteo correcto usando Departamento + Municipio
avisos_municipio_final = (
    datos.dropna(subset=['Departamento_mapa', 'Municipio_mapa'])
    .groupby(['Departamento_mapa', 'Municipio_mapa'])['Aviso']
    .count()
    .reset_index(name='Total avisos')
)

print('Municipios con avisos:', len(avisos_municipio_final))
print('Avisos representados espacialmente:', avisos_municipio_final['Total avisos'].sum())
print('Avisos totales:', datos['Aviso'].count())

resumen_tipos = (
    datos.groupby('Tipo de aviso')['Días abierto']
    .agg(['count', 'mean', 'median', 'std'])
    .reset_index()
)

fig_error = px.scatter(
    resumen_tipos,
    x='Tipo de aviso',
    y='mean',
    error_y='std',
    title='Tiempo promedio de los avisos según tipo',
    labels={
        'Tipo de aviso': 'Tipo de aviso',
        'mean': 'Promedio de días abierto',
        'std': 'Desviación estándar'
    }
)

fig_error.update_traces(
    marker={
        'size': 12,
        'color': CIAN
    }
)

fig_error.update_layout(
    paper_bgcolor=AZUL_TARJETA,
    plot_bgcolor=AZUL_TARJETA,
    font_color=BLANCO,
    title_font_size=18,
    margin=dict(
        l=60,
        r=30,
        t=70,
        b=60
    )
)

fig_error.update_xaxes(
    gridcolor=AZUL_BORDE
)

fig_error.update_yaxes(
    rangemode='tozero',
    gridcolor=AZUL_BORDE
)



# Paleta de colores NEXVOLT


total_avisos = datos['Aviso'].nunique()
total_equipos = datos['Equipo'].nunique()
total_departamentos = datos['Departamento'].nunique()
total_tipos = datos['Tipo de aviso'].nunique()
año_min = int(datos['Año'].min())
año_max = int(datos['Año'].max())

print('Avisos:', total_avisos)
print('Equipos:', total_equipos)
print('Departamentos:', total_departamentos)
print('Tipos:', total_tipos)
print('Periodo:', año_min, '-', año_max)

import base64

ruta_imagen = os.path.join(RUTA, 'assets', 'hero_nexvolt.png')

with open(ruta_imagen, 'rb') as archivo:
    imagen_codificada = base64.b64encode(archivo.read()).decode()

hero_imagen = 'data:image/png;base64,' + imagen_codificada

# Departamentos sin registros
mapa_sin_datos = mapa_departamentos[
    mapa_departamentos['Total avisos'].isna()
]

# Departamentos con registros
mapa_con_datos = mapa_departamentos[
    mapa_departamentos['Total avisos'].notna()
]

# Mapa de departamentos con registros
fig_mapa_nexvolt = px.choropleth_map(
    mapa_con_datos,
    geojson=geojson_colombia,
    locations='Departamento_mapa',
    featureidkey='properties.dpto_cnmbr',
    color='Total avisos',
    color_continuous_scale=[
        [0, '#B8E3F2'],
        [0.5, '#258AC4'],
        [1, '#06466D']
    ],
    map_style='carto-darkmatter',
    center={'lat': 4.5, 'lon': -74},
    zoom=4.2,
    opacity=0.9,
    hover_name='Departamento_mapa',
    hover_data={
        'Departamento_mapa': False,
        'Total avisos': True
    }
)

# Departamentos sin registros
fig_sin_datos = px.choropleth_map(
    mapa_sin_datos,
    geojson=geojson_colombia,
    locations='Departamento_mapa',
    featureidkey='properties.dpto_cnmbr',
    color_discrete_sequence=['#4B5563'],
    map_style='carto-darkmatter',
    center={'lat': 4.5, 'lon': -74},
    zoom=4.2
)

# Agregar los departamentos sin registros al mapa
for traza in fig_sin_datos.data:
    fig_mapa_nexvolt.add_trace(traza)

# Diseño del mapa
fig_mapa_nexvolt.update_layout(
    title='Distribución de avisos por departamento',
    paper_bgcolor=AZUL_TARJETA,
    plot_bgcolor=AZUL_TARJETA,
    font_color=BLANCO,
    margin=dict(l=0, r=0, t=50, b=0),
    coloraxis_colorbar=dict(
        title='Avisos'
    )
)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Menú lateral NEXVOLT

menu_lateral = html.Div([

    html.Div([
        html.H1([
            'NEX',
            html.Span('VOLT', style={'color': CIAN})
        ], style={
            'color': BLANCO,
            'marginBottom': '5px'
        }),

        html.P(
            'Energía · Infraestructura · Eficiencia',
            style={
                'color': GRIS_TEXTO,
                'fontSize': '12px',
                'marginTop': '0px'
            }
        )
    ]),

    html.Div([

        dcc.Link(
            '⌂  Inicio',
            href='/',
            style={
                'display': 'block',
                'padding': '14px',
                'marginTop': '40px',
                'marginBottom': '10px',
                'color': BLANCO,
                'textDecoration': 'none',
                'borderRadius': '8px'
            }
        ),

        dcc.Link(
            '▣  Mapa coroplético',
            href='/territorial',
            style={
                'display': 'block',
                'padding': '14px',
                'marginBottom': '10px',
                'color': GRIS_TEXTO,
                'textDecoration': 'none',
                'borderRadius': '8px'
            }
        ),

        dcc.Link(
            '▥  Gráfico de errores',
            href='/tiempos',
            style={
                'display': 'block',
                'padding': '14px',
                'marginBottom': '10px',
                'color': GRIS_TEXTO,
                'textDecoration': 'none',
                'borderRadius': '8px'
            }
        )

    ]),

    html.P(
        'Energía confiable para un futuro sostenible.',
        style={
            'color': GRIS_TEXTO,
            'fontSize': '13px',
            'position': 'absolute',
            'bottom': '30px',
            'width': '190px'
        }
    )

], style={
    'width': '250px',
    'height': '100vh',
    'backgroundColor': AZUL_FONDO,
    'padding': '30px 20px',
    'boxSizing': 'border-box',
    'position': 'fixed',
    'left': '0',
    'top': '0'
})

# Página de inicio NEXVOLT

pagina_inicio = html.Div([

    # Sección principal
    html.Div([

        # Texto principal
        html.Div([

            html.P(
                'INFRAESTRUCTURA ELÉCTRICA PARA UN PAÍS QUE AVANZA',
                style={
                    'color': CIAN,
                    'fontSize': '13px',
                    'letterSpacing': '2px',
                    'marginBottom': '15px'
                }
            ),

            html.H1([
                'Energía que conecta ',
                html.Span(
                    'territorios',
                    style={'color': CIAN}
                )
            ], style={
                'color': BLANCO,
                'fontSize': '46px',
                'marginTop': '0px',
                'marginBottom': '18px'
            }),

            html.P(
                'Soluciones integrales para la gestión, operación y eficiencia '
                'de infraestructura eléctrica, contribuyendo al desarrollo '
                'sostenible de Colombia.',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '17px',
                    'lineHeight': '1.6',
                    'maxWidth': '560px'
                }
            )

        ], style={
            'width': '48%',
            'paddingRight': '30px',
            'boxSizing': 'border-box'
        }),

        # Imagen
        html.Div([

            html.Img(
                src=hero_imagen,
                style={
                    'width': '100%',
                    'height': '300px',
                    'objectFit': 'cover',
                    'borderRadius': '12px'
                }
            )

        ], style={
            'width': '52%'
        })

    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'paddingTop': '35px',
        'paddingBottom': '35px'
    }),

    # Indicadores
    html.Div([

        html.Div([
            html.H2(
                f'{total_avisos:,}'.replace(',', '.'),
                style={
                    'color': BLANCO,
                    'marginBottom': '5px'
                }
            ),
            html.P(
                'Avisos registrados',
                style={
                    'color': GRIS_TEXTO,
                    'margin': '0'
                }
            )
        ], style={
            'backgroundColor': AZUL_TARJETA,
            'border': f'1px solid {AZUL_BORDE}',
            'borderRadius': '10px',
            'padding': '20px',
            'flex': '1'
        }),

        html.Div([
            html.H2(
                f'{total_equipos:,}'.replace(',', '.'),
                style={
                    'color': BLANCO,
                    'marginBottom': '5px'
                }
            ),
            html.P(
                'Equipos monitoreados',
                style={
                    'color': GRIS_TEXTO,
                    'margin': '0'
                }
            )
        ], style={
            'backgroundColor': AZUL_TARJETA,
            'border': f'1px solid {AZUL_BORDE}',
            'borderRadius': '10px',
            'padding': '20px',
            'flex': '1'
        }),

        html.Div([
            html.H2(
                str(total_departamentos),
                style={
                    'color': BLANCO,
                    'marginBottom': '5px'
                }
            ),
            html.P(
                'Departamentos con registros',
                style={
                    'color': GRIS_TEXTO,
                    'margin': '0'
                }
            )
        ], style={
            'backgroundColor': AZUL_TARJETA,
            'border': f'1px solid {AZUL_BORDE}',
            'borderRadius': '10px',
            'padding': '20px',
            'flex': '1'
        }),

        html.Div([
            html.H2(
                f'{año_min}–{año_max}',
                style={
                    'color': BLANCO,
                    'marginBottom': '5px'
                }
            ),
            html.P(
                'Periodo analizado',
                style={
                    'color': GRIS_TEXTO,
                    'margin': '0'
                }
            )
        ], style={
            'backgroundColor': AZUL_TARJETA,
            'border': f'1px solid {AZUL_BORDE}',
            'borderRadius': '10px',
            'padding': '20px',
            'flex': '1'
        })

    ], style={
        'display': 'flex',
        'gap': '18px'
    })
    ,

    # Sección institucional
    html.Div([

        html.P(
            'NUESTRAS SOLUCIONES',
            style={
                'color': CIAN,
                'fontSize': '12px',
                'letterSpacing': '2px',
                'marginBottom': '8px'
            }
        ),

        html.H2(
            'Energía, infraestructura y eficiencia',
            style={
                'color': BLANCO,
                'fontSize': '28px',
                'marginTop': '0px',
                'marginBottom': '10px'
            }
        ),

        html.P(
            'En NEXVOLT desarrollamos soluciones orientadas a la gestión '
            'y operación de infraestructura eléctrica, apoyando el seguimiento '
            'de activos y la atención de situaciones asociadas a la red.',
            style={
                'color': GRIS_TEXTO,
                'fontSize': '15px',
                'lineHeight': '1.6',
                'maxWidth': '750px',
                'marginBottom': '25px'
            }
        ),

        # Tres líneas de trabajo
        html.Div([

            html.Div([
                html.H3(
                    'Infraestructura eléctrica',
                    style={'color': BLANCO}
                ),
                html.P(
                    'Gestión y seguimiento de activos asociados '
                    'a redes y sistemas eléctricos.',
                    style={
                        'color': GRIS_TEXTO,
                        'lineHeight': '1.5'
                    }
                )
            ], style={
                'backgroundColor': AZUL_TARJETA,
                'border': f'1px solid {AZUL_BORDE}',
                'borderRadius': '10px',
                'padding': '20px',
                'flex': '1'
            }),

            html.Div([
                html.H3(
                    'Operación y mantenimiento',
                    style={'color': BLANCO}
                ),
                html.P(
                    'Monitoreo de avisos y situaciones que requieren '
                    'atención sobre la infraestructura.',
                    style={
                        'color': GRIS_TEXTO,
                        'lineHeight': '1.5'
                    }
                )
            ], style={
                'backgroundColor': AZUL_TARJETA,
                'border': f'1px solid {AZUL_BORDE}',
                'borderRadius': '10px',
                'padding': '20px',
                'flex': '1'
            }),

            html.Div([
                html.H3(
                    'Eficiencia energética',
                    style={'color': BLANCO}
                ),
                html.P(
                    'Información para apoyar una operación más eficiente, '
                    'confiable y sostenible.',
                    style={
                        'color': GRIS_TEXTO,
                        'lineHeight': '1.5'
                    }
                )
            ], style={
                'backgroundColor': AZUL_TARJETA,
                'border': f'1px solid {AZUL_BORDE}',
                'borderRadius': '10px',
                'padding': '20px',
                'flex': '1'
            })

        ], style={
            'display': 'flex',
            'gap': '18px'
        })

    ], style={
        'paddingTop': '55px',
        'paddingBottom': '50px'
    })

], style={
    'marginLeft': '250px',
    'minHeight': '100vh',
    'backgroundColor': AZUL_FONDO,
    'padding': '30px 45px',
    'boxSizing': 'border-box'
})

pagina_territorial = html.Div([

    # Encabezado
    html.Div([

        html.P(
            'MONITOREO OPERACIONAL',
            style={
                'color': CIAN,
                'fontSize': '12px',
                'letterSpacing': '2px',
                'marginBottom': '8px'
            }
        ),

        html.H1(
            'Mapa coroplético',
            style={
                'color': BLANCO,
                'fontSize': '36px',
                'marginTop': '0px',
                'marginBottom': '8px'
            }
        ),

        html.P(
            'Distribución geográfica de los avisos asociados '
            'a la infraestructura eléctrica.',
            style={
                'color': GRIS_TEXTO,
                'fontSize': '15px',
                'marginTop': '0px'
            }
        )

    ]),

    # -------------------------------------------------
    # PRIMERA FILA DE FILTROS
    # -------------------------------------------------

    html.Div([

        # Nivel de visualización
        html.Div([

            html.Label(
                'Nivel de visualización',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-nivel',
                options=[
                    {
                        'label': 'Departamento',
                        'value': 'Departamento'
                    },
                    {
                        'label': 'Municipio',
                        'value': 'Municipio'
                    }
                ],
                value='Departamento',
                clearable=False
            )

        ], style={
            'width': '32%'
        }),

        # Departamento
        html.Div([

            html.Label(
                'Departamento',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-departamento',
                options=[
                    {
                        'label': departamento.title(),
                        'value': departamento
                    }
                    for departamento in lista_departamentos
                ],
                placeholder='Todos los departamentos',
                clearable=True
            )

        ], style={
            'width': '32%'
        }),

        # Municipio
        html.Div([

            html.Label(
                'Municipio',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-municipio',
                options=[
                    {
                        'label': municipio.title(),
                        'value': municipio
                    }
                    for municipio in lista_municipios
                ],
                placeholder='Todos los municipios',
                clearable=True
            )

        ], style={
            'width': '32%'
        })

    ], style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'gap': '15px',
        'marginTop': '30px',
        'marginBottom': '18px'
    }),

    # -------------------------------------------------
    # SEGUNDA FILA DE FILTROS
    # -------------------------------------------------

        html.Div([

        # Año
        html.Div([

            html.Label(
                'Año',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-año',
                options=[
                    {'label': 'Todos los años', 'value': None}
                ] + [
                    {'label': str(año), 'value': año}
                    for año in sorted(
                        datos['Año'].dropna().unique()
                    )
                ],
                value=None,
                placeholder='Todos los años'
            )

        ], style={
            'width': '32%'
        }),

        # Tipo de aviso
        html.Div([

            html.Label(
                'Tipo de aviso',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-tipo',
                options=[
                    {'label': 'Todos los tipos', 'value': None}
                ] + [
                    {'label': tipo, 'value': tipo}
                    for tipo in sorted(
                        datos['Tipo de aviso'].dropna().unique()
                    )
                ],
                value=None,
                placeholder='Todos los tipos'
            )

        ], style={
            'width': '32%'
        }),

        # Estado
        html.Div([

            html.Label(
                'Estado',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-estado',
                options=[
                    {'label': 'Todos los estados', 'value': None}
                ] + [
                    {'label': estado, 'value': estado}
                    for estado in sorted(
                        datos['Estado aviso'].dropna().unique()
                    )
                ],
                value=None,
                placeholder='Todos los estados'
            )

        ], style={
            'width': '32%'
        })

    ], style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'gap': '15px',
        'marginBottom': '25px'
    }),


        # -------------------------------------------------
    # INDICADOR Y MAPA
    # -------------------------------------------------

    # Indicador de cantidad de avisos
    html.Div([

        html.Div([
            html.P(
                'TOTAL DE AVISOS',
                style={
                    'color': CIAN,
                    'fontSize': '11px',
                    'letterSpacing': '1.5px',
                    'margin': '0px'
                }
            ),

            html.H2(
                '3.118 avisos',
                id='total-avisos-mapa',
                style={
                    'color': BLANCO,
                    'fontSize': '26px',
                    'marginTop': '4px',
                    'marginBottom': '2px'
                }
            ),

            html.P(
                'Registros correspondientes a los filtros seleccionados',
                id='texto-total-avisos',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '12px',
                    'margin': '0px'
                }
            )

        ])

    ], style={
        'backgroundColor': AZUL_TARJETA,
        'border': f'1px solid {AZUL_BORDE}',
        'borderRadius': '10px',
        'padding': '12px 18px',
        'marginBottom': '15px'
    }),

    # Mapa
    html.Div([

        dcc.Graph(
            id='mapa-avisos',
            figure=fig_mapa_nexvolt,
            config={
                'displayModeBar': False
            },
            style={
                'height': '560px'
            }
        )

    ], style={
        'backgroundColor': AZUL_TARJETA,
        'border': f'1px solid {AZUL_BORDE}',
        'borderRadius': '12px',
        'padding': '10px',
        'overflow': 'hidden'
    })

], style={
    'minHeight': '100vh',
    'backgroundColor': AZUL_FONDO,
    'padding': '35px 45px',
    'marginLeft': '250px',
    'width': 'calc(100% - 250px)',
    'boxSizing': 'border-box'
})


# -------------------------------------------------
# PÁGINA 2 - GESTIÓN DE TIEMPOS
# -------------------------------------------------

pagina_tiempos = html.Div([

    # Encabezado
    html.Div([

        html.P(
            'GESTIÓN OPERACIONAL',
            style={
                'color': CIAN,
                'fontSize': '12px',
                'letterSpacing': '2px',
                'marginBottom': '8px'
            }
        ),

        html.H1(
            'Gráfico de errores',
            style={
                'color': BLANCO,
                'fontSize': '36px',
                'marginTop': '0px',
                'marginBottom': '8px'
            }
        ),

        html.P(
            'Análisis del tiempo de atención de los avisos '
            'y su variabilidad según el tipo de aviso.',
            style={
                'color': GRIS_TEXTO,
                'fontSize': '15px',
                'marginTop': '0px',
                'marginBottom': '8px'
            }
        ),

      html.P(
        'Los avisos de Construcciones presentan el mayor '
        'tiempo promedio de apertura y la mayor variabilidad.',
        id='hallazgo-tiempos',
        style={
          'color': CIAN,
          'fontSize': '14px',
          'marginTop': '0px',
          'marginBottom': '25px'
       }
    )

    ]),

    # -------------------------------------------------
    # FILTROS
    # -------------------------------------------------

    html.Div([

        # Año
        html.Div([

            html.Label(
                'Año',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-año-tiempos',
                options=[
                    {'label': 'Todos los años', 'value': None}
                ] + [
                    {'label': str(año), 'value': año}
                    for año in sorted(
                        datos['Año'].dropna().unique()
                    )
                ],
                value=None,
                placeholder='Todos los años'
            )

        ], style={
            'width': '32%'
        }),

        # Departamento
        html.Div([

            html.Label(
                'Departamento',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-departamento-tiempos',
                options=[
                    {
                        'label': 'Todos los departamentos',
                        'value': None
                    }
                ] + [
                    {
                        'label': departamento.title(),
                        'value': departamento
                    }
                    for departamento in lista_departamentos
                ],
                value=None,
                placeholder='Todos los departamentos'
            )

        ], style={
            'width': '32%'
        }),

        # Estado
        html.Div([

            html.Label(
                'Estado',
                style={
                    'color': GRIS_TEXTO,
                    'fontSize': '13px'
                }
            ),

            dcc.Dropdown(
                id='filtro-estado-tiempos',
                options=[
                    {'label': 'Todos los estados', 'value': None}
                ] + [
                    {
                        'label': estado,
                        'value': estado
                    }
                    for estado in sorted(
                        datos['Estado aviso'].dropna().unique()
                    )
                ],
                value=None,
                placeholder='Todos los estados'
            )

        ], style={
            'width': '32%'
        })

    ], style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'gap': '15px',
        'marginBottom': '25px'
    }),

    # -------------------------------------------------
    # GRÁFICO DE ERRORES
    # -------------------------------------------------

    html.Div([

        dcc.Graph(
            id='grafico-error',
            figure=fig_error,
            config={
                'displayModeBar': False
            },
            style={
                'height': '560px'
            }
        )

    ], style={
        'backgroundColor': AZUL_TARJETA,
        'border': f'1px solid {AZUL_BORDE}',
        'borderRadius': '12px',
        'padding': '10px',
        'overflow': 'hidden'
    }),

    # -------------------------------------------------
    # DETALLE DEL TIPO DE AVISO
    # -------------------------------------------------

    html.Div([

        html.P(
            'DETALLE DEL TIPO DE AVISO',
            style={
                'color': CIAN,
                'fontSize': '11px',
                'letterSpacing': '1.5px',
                'marginTop': '0px',
                'marginBottom': '8px'
            }
        ),

        html.Div(
            'Haz clic sobre un punto del gráfico para consultar '
            'el detalle del tipo de aviso.',
            id='detalle-aviso',
            style={
                'color': GRIS_TEXTO,
                'fontSize': '14px'
            }
        )

    ], style={
        'backgroundColor': AZUL_TARJETA,
        'border': f'1px solid {AZUL_BORDE}',
        'borderRadius': '10px',
        'padding': '16px 18px',
        'marginTop': '15px'
    })

], style={
    'minHeight': '100vh',
    'backgroundColor': AZUL_FONDO,
    'padding': '35px 45px',
    'marginLeft': '250px',
    'width': 'calc(100% - 250px)',
    'boxSizing': 'border-box'
})

# -------------------------------------------------
# CALLBACK - GRÁFICO DE ERRORES
# -------------------------------------------------

@app.callback(
    Output('grafico-error', 'figure'),
    Output('hallazgo-tiempos', 'children'),
    Input('filtro-año-tiempos', 'value'),
    Input('filtro-departamento-tiempos', 'value'),
    Input('filtro-estado-tiempos', 'value')
)
def actualizar_grafico_error(año, departamento, estado):

    # Copia de los datos originales
    datos_tiempos = datos.copy()

    # Filtro por año
    if año is not None:
        datos_tiempos = datos_tiempos[
            datos_tiempos['Año'] == año
        ]

    # Filtro por departamento
    if departamento is not None:
        datos_tiempos = datos_tiempos[
            datos_tiempos['Departamento_mapa'] == departamento
        ]

    # Filtro por estado
    if estado is not None:
        datos_tiempos = datos_tiempos[
            datos_tiempos['Estado aviso'] == estado
        ]

    # Resumen por tipo de aviso
    resumen_filtrado = (
        datos_tiempos
        .groupby('Tipo de aviso')['Días abierto']
        .agg(['count', 'mean', 'median', 'std'])
        .reset_index()
    )

    # Reemplazar desviaciones vacías por cero
    resumen_filtrado['std'] = resumen_filtrado['std'].fillna(0)

    # Identificar el tipo con mayor promedio
    if len(resumen_filtrado) > 0:

        mayor_promedio = resumen_filtrado.loc[
            resumen_filtrado['mean'].idxmax()
        ]

        tipo_destacado = mayor_promedio['Tipo de aviso']

        # Color y tamaño de cada punto
        resumen_filtrado['color'] = resumen_filtrado[
            'Tipo de aviso'
        ].apply(
            lambda x: CIAN if x == tipo_destacado else '#6B7F91'
        )

        resumen_filtrado['tamaño'] = resumen_filtrado[
            'Tipo de aviso'
        ].apply(
            lambda x: 16 if x == tipo_destacado else 10
        )

    else:
        tipo_destacado = None
        resumen_filtrado['color'] = CIAN
        resumen_filtrado['tamaño'] = 10

    # Gráfico
    figura = px.scatter(
        resumen_filtrado,
        x='Tipo de aviso',
        y='mean',
        error_y='std',

        hover_data={
            'count': True,
            'median': ':.0f',
            'std': ':.0f',
            'mean': ':.0f',
            'color': False,
            'tamaño': False
        },

        title='Tiempo promedio de los avisos según tipo',

        labels={
            'Tipo de aviso': 'Tipo de aviso',
            'mean': 'Promedio de días abierto',
            'median': 'Mediana de días abierto',
            'std': 'Desviación estándar',
            'count': 'Número de avisos'
        }
    )

    # Resaltado visual
    figura.update_traces(
        marker={
            'color': resumen_filtrado['color'],
            'size': resumen_filtrado['tamaño']
        }
    )

    figura.update_layout(
        paper_bgcolor=AZUL_TARJETA,
        plot_bgcolor=AZUL_TARJETA,
        font_color=BLANCO,
        title_font_size=18,
        transition_duration=500,
        margin=dict(
            l=60,
            r=30,
            t=70,
            b=60
        )
    )

    figura.update_xaxes(
        gridcolor=AZUL_BORDE
    )

    figura.update_yaxes(
        rangemode='tozero',
        gridcolor=AZUL_BORDE
    )

    # Hallazgo principal
    if len(resumen_filtrado) > 0:

        hallazgo = (
            f"Los avisos de {mayor_promedio['Tipo de aviso']} "
            f"presentan el mayor tiempo promedio de apertura, "
            f"con {mayor_promedio['mean']:.0f} días."
        )

    else:
        hallazgo = (
            'No se encontraron avisos para los filtros seleccionados.'
        )

    return figura, hallazgo

# -------------------------------------------------
# CALLBACK - DETALLE AL HACER CLIC
# -------------------------------------------------

@app.callback(
    Output('detalle-aviso', 'children'),
    Input('grafico-error', 'clickData'),
    Input('filtro-año-tiempos', 'value'),
    Input('filtro-departamento-tiempos', 'value'),
    Input('filtro-estado-tiempos', 'value')
)
def mostrar_detalle_aviso(clickData, año, departamento, estado):

    if clickData is None:
        return (
            'Haz clic sobre un punto del gráfico para consultar '
            'el detalle del tipo de aviso.'
        )

    # Tipo de aviso seleccionado en el gráfico
    tipo_aviso = clickData['points'][0]['x']

    # Copia de los datos
    datos_detalle = datos.copy()

    # Aplicar los mismos filtros del gráfico
    if año is not None:
        datos_detalle = datos_detalle[
            datos_detalle['Año'] == año
        ]

    if departamento is not None:
        datos_detalle = datos_detalle[
            datos_detalle['Departamento_mapa'] == departamento
        ]

    if estado is not None:
        datos_detalle = datos_detalle[
            datos_detalle['Estado aviso'] == estado
        ]

    # Seleccionar el tipo de aviso sobre el que se hizo clic
    datos_detalle = datos_detalle[
        datos_detalle['Tipo de aviso'] == tipo_aviso
    ]

    # Calcular indicadores
    total = datos_detalle['Aviso'].count()
    promedio = datos_detalle['Días abierto'].mean()
    mediana = datos_detalle['Días abierto'].median()
    desviacion = datos_detalle['Días abierto'].std()

    return html.Div([

        html.H3(
            tipo_aviso,
            style={
                'color': BLANCO,
                'marginTop': '0px',
                'marginBottom': '12px'
            }
        ),

        html.Div([

            html.Div([
                html.P(
                    'Número de avisos',
                    style={
                        'color': GRIS_TEXTO,
                        'margin': '0px'
                    }
                ),
                html.H3(
                    f'{total}',
                    style={
                        'color': CIAN,
                        'margin': '5px 0px'
                    }
                )
            ], style={'width': '24%'}),

            html.Div([
                html.P(
                    'Promedio',
                    style={
                        'color': GRIS_TEXTO,
                        'margin': '0px'
                    }
                ),
                html.H3(
                    f'{promedio:.0f} días',
                    style={
                        'color': CIAN,
                        'margin': '5px 0px'
                    }
                )
            ], style={'width': '24%'}),

            html.Div([
                html.P(
                    'Mediana',
                    style={
                        'color': GRIS_TEXTO,
                        'margin': '0px'
                    }
                ),
                html.H3(
                    f'{mediana:.0f} días',
                    style={
                        'color': CIAN,
                        'margin': '5px 0px'
                    }
                )
            ], style={'width': '24%'}),

            html.Div([
                html.P(
                    'Desviación estándar',
                    style={
                        'color': GRIS_TEXTO,
                        'margin': '0px'
                    }
                ),
                html.H3(
                    f'{desviacion:.0f} días',
                    style={
                        'color': CIAN,
                        'margin': '5px 0px'
                    }
                )
            ], style={'width': '24%'})

        ], style={
            'display': 'flex',
            'justifyContent': 'space-between'
        })

    ])

app.layout = html.Div([

    dcc.Location(id='url', refresh=False),

    menu_lateral,

    # Página de inicio
    html.Div(
        pagina_inicio,
        id='contenedor-inicio'
    ),

    # Página del mapa coroplético
    html.Div(
        pagina_territorial,
        id='contenedor-territorial',
        style={'display': 'none'}
    ),

    # Página del gráfico de errores
    html.Div(
        pagina_tiempos,
        id='contenedor-tiempos',
        style={'display': 'none'}
    )

], style={

    'fontFamily': 'Arial, sans-serif',
    'margin': '0'

})

@app.callback(
    Output('contenedor-inicio', 'style'),
    Output('contenedor-territorial', 'style'),
    Output('contenedor-tiempos', 'style'),
    Input('url', 'pathname')
)
def mostrar_pagina(pathname):

    # Página del mapa coroplético
    if pathname == '/territorial':
        return (
            {'display': 'none'},
            {'display': 'block'},
            {'display': 'none'}
        )

    # Página del gráfico de errores
    if pathname == '/tiempos':
        return (
            {'display': 'none'},
            {'display': 'none'},
            {'display': 'block'}
        )

    # Página de inicio
    return (
        {'display': 'block'},
        {'display': 'none'},
        {'display': 'none'}
    )

@app.callback(
    Output('filtro-municipio', 'options'),
    Output('filtro-municipio', 'value'),
    Input('filtro-departamento', 'value')
)
def actualizar_municipios(departamento):

    if departamento is None:
        municipios_disponibles = (
            datos['Municipio_mapa']
            .dropna()
            .unique()
        )

    else:
        municipios_disponibles = (
            datos[
                datos['Departamento_mapa'] == departamento
            ]['Municipio_mapa']
            .dropna()
            .unique()
        )

    municipios_disponibles = sorted(municipios_disponibles)

    opciones = [
        {
            'label': municipio.title(),
            'value': municipio
        }
        for municipio in municipios_disponibles
    ]

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
def actualizar_mapa(
    nivel,
    departamento,
    municipio,
    año,
    tipo,
    estado
):

    # Copiar los datos originales
    datos_filtrados = datos.copy()

    # Filtro de departamento
    if departamento is not None:
        datos_filtrados = datos_filtrados[
            datos_filtrados['Departamento_mapa'] == departamento
        ]

    # Filtro de municipio
    if nivel == 'Municipio' and municipio is not None:
        datos_filtrados = datos_filtrados[
            datos_filtrados['Municipio_mapa'] == municipio
        ]

    # Filtro de año
    if año is not None:
        datos_filtrados = datos_filtrados[
            datos_filtrados['Año'] == año
        ]

    # Filtro de tipo de aviso
    if tipo is not None:
        datos_filtrados = datos_filtrados[
            datos_filtrados['Tipo de aviso'] == tipo
        ]

    # Filtro de estado
    if estado is not None:
        datos_filtrados = datos_filtrados[
            datos_filtrados['Estado aviso'] == estado
        ]

    # -------------------------------------------------
    # MAPA POR DEPARTAMENTO
    # -------------------------------------------------


    if nivel == 'Departamento':

        avisos_filtrados = (
            datos_filtrados
            .dropna(subset=['Departamento_mapa'])
            .groupby('Departamento_mapa')['Aviso']
            .count()
            .reset_index(name='Total avisos')
        )

        mapa_filtrado = departamentos.merge(
            avisos_filtrados,
            on='Departamento_mapa',
            how='left'
        )

        # Si se selecciona un departamento,
        # mostrar solamente ese departamento
        if departamento is not None:
            mapa_filtrado = mapa_filtrado[
                mapa_filtrado['Departamento_mapa'] == departamento
            ]

        # Identificar los departamentos que se van a mostrar
        departamentos_seleccionados = set(
            mapa_filtrado['Departamento_mapa']
        )

        # Crear un GeoJSON solamente con los departamentos
        # que realmente se necesitan mostrar
        geojson_departamentos_filtrado = {
            'type': 'FeatureCollection',
            'features': [
                elemento
                for elemento in geojson_colombia['features']
                if elemento['properties']['dpto_cnmbr']
                in departamentos_seleccionados
            ]
        }

        mapa_con_datos = mapa_filtrado[
            mapa_filtrado['Total avisos'].notna()
        ]

        mapa_sin_datos = mapa_filtrado[
            mapa_filtrado['Total avisos'].isna()
        ]

        figura = px.choropleth_map(
            mapa_con_datos,
            geojson=geojson_departamentos_filtrado,
            locations='Departamento_mapa',
            featureidkey='properties.dpto_cnmbr',
            color='Total avisos',
            color_continuous_scale=[
                [0, '#B8E3F2'],
                [0.5, '#258AC4'],
                [1, '#06466D']
            ],
            map_style='carto-darkmatter',
            center={'lat': 4.5, 'lon': -74},
            zoom=4.2,
            opacity=0.9,
            hover_name='Departamento_mapa',
            hover_data={
                'Departamento_mapa': False,
                'Total avisos': True
            }
        )

        figura_sin_datos = px.choropleth_map(
            mapa_sin_datos,
            geojson=geojson_departamentos_filtrado,
            locations='Departamento_mapa',
            featureidkey='properties.dpto_cnmbr',
            color_discrete_sequence=['#4B5563'],
            map_style='carto-darkmatter',
            center={'lat': 4.5, 'lon': -74},
            zoom=4.2
        )

        for traza in figura_sin_datos.data:
            figura.add_trace(traza)

        titulo = 'Distribución de avisos por departamento'

        # Zoom al departamento seleccionado
        if departamento is not None:

            # Buscar directamente la geometría del departamento
            departamento_geojson = [
                elemento
                for elemento in geojson_colombia['features']
                if elemento['properties']['dpto_cnmbr']
                == departamento
            ]

            if len(departamento_geojson) > 0:

                departamento_geo = municipios_4326[
                    municipios_4326['Departamento_mapa']
                    == departamento
                ]

                if len(departamento_geo) > 0:

                    centro = (
                        departamento_geo
                        .geometry
                        .union_all()
                        .centroid
                    )

                    figura.update_layout(
                        map_center={
                            'lat': centro.y,
                            'lon': centro.x
                        },
                        map_zoom=7
                    )



    # -------------------------------------------------
    # MAPA POR MUNICIPIO
    # -------------------------------------------------

    else:

        avisos_filtrados = (
            datos_filtrados
            .dropna(
                subset=[
                    'Departamento_mapa',
                    'Municipio_mapa'
                ]
            )
            .groupby(
                [
                    'Departamento_mapa',
                    'Municipio_mapa'
                ]
            )['Aviso']
            .count()
            .reset_index(name='Total avisos')
        )

        # Partir de la capa municipal completa
        municipios_seleccionados = municipios_4326.copy()

        # Si hay departamento seleccionado,
        # conservar solamente sus municipios
        if departamento is not None:
            municipios_seleccionados = municipios_seleccionados[
                municipios_seleccionados['Departamento_mapa']
                == departamento
            ]

        # Si hay municipio seleccionado,
        # conservar solamente ese municipio
        if municipio is not None:
            municipios_seleccionados = municipios_seleccionados[
                municipios_seleccionados['Municipio_mapa']
                == municipio
            ]

        # Crear un GeoJSON solamente con las geometrías
        # que realmente se necesitan mostrar
        geojson_seleccionado = json.loads(
            municipios_seleccionados.to_json()
        )

        # Tabla para relacionar geometría y cantidad de avisos
        municipios_mapa = municipios_seleccionados[
            [
                'Departamento_mapa',
                'Municipio_mapa',
                'COD_MUN'
            ]
        ].copy()

        mapa_filtrado = municipios_mapa.merge(
            avisos_filtrados,
            on=[
                'Departamento_mapa',
                'Municipio_mapa'
            ],
            how='left'
        )

        mapa_con_datos = mapa_filtrado[
            mapa_filtrado['Total avisos'].notna()
        ]

        mapa_sin_datos = mapa_filtrado[
            mapa_filtrado['Total avisos'].isna()
        ]

        # Municipios con avisos
        figura = px.choropleth_map(
            mapa_con_datos,
            geojson=geojson_seleccionado,
            locations='COD_MUN',
            featureidkey='properties.COD_MUN',
            color='Total avisos',
            color_continuous_scale=[
                [0, '#B8E3F2'],
                [0.5, '#258AC4'],
                [1, '#06466D']
            ],
            map_style='carto-darkmatter',
            center={'lat': 4.5, 'lon': -74},
            zoom=4.2,
            opacity=0.9,
            hover_name='Municipio_mapa',
            hover_data={
                'Municipio_mapa': False,
                'Departamento_mapa': True,
                'Total avisos': True,
                'COD_MUN': False
            }
        )

        # Municipios sin avisos
        figura_sin_datos = px.choropleth_map(
            mapa_sin_datos,
            geojson=geojson_seleccionado,
            locations='COD_MUN',
            featureidkey='properties.COD_MUN',
            color_discrete_sequence=['#4B5563'],
            map_style='carto-darkmatter',
            center={'lat': 4.5, 'lon': -74},
            zoom=4.2
        )

        for traza in figura_sin_datos.data:
            figura.add_trace(traza)

        titulo = 'Distribución de avisos por municipio'

        # Zoom al municipio seleccionado
        if municipio is not None:

            if len(municipios_seleccionados) > 0:

                centro = (
                    municipios_seleccionados
                    .geometry
                    .union_all()
                    .centroid
                )

                figura.update_layout(
                    map_center={
                        'lat': centro.y,
                        'lon': centro.x
                    },
                    map_zoom=10
                )

        # Si solo se selecciona departamento,
        # acercarse al departamento
        elif departamento is not None:

            if len(municipios_seleccionados) > 0:

                centro = (
                    municipios_seleccionados
                    .geometry
                    .union_all()
                    .centroid
                )

                figura.update_layout(
                    map_center={
                        'lat': centro.y,
                        'lon': centro.x
                    },
                    map_zoom=7
                )

    # -------------------------------------------------
    # DISEÑO GENERAL
    # -------------------------------------------------

    figura.update_layout(
        title=titulo,
        paper_bgcolor=AZUL_TARJETA,
        plot_bgcolor=AZUL_TARJETA,
        font_color=BLANCO,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title='Avisos'
        )
    )

    total_avisos_filtrados = len(datos_filtrados)

    texto_total = f'{total_avisos_filtrados:,}'.replace(',', '.') + ' avisos'

    return figura, texto_total

if __name__ == '__main__':
    app.run(debug=False)

import os


