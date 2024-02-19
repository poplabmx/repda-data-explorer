import streamlit as st
import pandas as pd
import geopandas as gpd
from diagnostics import run_df_diagnostics
import plotly.express as px
from streamlit_option_menu import option_menu


# Utils


def exclusive_categorical_search(df, filters: dict[str, list[str]]):
    filtered_df = df.copy()
    for column, values in filters.items():
        if "Todos" in values:
            continue
        filtered_df = filtered_df[filtered_df[column].isin(values)]

        # [ 1, 2, 3, 4] -> [TRUE, FALSE, TRUE, FALSE] -> [1, 3]
        # [1, 3] -> [False, TRUE, ] -> [3]
        # True and True -> True
        # False and True -> False

    return filtered_df


def exclusive_numerical_search(df, filters: dict[str, list[float]]):
    """Performs an exclusive search on a dataframe
    Args:
        df (pd.DataFrame): Dataframe to search
        filters (dict[str, list[float]]): Dictionary of filters with a list of two values min and max
    """
    filtered_df = df.copy()
    for column, values in filters.items():
        filtered_df = filtered_df[filtered_df[column] >= values[0]]
        filtered_df = filtered_df[filtered_df[column] <= values[1]]

        # [ 1, 2, 3, 4] -> [TRUE, FALSE, TRUE, FALSE] -> [1, 3]
        # [1, 3] -> [False, TRUE, ] -> [3]
        # True and True -> True
        # False and True -> False
    return filtered_df


def inclusive_categorical_search(df: pd.DataFrame, filters: dict[str, list[str]]):
    filtered_dfs = []
    if len(filters) == 0:
        return df
    for column, values in filters.items():
        st.write(column)
        if "Todos" in values:
            filtered_dfs.append(df)
            continue
        filtered_dfs.append(df[df[column].isin(values)])
    filtered_df = pd.concat(filtered_dfs)
    filtered_df = filtered_df.drop_duplicates()

    # d1 [1, 2, 3, 4] -> [TRUE, FALSE, TRUE, FALSE] -> [1, 3]
    # d2 [1, 2, 3, 4] -> [FALSE, TRUE, TRUE, FALSE] -> [2, 3]
    # [1, 3] + [2, 3] -> [1, 3, 2, 3] -> [1, 3, 2, 3]
    # [1, 3, 2, 3] -> [1, 3, 2]

    return filtered_df


def inclusive_numerical_search(df: pd.DataFrame, filters: dict[str, list[float]]):
    filtered_dfs = []
    if len(filters) == 0:
        return df
    for column, values in filters.items():
        column = get_option_value(column)
        temp_df = df.copy()
        temp_df = temp_df[temp_df[column] >= values[0]]
        temp_df = temp_df[temp_df[column] <= values[1]]
        filtered_dfs.append(temp_df)
    filtered_df = pd.concat(filtered_dfs)
    filtered_df = filtered_df.drop_duplicates()

    # d1 [1, 2, 3, 4] -> [TRUE, FALSE, TRUE, FALSE] -> [1, 3]
    # d2 [1, 2, 3, 4] -> [FALSE, TRUE, TRUE, FALSE] -> [2, 3]
    # [1, 3] + [2, 3] -> [1, 3, 2, 3] -> [1, 3, 2, 3]
    # [1, 3, 2, 3] -> [1, 3, 2]

    return filtered_df


# CONSTANTS
CATEGORICAL_COLUMNS = {
    "Titular": "titular",
    # "Título": "titulo",
    "Uso amparado": "uso_amparado",
    # "Anotaciones marginales": "anotaciones_marginales",
    # "Tipo de anexo": "tipo_de_anexo",
    # "Estado": "estado",
    "Municipio": "municipio",
    # "Región hidrológica": "region_hidrologica",
    # "Cuenca": "cuenca",
    "Acuífero": "acuifero",
    # "Acuifero homologado": "acuifero_homologado",
}

NUMERIC_COLUMNS = {
    # "Volumen total de aguas nacionales": "volumen_total_de_aguas_nacionales",
    # "Volumen total de aguas superficiales": "volumen_total_de_aguas_superficiales",
    # "Volumen total de aguas subterráneas": "volumen_total_de_aguas_subterraneas",
    # "Volumen total de descargas": "volumen_total_de_descargas",
    # "Número de descargas en el título": "anexos_descargas",
    # "Número de tomas subtarráneas en el título": "anexos_subterraneos",
    # "Número de tomas superficiales en el título": "anexos_superficiales",
    # "Número de tomas en zonas federales en el título": "anexos_zonas_federales",
    "Volumen de extracción": "volumen",
    # "Superficie": "superficie",
    # "Volumen de descarga diario": "volumen_de_descarga_diario",
    "Volumen de descarga anual": "volumen_de_descarga_anual",
}


def get_option_value(key):
    if key in CATEGORICAL_COLUMNS.keys():
        return CATEGORICAL_COLUMNS[key]
    elif key in NUMERIC_COLUMNS.keys():
        return NUMERIC_COLUMNS[key]
    else:
        return None


# PAGE CONFIG
st.set_page_config(
    page_title="Explorador de datos REPDA Guanajuato",
    page_icon="💧",
    layout="wide",
)

_, cent_co, _ = st.columns(3)
with cent_co:
    st.image("media/logo-poplab.png", width=500, use_column_width=True)


st.title("Explorador de datos REPDA Guanajuato")
st.subheader("Datos de concesiones de aguas nacionales en Guanajuato")
st.markdown("""
<iframe src="https://poplab.mx/dataCenter/pozos/counter"
  style="width: 100%; height: 1px; border: none; position: absolute; top: 0; left: 0; right: 0; bottom: 0;"
></iframe>

<div style="text-align: justify;max-width: 800px;">

Este explorador permite filtrar y examinar los datos de concesiones de aguas nacionales en Guanajuato.
Los datos han sido obtenidos del Registro Público de Derechos de Agua (REPDA) y han sido procesados para su visualización y análisis.

#### Instrucciones

En el menú de la izquierda, se podran realizar filtros categóricos y numéricos para explorar los datos.

Arriba del mapa se podrá seleccionar una columna para colorear el mapa. También se podrán seleccionar las columnas para visualizar al pasar el cursor sobre los puntos del mapa.

**Nota:** Algunos datos no cuentan con coordenadas, por lo que se les asignó latitud y longitud 1.

</div>
""", unsafe_allow_html=True
)

st.sidebar.header("Filtros")

# DATA LOADING


@st.cache_data
def load_complete_data():
    df = pd.read_json("data.json")
    df = df.drop_duplicates()
    return df


options = ["Explorador de datos filtrados", "Explorador de datos completos del REPDA"]


df = load_complete_data()
# run_df_diagnostics(df, "Datos iniciales")

# color = st.sidebar.selectbox(
#     "Selecciona una columna para colorear el mapa", list(CATEGORICAL_COLUMNS.keys()), index=0
# )
# if not color:
#     color = "Estado"

filters = {}

categorical_search_type = "Inclusiva"
st.sidebar.subheader("Categorías")
active_filters = st.sidebar.multiselect(
    "Filtros activos",
    list(CATEGORICAL_COLUMNS.keys()),
)

for column_name in active_filters:
    column = get_option_value(column_name)
    st.sidebar.write(f"Selecciona {column}")
    options = df[column].unique().tolist()
    if column == "estado":
        options = sorted(options)
    options.insert(0, "Todos")

    values = st.sidebar.multiselect(
        column,
        options,
        default=["Todos"],
    )
    filters[column] = values
    st.sidebar.divider()

if categorical_search_type == "Inclusiva":
    if len(filters) > 0:
        filtered_df = inclusive_categorical_search(df, filters)
    else:
        filtered_df = df
else:
    filtered_df = exclusive_categorical_search(df, filters)

st.sidebar.subheader("Volúmenes")
numerical_search_type = "Exclusiva"
active_filters = st.sidebar.multiselect(
    "Filtros activos",
    list(NUMERIC_COLUMNS.keys()),
)

numerical_filters = {}

for column_name in active_filters:
    column = get_option_value(column_name)
    range_type = st.sidebar.radio(f"Selecciona {column}", ["Mayor que", "Menor que", "Entre"])
    min = filtered_df[column].min()
    max = filtered_df[column].max()
    if range_type == "Mayor que":
        min_value = st.sidebar.slider(f"Valor mínimo para {column}", min_value=min, max_value=max, value=min)
        max_value = max

    elif range_type == "Menor que":
        min_value = min
        max_value = st.sidebar.slider(f"Valor máximo para {column}", min_value=min, max_value=max, value=max)
    else:
        min_value = st.sidebar.slider(f"Valor mínimo para {column}", min_value=min, max_value=max, value=min)
        max_value = st.sidebar.slider(f"Valor máximo para {column}", min_value=min, max_value=max, value=max)
    numerical_filters[column] = [min_value, max_value]
    st.sidebar.divider()

if numerical_search_type == "Inclusiva":
    if len(numerical_filters) > 0:
        filtered_df = inclusive_numerical_search(filtered_df, numerical_filters)
    else:
        filtered_df = filtered_df
else:
    filtered_df = exclusive_numerical_search(filtered_df, numerical_filters)


color_options = list(CATEGORICAL_COLUMNS.keys()) + list(NUMERIC_COLUMNS.keys())
hover_options = color_options.copy() + ["lat", "lon"]
color_options.remove("Titular")
# color_options.remove("Título")

color = st.selectbox("Selecciona una columna para colorear el mapa", color_options, index=2)

hover = st.multiselect(
    "Selecciona columnas para visualizar al pasar el cursor sobre los puntos del mapa",
    hover_options,
    default=["lat", "lon", "Titular"],
)

# st.plotly_chart(px.colors.qualitative.swatches())

# st.plotly_chart(px.colors.sequential.swatches())

fig = px.scatter_mapbox(
    filtered_df,
    lat="lat",
    lon="lon",
    # color=CATEGORICAL_COLUMNS[color],
    color=get_option_value(color),
    width=1000,
    height=600,
    hover_name="titulo",
    hover_data=map(get_option_value, hover),
    mapbox_style="carto-positron",
    color_continuous_scale=px.colors.sequential.Reds,
    color_discrete_sequence=px.colors.qualitative.Dark24,
    center={"lat": 23.634501, "lon": -102.552784},
    zoom=4,
)

fig.update_traces(marker=dict(size=8, opacity=0.4))

st.plotly_chart(fig)
# st.write("Algunos datos no cuentan con coordenadas, por lo que se les asignó latitud y longitud 1")
st.dataframe(df)

st.download_button(
    label="Descargar datos",
    data=df.to_csv().encode("utf-8"),
    file_name="data.csv",
    mime="text/csv",
)
