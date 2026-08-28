"""
Match performance calculations.

Two sources with different grain:
  - appearances: one row per player and match, with minutes and contributions.
  - goals: one row per goal, covering the whole league, with minute and scorer.

In the goals table, 'equipo_id' identifies who scored and 'rival_id' who
conceded. That makes both attacking and defensive patterns computable for any
team in the league from a single table.
"""

import pandas as pd

from src import config, squad as sq


# ============================================================
# PARTICIPATION
# ============================================================

def preparar_appearances(appearances: pd.DataFrame, matches: pd.DataFrame,
                         squad: pd.DataFrame, equipo_id: int
                         ) -> tuple[pd.DataFrame, dict]:
    """Attach match context, derive minutes played and validate.

    Minutes are always computed from entry and exit, never read from a stored
    column: a manually maintained total drifts out of step with the times it
    is supposed to summarise.

    Squad members who were named but did not play are recorded with zero
    minutes and excluded here. Counting them would inflate appearances and
    depress the minutes-per-match figure.
    """
    issues = {}

    if appearances.empty or matches.empty:
        return pd.DataFrame(), {"sin_datos": True}

    propios = matches[(matches["local_id"] == equipo_id) |
                      (matches["visita_id"] == equipo_id)].copy()
    propios["es_local"] = propios["local_id"] == equipo_id
    propios["rival_id"] = propios["visita_id"].where(
        propios["es_local"], propios["local_id"])

    a = appearances.merge(
        propios[["id", "jornada", "fecha", "rival_id", "es_local"]],
        left_on="partido_id", right_on="id", how="inner",
        suffixes=("", "_partido"))

    incoherentes = int((a["min_sale"] < a["min_entra"]).sum())
    if incoherentes:
        issues["salida_antes_de_entrada"] = incoherentes

    a["minutos"] = (a["min_sale"] - a["min_entra"]).clip(lower=0)

    largos = int((a["minutos"] > config.MINUTOS_MAX).sum())
    if largos:
        issues["minutos_excesivos"] = largos

    sin_jugar = a["minutos"] == 0
    if sin_jugar.any():
        issues["convocadas_sin_minutos"] = int(sin_jugar.sum())
        a = a[~sin_jugar].copy()

    a, huerfanos = sq.enriquecer(a, squad)
    if huerfanos:
        issues["dorsales_desconocidos"] = huerfanos

    return a.reset_index(drop=True), issues


def resumen_jugadoras(a: pd.DataFrame, goals: pd.DataFrame,
                      equipo_id: int) -> pd.DataFrame:
    """Accumulated participation per player, with a team total row.

    In the total row, 'PJ' is the number of matches the team played, not the
    column sum: adding it up would count every match once per player fielded.
    """
    if a.empty:
        return pd.DataFrame()

    goles = (goals[goals["equipo_id"] == equipo_id]
             .groupby("dorsal").size().rename("Goles")
             if not goals.empty else pd.Series(dtype=int, name="Goles"))

    res = (a.groupby(["posicion", "jugadora", "dorsal"])
            .agg(**{"PJ":        ("partido_id", "nunique"),
                    "Titular":   ("titular", "sum"),
                    "Min. tot.": ("minutos", "sum"),
                    "Asist.":    ("asistencias", "sum"),
                    "TA":        ("amarillas", "sum"),
                    "TR":        ("rojas", "sum")})
            .reset_index())

    res["Goles"] = res["dorsal"].map(goles).fillna(0).astype(int)
    res["Titular"] = res["Titular"].astype(int)
    res["Min. tot."] = res["Min. tot."].astype(int)
    res["Min./partido"] = (res["Min. tot."] / res["PJ"]).round(2).map(
        lambda x: f"{x:.2f}" if pd.notna(x) else "—")

    res = res[["posicion", "jugadora", "PJ", "Titular", "Min. tot.",
               "Min./partido", "Goles", "Asist.", "TA", "TR"]]

    res["posicion"] = sq.ordenar_posiciones(res["posicion"])
    res = (res.sort_values(["posicion", "Min. tot."], ascending=[True, False])
              .rename(columns={"posicion": "Posición", "jugadora": "Jugadora"}))

    total = pd.DataFrame([{
        "Posición": "", "Jugadora": "TOTAL EQUIPO",
        "PJ": int(a["partido_id"].nunique()),
        "Titular": "—",
        "Min. tot.": int(res["Min. tot."].sum()),
        "Min./partido": "—",
        "Goles": int(res["Goles"].sum()),
        "Asist.": int(res["Asist."].sum()),
        "TA": int(res["TA"].sum()),
        "TR": int(res["TR"].sum()),
    }])

    return pd.concat([res, total], ignore_index=True)


# ============================================================
# GOALS
# ============================================================

def preparar_goals(goals: pd.DataFrame, squad: pd.DataFrame,
                   equipo_id: int) -> tuple[pd.DataFrame, dict]:
    """Assign each goal to a match phase and resolve the scorer.

    'goleadora' holds the short name for the team's own goals and the bare
    shirt number for everyone else's: there is no opposition squad list to
    translate against, and inventing one would be worse than showing a number.
    """
    issues = {}
    g = goals.copy()

    if g.empty:
        return g, {"sin_datos": True}

    fuera = g["minuto"].notna() & ~g["minuto"].between(1, 90)
    if fuera.any():
        issues["minutos_fuera_de_rango"] = int(fuera.sum())
    g = g[g["minuto"].between(1, 90)].copy()

    if g.empty:
        return g, issues

    nombres = sq.mapa_nombres(squad)
    es_propio = g["equipo_id"] == equipo_id

    g["goleadora"] = g["dorsal"].astype(str)
    g.loc[es_propio, "goleadora"] = (
        g.loc[es_propio, "dorsal"].map(nombres)
         .fillna(g.loc[es_propio, "dorsal"].astype(str)))

    sin_resolver = sorted(
        g.loc[es_propio & ~g["dorsal"].isin(nombres), "dorsal"].unique())
    if sin_resolver:
        issues["dorsales_goleadoras_desconocidos"] = sin_resolver

    g["tramo"] = pd.cut(g["minuto"], bins=config.CORTES_TRAMOS,
                        labels=config.ETIQ_TRAMOS, right=True)

    return g.reset_index(drop=True), issues


def partidos_disputados(matches: pd.DataFrame, equipo_id: int,
                        hasta: pd.Timestamp = None) -> int:
    """Matches played by a team.

    Taken from the fixture list rather than the goals table: a goalless draw
    produces no goal rows, and using goals as the denominator would inflate
    every per-match average.
    """
    if matches.empty:
        return 0
    m = matches[(matches["local_id"] == equipo_id) |
                (matches["visita_id"] == equipo_id)]
    if hasta is not None:
        m = m[m["fecha"] <= hasta]
    return int(len(m))


def conteo_tramos(g: pd.DataFrame, equipo_id: int
                  ) -> tuple[pd.Series, pd.Series]:
    """Goals scored and conceded by phase, for any team in the league."""
    vacio = pd.Series(0, index=config.ETIQ_TRAMOS)
    if g.empty:
        return vacio.copy(), vacio.copy()

    cf = (g[g["equipo_id"] == equipo_id]["tramo"]
          .value_counts().reindex(config.ETIQ_TRAMOS, fill_value=0))
    cc = (g[g["rival_id"] == equipo_id]["tramo"]
          .value_counts().reindex(config.ETIQ_TRAMOS, fill_value=0))
    return cf, cc


def concentracion(conteo: pd.Series) -> str:
    """Phase with most goals. Returns all tied phases rather than picking one
    arbitrarily, which matters when few matches have been played."""
    if conteo.sum() == 0:
        return "—"
    top = conteo.max()
    tramos = [t for t, v in conteo.items() if v == top]
    return f"{' / '.join(tramos)} ({int(top)})"


def resumen_goles(cf: pd.Series, cc: pd.Series, n_partidos: int) -> pd.DataFrame:
    """Attacking and defensive indicators by phase."""
    n = max(n_partidos, 1)
    return pd.DataFrame([
        {"Indicador": "Partidos disputados",           "Valor": n_partidos},
        {"Indicador": "Goles a favor",                 "Valor": int(cf.sum())},
        {"Indicador": "Media goles a favor/partido",   "Valor": f"{cf.sum()/n:.2f}"},
        {"Indicador": "Tramo de mayor concentración (a favor)",
         "Valor": concentracion(cf)},
        {"Indicador": "Goles en contra",               "Valor": int(cc.sum())},
        {"Indicador": "Media goles en contra/partido", "Valor": f"{cc.sum()/n:.2f}"},
        {"Indicador": "Tramo de mayor concentración (en contra)",
         "Valor": concentracion(cc)},
        {"Indicador": "Diferencia de goles",
         "Valor": f"{int(cf.sum() - cc.sum()):+d}"},
    ])


def clasificacion(matches: pd.DataFrame, nombres: dict) -> pd.DataFrame:
    """League table derived from the fixture results."""
    if matches.empty:
        return pd.DataFrame()

    filas = {eq: dict(PJ=0, G=0, E=0, P=0, GF=0, GC=0, Pts=0) for eq in nombres}

    for _, m in matches.iterrows():
        l, v = m["local_id"], m["visita_id"]
        gl, gv = int(m["goles_local"]), int(m["goles_visita"])
        for eq, marcados, encajados in ((l, gl, gv), (v, gv, gl)):
            f = filas[eq]
            f["PJ"] += 1
            f["GF"] += marcados
            f["GC"] += encajados
            if marcados > encajados:
                f["G"] += 1; f["Pts"] += 3
            elif marcados == encajados:
                f["E"] += 1; f["Pts"] += 1
            else:
                f["P"] += 1

    t = pd.DataFrame([{"Equipo": nombres[eq], **f} for eq, f in filas.items()])
    t["DG"] = t["GF"] - t["GC"]
    t = (t.sort_values(["Pts", "DG", "GF"], ascending=False)
           .reset_index(drop=True))
    t.insert(0, "Pos", range(1, len(t) + 1))

    return t[["Pos", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "DG", "Pts"]]
