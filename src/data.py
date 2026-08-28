"""
Data loading.

The public demo reads from CSV files committed to the repository, so it needs
no credentials and starts instantly. The production version of this tool reads
the same tables from a database; because every calculation module works on
DataFrames with these column names, swapping the source touches only this file.
"""

import pandas as pd
import streamlit as st

from src import config


def _leer(clave: str) -> pd.DataFrame:
    """Read one CSV and check that the expected columns are present."""
    ruta = config.DATA_DIR / config.FICHEROS[clave]
    if not ruta.exists():
        raise FileNotFoundError(
            f"Missing data file: {ruta}. "
            f"Export it from the database into data/ before running the app."
        )

    df = pd.read_csv(ruta)
    df.columns = [c.strip() for c in df.columns]

    faltan = [c for c in config.COLUMNAS[clave] if c not in df.columns]
    if faltan:
        raise KeyError(
            f"'{clave}' is missing columns {faltan}. "
            f"Present: {df.columns.tolist()}"
        )
    return df


def _normalizar(clave: str, df: pd.DataFrame) -> pd.DataFrame:
    """Cast dates, numbers and booleans, and normalise the shirt number.

    Shirt numbers arrive as integers here, but are handled as strings
    throughout the app: they are identifiers, not quantities, and pandas will
    happily turn a column of them into floats the moment a merge misses.
    """
    d = df.copy()

    if "fecha" in d.columns:
        d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce").dt.normalize()

    if "dorsal" in d.columns:
        d["dorsal"] = (d["dorsal"].astype("Int64").astype(str)
                       .replace("<NA>", pd.NA))

    for col in ("titular", "activa", "es_propio"):
        if col in d.columns:
            d[col] = (d[col].astype(str).str.strip().str.lower()
                      .isin(["true", "t", "1", "sí", "si", "yes"]))

    enteros = ["min_entra", "min_sale", "asistencias", "amarillas", "rojas",
               "minuto", "rpe", "jornada", "goles_local", "goles_visita",
               *config.ITEMS_WELLNESS]
    for col in enteros:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce")

    for col in ("zona", "nombre", "nombre_corto", "posicion"):
        if col in d.columns:
            d[col] = (d[col].astype(str).str.strip()
                      .replace({"nan": "", "None": "", "<NA>": ""}))

    return d


@st.cache_data(show_spinner="Cargando datos…")
def cargar_todo() -> dict:
    """Load and normalise every table. Returns {key: DataFrame}."""
    return {clave: _normalizar(clave, _leer(clave))
            for clave in config.FICHEROS}


def nombre_equipos(teams: pd.DataFrame) -> dict:
    """{team id: name}, for resolving foreign keys into readable labels."""
    return dict(zip(teams["id"], teams["nombre"]))


def id_equipo_propio(teams: pd.DataFrame) -> int:
    """Id of the team the tool belongs to."""
    propios = teams.loc[teams["es_propio"], "id"]
    if propios.empty:
        raise ValueError("No team is flagged as es_propio in teams.csv")
    return int(propios.iloc[0])
