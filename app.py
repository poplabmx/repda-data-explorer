import streamlit as st
import pandas as pd
import geopandas as gpd
from diagnostics import run_df_diagnostics
import plotly.express as px


st.set_page_config(
    page_title="Explorador REPDA",
    page_icon="🧊",
    layout="wide",
)

st.title("Explorador REPDA")


def load_data():
    df = pd.read_json("data.json")
    df = df.drop_duplicates()

    return df


df = load_data()

# run_df_diagnostics(df, "Datos iniciales")


# Filters

st.sidebar.header("Filtros")

categorical_columns = {
    "Titular": "titular",
    "Título": "titulo",
    "Uso amparado": "uso_amparado",
    "Anotaciones marginales": "anotaciones_marginales",
    "Tipo de anexo": "tipo_de_anexo",
    "Estado": "estado",
    "Municipio": "municipio",
    "Región hidrológica": "region_hidrologica",
    "Cuenca": "cuenca",
    "Acuífero": "acuifero",
    "Acuifero homologado": "acuifero_homologado",
}

st.sidebar.write("Filtrado por region via GeoJSON")
st.sidebar.write("Instrucciones: Entra a https://geojson.io/ y dibuja un poligono")
st.sidebar.write("Despues descarga el archivo como GeoJSON y cargalo aqui")
geojson = st.sidebar.file_uploader("Cargar GeoJSON", type=["geojson"])

if geojson is not None:
    gdf = gpd.read_file(geojson)
    df = gpd.GeoDataFrame(df)
    df["geometry"] = df.apply(lambda row: gpd.points_from_xy([row.lon], [row.lat])[0], axis=1)
    df.set_geometry('geometry')
    df = gpd.sjoin(df, gdf, op="within")
    df = df.drop(columns=["geometry", "index_right"])
    df = pd.DataFrame(df)


columns = st.sidebar.multiselect(
    "Selecciona columnas para filtrar por valor",
    categorical_columns.keys(),
)

if columns:
    for column in columns:
        key = categorical_columns[column]
        column_filters = st.sidebar.multiselect(
            f"Selecciona valores para: {column}",
            df[key].unique().tolist(),
        )
        if column_filters:
            df = df[df[key].isin(column_filters)]

numeric_columns = {
    "Volumen total de aguas nacionales": "volumen_total_de_aguas_nacionales",
    "Volumen total de aguas superficiales": "volumen_total_de_aguas_superficiales",
    "Volumen total de aguas subterráneas": "volumen_total_de_aguas_subterraneas",
    "Volumen total de descargas": "volumen_total_de_descargas",
    "Número de descargas en el título": "anexos_descargas",
    "Número de tomas subtarráneas en el título": "anexos_subterraneos",
    "Número de tomas superficiales en el título": "anexos_superficiales",
    "Número de tomas en zonas federales en el título": "anexos_zonas_federales",
    "Volumen individual": "volumen",
    "Superficie": "superficie",
    "Volumen de descarga diario": "volumen_de_descarga_diario",
    "Volumen de descarga anual": "volumen_de_descarga_anual",
}

# Check if there are not None values in columns
numeric_columns_alive = {}
other_category_columns = (
    set(df.columns.tolist())
    - set(numeric_columns.values())
    - set(categorical_columns.values())
)

other_catergory_columns_alive = {}
for key in other_category_columns:
    if df[key].notnull().any():
        other_catergory_columns_alive[key.capitalize().replace("_", " ")] = key

if other_catergory_columns_alive.keys() != []:
    other_category_columns = st.sidebar.multiselect(
        "Selecciona columnas para filtrar",
        other_catergory_columns_alive.keys(),
    )
    if other_category_columns:
        for key in other_category_columns:
            column_name = other_catergory_columns_alive[key]
            column_filters = st.sidebar.multiselect(
                f"Selecciona valores para: {key}",
                df[column_name].unique().tolist(),
            )
            if column_filters:
                df = df[df[column_name].isin(column_filters)]

for key, column_name in numeric_columns.items():
    if df[column_name].notnull().any():
        if df[column_name].min() != df[column_name].max():
            numeric_columns_alive[key] = column_name


if numeric_columns_alive.keys() != []:
    numeric_column_filters = st.sidebar.multiselect(
        "Selecciona columnas para filtrar por rango",
        numeric_columns_alive.keys(),
    )
    if numeric_column_filters:
        for key in numeric_column_filters:
            column_name = numeric_columns_alive[key]
            st.sidebar.write(f"Escoge un rango para: {key}")
            min_value = st.sidebar.slider(
                f"Valor mínimo para: {key}",
                df[column_name].min(),
                df[column_name].max(),
                df[column_name].min(),
            )
            max_value = st.sidebar.slider(
                f"Valor máximo para: {key}",
                df[column_name].min(),
                df[column_name].max(),
                df[column_name].max(),
            )
            # drop rows that are NONE for that column

            df = df[(df[column_name] >= min_value) & (df[column_name] <= max_value)]


# run_df_diagnostics(df, "Datos filtrados")


st.header("Mapa")


mapbox = px.scatter_mapbox(
    df,
    lat="lat",
    lon="lon",
    color="tipo_de_anexo",
    hover_name="titular",
    hover_data=[
        "titulo",
        "estado",
        "municipio",
        "region_hidrologica",
        "cuenca",
        "acuifero",
    ],
    color_discrete_sequence=px.colors.qualitative.Vivid,
    zoom=4,
    height=900,
    width=1000,
    center={"lat": 23.634501, "lon": -102.552784},
    mapbox_style="carto-positron",
)
mapbox.update_traces(marker={"size": 8})

st.plotly_chart(mapbox)


st.header("Datos")

st.dataframe(df)

st.download_button(
    label="Descargar datos",
    data=df.to_csv().encode("utf-8"),
    file_name="data.csv",
    mime="text/csv",
)
