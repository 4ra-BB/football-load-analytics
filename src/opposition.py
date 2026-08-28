"""
Opposition analysis.

The goals table covers every team in the league, so any opponent can be
analysed with the same code that analyses the team's own play. The counting
and summary functions are reused from matches.py by passing a different team
id, rather than duplicated.
"""

import pandas as pd

from src import config, matches as mt


def calendario(matches: pd.DataFrame, equipo_id: int,
               nombres: dict) -> pd.DataFrame:
    """The team's fixture list, with opponent and venue resolved."""
    if matches.empty:
        return pd.DataFrame()

    m = matches[(matches["local_id"] == equipo_id) |
                (matches["visita_id"] == equipo_id)].copy()

    m["es_local"] = m["local_id"] == equipo_id
    m["rival_id"] = m["visita_id"].where(m["es_local"], m["local_id"])
    m["rival"] = m["rival_id"].map(nombres)
    m["condicion"] = m["es_local"].map({True: "Local", False: "Visitante"})

    m["goles_favor"] = m["goles_local"].where(m["es_local"], m["goles_visita"])
    m["goles_contra"] = m["goles_visita"].where(m["es_local"], m["goles_local"])

    return m.sort_values("fecha").reset_index(drop=True)


def proximo_partido(cal: pd.DataFrame, fecha_ref: pd.Timestamp) -> dict | None:
    """First fixture on or after the reference date, or None if the season is
    over."""
    if cal.empty:
        return None

    futuros = cal[cal["fecha"] >= fecha_ref]
    if futuros.empty:
        return None

    p = futuros.iloc[0]
    return {
        "rival": p["rival"],
        "rival_id": int(p["rival_id"]),
        "fecha": p["fecha"],
        "jornada": int(p["jornada"]),
        "condicion": p["condicion"],
        "dias": int((p["fecha"] - fecha_ref).days),
    }


def ultimo_partido(cal: pd.DataFrame, fecha_ref: pd.Timestamp) -> dict | None:
    """Most recent fixture already played.

    Used when the season has finished, so the opposition view still has
    something to show instead of going blank.
    """
    if cal.empty:
        return None

    pasados = cal[cal["fecha"] <= fecha_ref]
    if pasados.empty:
        return None

    p = pasados.iloc[-1]
    return {
        "rival": p["rival"],
        "rival_id": int(p["rival_id"]),
        "fecha": p["fecha"],
        "jornada": int(p["jornada"]),
        "condicion": p["condicion"],
        "dias": int((fecha_ref - p["fecha"]).days),
    }


def equipos_disponibles(teams: pd.DataFrame, excluir: int = None) -> dict:
    """{team id: name} for the opponent selector."""
    t = teams if excluir is None else teams[teams["id"] != excluir]
    return dict(zip(t["id"], t["nombre"]))


def maximas_goleadoras(g: pd.DataFrame, equipo_id: int, top_n: int = 5
                       ) -> tuple[pd.DataFrame, int]:
    """Top scorers of a team, with the share of team goals each accounts for.

    That share carries the tactical reading: a player concentrating a large
    part of the scoring can be marked individually, while a flat distribution
    means the problem is collective.

    Returns (table, total goals scored by the team).
    """
    goles = g[g["equipo_id"] == equipo_id]
    total = len(goles)
    if total == 0:
        return pd.DataFrame(), 0

    top = (goles.groupby("goleadora")
           .agg(**{"Goles": ("minuto", "count"),
                   "Partidos con gol": ("jornada", "nunique"),
                   "Minuto medio": ("minuto", "mean")})
           .sort_values("Goles", ascending=False)
           .head(top_n).reset_index()
           .rename(columns={"goleadora": "Jugadora"}))

    top["Minuto medio"] = top["Minuto medio"].map(lambda x: f"{x:.0f}'")
    top["% goles equipo"] = (top["Goles"] / total * 100).map(lambda x: f"{x:.0f}%")

    return top, total


def resumen_rival(g: pd.DataFrame, equipo_id: int,
                  n_partidos: int) -> pd.DataFrame:
    """Attacking and defensive indicators for an opponent."""
    cf, cc = mt.conteo_tramos(g, equipo_id)
    n = max(n_partidos, 1)

    return pd.DataFrame([
        {"Indicador": "Partidos disputados",           "Valor": n_partidos},
        {"Indicador": "Goles marcados",                "Valor": int(cf.sum())},
        {"Indicador": "Media goles marcados/partido",  "Valor": f"{cf.sum()/n:.2f}"},
        {"Indicador": "Tramo en que más marca",        "Valor": mt.concentracion(cf)},
        {"Indicador": "Goles encajados",               "Valor": int(cc.sum())},
        {"Indicador": "Media goles encajados/partido", "Valor": f"{cc.sum()/n:.2f}"},
        {"Indicador": "Tramo en que más encaja",       "Valor": mt.concentracion(cc)},
        {"Indicador": "Diferencia de goles",
         "Valor": f"{int(cf.sum() - cc.sum()):+d}"},
    ])


def contraste_tramos(g: pd.DataFrame, propio_id: int,
                     rival_id: int) -> pd.DataFrame:
    """Where we score against where they concede, phase by phase.

    This is the comparison that turns two separate charts into a decision: a
    phase where our scoring is strong and their defending is weak is a concrete
    thing to prepare for.
    """
    cf_propio, _ = mt.conteo_tramos(g, propio_id)
    _, cc_rival = mt.conteo_tramos(g, rival_id)

    return pd.DataFrame({
        "Tramo": config.ETIQ_TRAMOS,
        "Marcamos": cf_propio.values,
        "Encajan": cc_rival.values,
    })


def historial(cal: pd.DataFrame, rival_id: int,
              fecha_ref: pd.Timestamp) -> pd.DataFrame:
    """Previous meetings with an opponent this season."""
    if cal.empty:
        return pd.DataFrame()

    previos = cal[(cal["rival_id"] == rival_id) & (cal["fecha"] < fecha_ref)]
    if previos.empty:
        return pd.DataFrame()

    h = previos[["jornada", "fecha", "condicion",
                 "goles_favor", "goles_contra"]].copy()
    h["Resultado"] = (h["goles_favor"].astype(int).astype(str) + "-"
                      + h["goles_contra"].astype(int).astype(str))
    h["Fecha"] = h["fecha"].dt.strftime("%d-%m-%Y")

    return (h[["jornada", "Fecha", "condicion", "Resultado"]]
            .rename(columns={"jornada": "Jornada", "condicion": "Condición"})
            .reset_index(drop=True))
