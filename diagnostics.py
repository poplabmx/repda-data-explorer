import pandas as pd
import streamlit as st


def run_df_diagnostics(df: pd.DataFrame, name: str = 'df'):
    show = st.checkbox(f'Mostrar diagnóstico de {name}')
    if show:
        expander = st.expander(f'Diagnóstico de {name}')
        expander.write(f'Filas: {df.shape[0]}')
        expander.write(f'Columnas: {df.shape[1]}')
        expander.write('Columnas')
        expander.write(df.columns.tolist())
        expander.write('Tipos de datos')
        expander.write(df.dtypes)
        expander.write('Descripción')
        expander.write(df.describe())
        expander.write('Head (5)')
        expander.write(df.head())
        expander.write('Tail (5)')
        expander.write(df.tail())
    
