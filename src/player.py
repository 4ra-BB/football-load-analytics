"""
Individual player view.

Pulls together everything recorded about one player: internal load, perceived
exertion, match participation and attacking contribution. It exists because
the position grids answer "who needs attention" but not "what is going on with
this specific player", which is the next question a coach asks.
"""

import pandas as pd

from src import config


def datos(dorsal: str, squad: pd.DataFrame) -> dict | None:
    """Basic details from the squad list."""
    fila = squad[squad["dorsal"] == str(dorsal)]
    if fila.empty:
        return None
    r = fila.iloc[0]
    return {"dorsal": r["dorsal"], "nombre": r["nombre"],
            "nombre_corto": r["nombre_corto"], "posicion": r["posicion"]}


def opciones_selector(squad: pd.DataFrame) -> dict:
    """{label: shirt number} for the player picker.

    The label carries number, name and position so that typing any of the
    three filters the list — a search box in everything but name.
    """
    orden = {p: i for i, p in enumerate(config.ORDEN_POS)}
    s = squad.copy()
    s["_orden"] = s["posicion"].map(orden).fillna(99)
    s["_num"] = pd.to_numeric(s["dorsal"], errors="coerce")
    s = s.sort_values(["_orden", "_num"])

    return {f"{r['dorsal']} · {r['nombre_corto']} ({r['posicion']})": r["dorsal"]
            for _, r in s.iterrows()}


def _en_ventana(df: pd.DataFrame, dorsal: str, fecha_ref: pd.Timestamp,
                dias: int) -> pd.DataFrame:
    if df.empty:
        return df
    sub = df[df["dorsal"] == str(dorsal)]
    return sub[sub["fecha"] >= fecha_ref - pd.Timedelta(days=dias)].sort_values("fecha")


def series(dorsal: str, w: pd.DataFrame, r: pd.DataFrame,
           fecha_ref: pd.Timestamp, dias: int) -> dict:
    """Player series plus team means, so the chart can show both."""
    w_jug = _en_ventana(w, dorsal, fecha_ref, dias)
    r_jug = _en_ventana(r, dorsal, fecha_ref, dias)

    corte = fecha_ref - pd.Timedelta(days=dias)
    w_v = w[w["fecha"] >= corte] if not w.empty else w
    r_v = r[r["fecha"] >= corte] if not r.empty else r

    return {
        "wellness": w_jug,
        "rpe": r_jug,
        "media_hooper": (w_v.groupby("fecha")["hooper"].mean()
                         if not w_v.empty else pd.Series(dtype=float)),
        "media_rpe": (r_v.groupby("fecha")["rpe"].mean()
                      if not r_v.empty else pd.Series(dtype=float)),
    }


def indicadores(dorsal: str, nombre_corto: str, w: pd.DataFrame,
                r: pd.DataFrame, a: pd.DataFrame, g: pd.DataFrame,
                equipo_id: int, fecha_ref: pd.Timestamp,
                dias: int) -> pd.DataFrame:
    """Accumulated indicators for one player.

    Load figures are restricted to the selected window; match figures are
    season totals, which is how they are normally read.
    """
    filas = []

    w_jug = _en_ventana(w, dorsal, fecha_ref, dias)
    if not w_jug.empty:
        filas += [
            (f"Registros de wellness ({dias} días)", len(w_jug)),
            ("Índice Hooper medio", f"{w_jug['hooper'].mean():.1f}"),
            ("Índice Hooper máximo", f"{w_jug['hooper'].max():.0f}"),
            (f"Días en zona de alerta (≥{config.HOOPER_ALERTA})",
             int((w_jug["hooper"] >= config.HOOPER_ALERTA).sum())),
            ("Wellness promedio", f"{w_jug['wellness'].mean():.2f}"),
            ("Días con molestia reportada", int((w_jug["zona"] != "").sum())),
        ]

    r_jug = _en_ventana(r, dorsal, fecha_ref, dias)
    if not r_jug.empty:
        filas += [
            (f"Sesiones con RPE ({dias} días)", len(r_jug)),
            ("RPE medio", f"{r_jug['rpe'].mean():.1f}"),
            ("RPE máximo", f"{r_jug['rpe'].max():.0f}"),
            (f"Sesiones exigentes (≥{config.RPE_ALTO})",
             int((r_jug["rpe"] >= config.RPE_ALTO).sum())),
        ]

    if not a.empty:
        a_jug = a[a["dorsal"] == str(dorsal)]
        if not a_jug.empty:
            pj = int(a_jug["partido_id"].nunique())
            minutos = int(a_jug["minutos"].sum())
            filas += [
                ("Partidos jugados", pj),
                ("Titularidades", int(a_jug["titular"].sum())),
                ("Minutos totales", minutos),
                ("Minutos por partido", f"{minutos / pj:.2f}"),
                ("Asistencias", int(a_jug["asistencias"].sum())),
                ("Tarjetas amarillas", int(a_jug["amarillas"].sum())),
                ("Tarjetas rojas", int(a_jug["rojas"].sum())),
            ]

            if not g.empty:
                goles = g[(g["equipo_id"] == equipo_id) &
                          (g["dorsal"] == str(dorsal))]
                filas.append(("Goles", len(goles)))
                if len(goles):
                    filas += [
                        ("Minutos por gol", f"{minutos / len(goles):.0f}"),
                        ("Minuto medio de sus goles",
                         f"{goles['minuto'].mean():.0f}'"),
                    ]

    if not filas:
        return pd.DataFrame({"Indicador": ["Sin datos registrados"],
                             "Valor": ["—"]})

    return pd.DataFrame(filas, columns=["Indicador", "Valor"])


def molestias(dorsal: str, w: pd.DataFrame, fecha_ref: pd.Timestamp,
              dias: int) -> pd.DataFrame:
    """History of discomfort reported by one player."""
    sub = _en_ventana(w, dorsal, fecha_ref, dias)
    if sub.empty:
        return pd.DataFrame()

    con = sub[sub["zona"] != ""].sort_values("fecha", ascending=False)
    if con.empty:
        return pd.DataFrame()

    out = con[["fecha", "zona", "dolor", "hooper"]].rename(
        columns={"fecha": "Fecha", "zona": "Zona / descripción",
                 "dolor": "Dolor (1-5)", "hooper": "Hooper ese día"})
    out["Fecha"] = out["Fecha"].dt.strftime("%d-%m-%Y")

    return out.reset_index(drop=True)


def partidos_jugadora(dorsal: str, a: pd.DataFrame, g: pd.DataFrame,
                      equipo_id: int, nombres: dict) -> pd.DataFrame:
    """Match-by-match record for one player.

    Reading minutes chronologically is how a drop in participation becomes
    visible — an injury or a loss of trust shows up here before it shows up
    in any average.
    """
    if a.empty:
        return pd.DataFrame()

    sub = a[a["dorsal"] == str(dorsal)].sort_values("fecha")
    if sub.empty:
        return pd.DataFrame()

    goles = (g[(g["equipo_id"] == equipo_id) & (g["dorsal"] == str(dorsal))]
             .groupby("jornada").size() if not g.empty else pd.Series(dtype=int))

    out = pd.DataFrame({
        "Jornada": sub["jornada"].astype(int),
        "Fecha": sub["fecha"].dt.strftime("%d-%m"),
        "Rival": sub["rival_id"].map(nombres),
        "Condición": sub["es_local"].map({True: "Local", False: "Visitante"}),
        "Titular": sub["titular"].map({True: "Sí", False: "No"}),
        "Minutos": sub["minutos"].astype(int),
        "Goles": sub["jornada"].map(goles).fillna(0).astype(int),
        "Asist.": sub["asistencias"].astype(int),
        "TA": sub["amarillas"].astype(int),
        "TR": sub["rojas"].astype(int),
    })

    return out.reset_index(drop=True)
