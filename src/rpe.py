"""
Perceived exertion calculations.

Borg CR10 scale: 0 is complete rest, 10 maximal effort. The raw perceived value
is used, without multiplying by session duration, because the source
questionnaire does not capture it.

Unlike the wellness questionnaire, which is answered every day, RPE only exists
on days with a session or a match. A gap in the series means there was no
training, not that someone forgot to answer.
"""

import numpy as np
import pandas as pd

from src import config, squad as sq


def preparar(rpe: pd.DataFrame, squad: pd.DataFrame
             ) -> tuple[pd.DataFrame, dict]:
    """Clean and attach player identity. Returns (DataFrame, issues)."""
    issues = {}
    r = rpe.copy()

    sin_fecha = int(r["fecha"].isna().sum())
    if sin_fecha:
        issues["fechas_ilegibles"] = sin_fecha
        r = r.dropna(subset=["fecha"])

    minimo, maximo = config.ESCALA_RPE
    fuera = r["rpe"].notna() & ~r["rpe"].between(minimo, maximo)
    if fuera.any():
        issues["fuera_de_escala"] = int(fuera.sum())
        r.loc[fuera, "rpe"] = np.nan

    r, huerfanos = sq.enriquecer(r, squad)
    if huerfanos:
        issues["dorsales_desconocidos"] = huerfanos

    dups = int(r.duplicated(subset=["dorsal", "fecha"]).sum())
    if dups:
        issues["duplicados"] = dups
        r = (r.sort_values("fecha")
               .drop_duplicates(subset=["dorsal", "fecha"], keep="last"))

    return r.reset_index(drop=True), issues


def ventana(r: pd.DataFrame, fecha_ref: pd.Timestamp, dias: int) -> pd.DataFrame:
    """Records from the last `dias` days."""
    if r.empty:
        return r
    return r[r["fecha"] >= fecha_ref - pd.Timedelta(days=dias)].copy()


def media_equipo(r: pd.DataFrame) -> pd.Series:
    """Daily team mean, used as the reference line on the chart."""
    if r.empty:
        return pd.Series(dtype=float)
    return r.groupby("fecha")["rpe"].mean()


def tabla_promedios(r: pd.DataFrame) -> pd.DataFrame:
    """Per-player summary of perceived load.

    'Sesiones ≥7' separates what the mean hides: an average of 5.5 can come
    from consistently moderate sessions or from alternating 2 and 9, and those
    are different load profiles calling for different decisions.
    """
    if r.empty:
        return pd.DataFrame()

    t = (r.groupby(["posicion", "jugadora"])
          .agg(**{"RPE medio":   ("rpe", "mean"),
                  "RPE máx.":    ("rpe", "max"),
                  "Sesiones ≥7": ("rpe", lambda s: int((s >= config.RPE_ALTO).sum())),
                  "Sesiones":    ("fecha", "count")})
          .round(2).reset_index())

    t["posicion"] = sq.ordenar_posiciones(t["posicion"])
    t = (t.sort_values(["posicion", "RPE medio"], ascending=[True, False])
           .rename(columns={"posicion": "Posición", "jugadora": "Jugadora"}))

    return t.reset_index(drop=True)


def banda(valor: float) -> tuple | None:
    """Scale band a value falls into: (min, max, colour, label), or None."""
    if pd.isna(valor):
        return None
    for lo, hi, color, etiqueta in config.RPE_BANDAS:
        if lo <= valor <= hi + 0.99:
            return (lo, hi, color, etiqueta)
    return None
