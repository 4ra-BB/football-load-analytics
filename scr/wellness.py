"""
Wellness calculations.

Five items on a 1-5 scale, all pointing the same way: 1 is the best possible
state and 5 the worst. The Hooper Index is therefore the plain sum of sleep,
fatigue, muscle soreness and stress, with no inversion — the single most common
error when reproducing this index from positively-worded questionnaires.

This module only calculates. It takes DataFrames and returns DataFrames, never
prints and never plots, which is what allows the same functions to serve both
the interactive app and the PDF reports.
"""

import pandas as pd

from src import config, squad as sq


def preparar(wellness: pd.DataFrame, squad: pd.DataFrame
             ) -> tuple[pd.DataFrame, dict]:
    """Clean, compute indices and attach player identity.

    Returns (DataFrame, issues), where issues collects anything worth
    reporting to the user rather than swallowing.
    """
    issues = {}
    w = wellness.copy()

    sin_fecha = int(w["fecha"].isna().sum())
    if sin_fecha:
        issues["fechas_ilegibles"] = sin_fecha
        w = w.dropna(subset=["fecha"])

    # min_count guards against a partial response producing a plausible-looking
    # index built from fewer than four items.
    w["hooper"] = w[config.ITEMS_HOOPER].sum(
        axis=1, min_count=len(config.ITEMS_HOOPER))
    w["wellness"] = w[config.ITEMS_WELLNESS].mean(axis=1)

    w, huerfanos = sq.enriquecer(w, squad)
    if huerfanos:
        issues["dorsales_desconocidos"] = huerfanos

    dups = int(w.duplicated(subset=["dorsal", "fecha"]).sum())
    if dups:
        issues["duplicados"] = dups
        w = (w.sort_values("fecha")
               .drop_duplicates(subset=["dorsal", "fecha"], keep="last"))

    return w.reset_index(drop=True), issues


def ventana(w: pd.DataFrame, fecha_ref: pd.Timestamp, dias: int) -> pd.DataFrame:
    """Records from the last `dias` days."""
    if w.empty:
        return w
    return w[w["fecha"] >= fecha_ref - pd.Timedelta(days=dias)].copy()


def media_equipo(w: pd.DataFrame, variable: str = "hooper") -> pd.Series:
    """Daily team mean, used as the reference line on every chart."""
    if w.empty:
        return pd.Series(dtype=float)
    return w.groupby("fecha")[variable].mean()


def tabla_promedios(w: pd.DataFrame) -> pd.DataFrame:
    """Per-player averages of each item and of the Hooper Index.

    Sorted by Hooper descending within each position, so whoever needs
    attention appears first. 'Registros' shows how many responses each average
    rests on: a mean over two answers is not comparable to one over eighteen,
    and without that column the table invites exactly that comparison.
    """
    if w.empty:
        return pd.DataFrame()

    etiquetas = [(v, config.ETIQUETAS_ITEMS[v]) for v in config.ITEMS_WELLNESS]
    etiquetas.append(("hooper", "Índice Hooper"))

    t = (w.groupby(["posicion", "jugadora"])
           .agg(**{et: (v, "mean") for v, et in etiquetas},
                **{"Registros": ("fecha", "count")})
           .round(2).reset_index())

    t["posicion"] = sq.ordenar_posiciones(t["posicion"])
    t = (t.sort_values(["posicion", "Índice Hooper"], ascending=[True, False])
           .rename(columns={"posicion": "Posición", "jugadora": "Jugadora"}))

    return t.reset_index(drop=True)


def _racha(grupo: pd.DataFrame) -> int:
    """Consecutive answered days reporting discomfort, counting back from the
    most recent record.

    A day with no response neither breaks the streak nor extends it: absence
    of data is not absence of pain, and treating it as either would misstate
    the evidence.
    """
    n = 0
    for zona in grupo.sort_values("fecha", ascending=False)["zona"]:
        if zona:
            n += 1
        else:
            break
    return n


def molestias(w: pd.DataFrame, w_corta: pd.DataFrame, dias: int
              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detail and summary of discomfort reported within the short window.

    Streaks are computed over the full history rather than the window: a player
    twelve days into the same complaint should read as twelve, not as a figure
    truncated by an arbitrary cutoff.
    """
    if w_corta.empty:
        return pd.DataFrame(), pd.DataFrame()

    con = w_corta[w_corta["zona"] != ""]
    if con.empty:
        return pd.DataFrame(), pd.DataFrame()

    detalle = (con[["jugadora", "posicion", "fecha", "zona", "dolor"]]
               .sort_values(["jugadora", "fecha"], ascending=[True, False])
               .rename(columns={"jugadora": "Jugadora", "posicion": "Posición",
                                "fecha": "Fecha", "zona": "Zona / descripción",
                                "dolor": "Dolor (1-5)"}))
    detalle["Fecha"] = detalle["Fecha"].dt.strftime("%d-%m")

    rachas = (w.groupby("jugadora", group_keys=False)
                .apply(_racha, include_groups=False)
                .rename("Días seguidos"))

    col_resp = f"Días respondidos (de {dias + 1})"
    respondidos = w_corta.groupby("jugadora")["fecha"].nunique().rename(col_resp)

    resumen = (con.groupby("jugadora")
               .agg(**{"Posición": ("posicion", "first"),
                       "Zona más reciente": ("zona", "last"),
                       "Reportes": ("zona", "count")})
               .join(rachas).join(respondidos)
               .sort_values("Días seguidos", ascending=False)
               .reset_index().rename(columns={"jugadora": "Jugadora"}))

    return detalle.reset_index(drop=True), resumen


def alertas_dia(w: pd.DataFrame, fecha: pd.Timestamp
                ) -> tuple[list, pd.DataFrame]:
    """Players in the alert band and discomfort reported on a given date."""
    if w.empty:
        return [], pd.DataFrame()

    dia = w[w["fecha"] == fecha]
    if dia.empty:
        return [], pd.DataFrame()

    alerta = sorted(dia.loc[dia["hooper"] >= config.HOOPER_ALERTA, "jugadora"])

    molestia = dia[dia["zona"] != ""]
    if not molestia.empty:
        molestia = (molestia[["jugadora", "posicion", "zona", "dolor"]]
                    .rename(columns={"jugadora": "Jugadora",
                                     "posicion": "Posición",
                                     "zona": "Zona / descripción",
                                     "dolor": "Dolor (1-5)"})
                    .reset_index(drop=True))

    return alerta, molestia
