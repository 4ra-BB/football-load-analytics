"""
Squad and player identity.

Players are identified by shirt number everywhere in the system. This module
is the single place where that number is resolved into a name and a position,
so that every chart and table can display a readable label without each of
them having to know how the mapping works.
"""

import pandas as pd

from src import config


def preparar(players: pd.DataFrame, equipo_id: int) -> pd.DataFrame:
    """Return the active squad of a team, validated.

    A repeated shirt number would silently duplicate every row that joins
    against it, so it is treated as a fatal error rather than a warning.
    """
    p = players[(players["equipo_id"] == equipo_id)].copy()

    if "activa" in p.columns:
        p = p[p["activa"]]

    p = p[p["nombre_corto"] != ""].dropna(subset=["dorsal"])

    if p.empty:
        raise ValueError(f"No active players found for team {equipo_id}")

    if p["dorsal"].duplicated().any():
        repetidos = sorted(p.loc[p["dorsal"].duplicated(keep=False), "dorsal"])
        raise ValueError(
            f"Duplicate shirt numbers in the squad: {repetidos}. "
            f"Each number must belong to exactly one player."
        )

    return (p[["dorsal", "nombre", "nombre_corto", "posicion"]]
            .sort_values("posicion")
            .reset_index(drop=True))


def posiciones_no_reconocidas(squad: pd.DataFrame) -> list:
    """Positions not listed in config.ORDEN_POS.

    Players in these positions would be dropped from the by-position grids
    without any error being raised, so the interface should flag them.
    """
    return sorted(p for p in squad["posicion"].unique()
                  if p not in config.ORDEN_POS)


def posiciones_presentes(df: pd.DataFrame) -> list:
    """Positions actually present in the data, in pitch order."""
    if df.empty or "posicion" not in df.columns:
        return []
    presentes = set(df["posicion"].dropna())
    return [p for p in config.ORDEN_POS if p in presentes]


def mapa_nombres(squad: pd.DataFrame) -> dict:
    """{shirt number: short name}, for translating standalone columns such as
    the scorer field in the goals table."""
    return dict(zip(squad["dorsal"], squad["nombre_corto"]))


def enriquecer(df: pd.DataFrame, squad: pd.DataFrame
               ) -> tuple[pd.DataFrame, list]:
    """Attach name and position to any table that carries a shirt number.

    'jugadora' holds the short name and is the label used in every chart and
    table downstream.

    Rows whose shirt number is not in the squad are dropped and returned
    separately: showing a raw number in a chart legend is worse than leaving
    it out, but silently discarding records without telling anyone is worse
    still.
    """
    if df.empty:
        return df, []

    d = df.merge(squad, on="dorsal", how="left")

    huerfanos = sorted(
        d.loc[d["nombre_corto"].isna(), "dorsal"].dropna().unique()
    )

    d["jugadora"] = d["nombre_corto"]
    d = d.dropna(subset=["jugadora"]).reset_index(drop=True)

    return d, huerfanos


def ordenar_posiciones(serie: pd.Series) -> pd.Categorical:
    """Make the position column an ordered category, so tables come out in
    pitch order rather than alphabetically."""
    return pd.Categorical(serie, categories=config.ORDEN_POS, ordered=True)


def sin_registro(df: pd.DataFrame, squad: pd.DataFrame,
                 fecha: pd.Timestamp) -> pd.DataFrame:
    """Players with no record on a given date.

    'Días sin responder' separates a one-off omission from someone who has
    dropped out of the routine altogether — two situations that call for very
    different conversations.
    """
    if df.empty:
        faltan = squad.copy()
        faltan["Último registro"] = "Nunca"
        faltan["Días sin responder"] = pd.NA
    else:
        con_registro = set(df.loc[df["fecha"] == fecha, "dorsal"])
        faltan = squad[~squad["dorsal"].isin(con_registro)].copy()

        ultimos = df.groupby("dorsal")["fecha"].max()
        ult = faltan["dorsal"].map(ultimos)
        faltan["Días sin responder"] = (fecha - ult).dt.days.astype("Int64")
        faltan["Último registro"] = ult.dt.strftime("%d-%m-%Y").fillna("Nunca")

    faltan["posicion"] = ordenar_posiciones(faltan["posicion"])

    return (faltan[["dorsal", "nombre_corto", "posicion",
                    "Último registro", "Días sin responder"]]
            .rename(columns={"dorsal": "Dorsal", "nombre_corto": "Jugadora",
                             "posicion": "Posición"})
            .sort_values(["Posición", "Dorsal"])
            .reset_index(drop=True))
