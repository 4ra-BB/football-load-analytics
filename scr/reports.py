"""
PDF report assembly.

Two reports, split by audience and by sensitivity:
  - Load: wellness and RPE. Contains health data, so its distribution should
    be restricted.
  - Match: performance and opposition analysis. Purely sporting data.

Keeping them apart is a data-protection decision, not a formatting one.

Reports are returned as bytes rather than written to disk: Streamlit Cloud has
an ephemeral filesystem, and st.download_button needs bytes anyway.
"""

import io

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from src import (charts, config, matches as mt, opposition as opp,
                 rpe as mod_rpe, tables, wellness as mod_w)


def _a_bytes(figuras: list) -> bytes:
    """Write a list of figures into an in-memory PDF and close them.

    Closing matters here: in a long-running app, figures that are never closed
    accumulate until the process is restarted.
    """
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        for fig in figuras:
            pdf.savefig(fig, bbox_inches="tight")
    for fig in figuras:
        plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


def portada(titulo: str, subtitulo: str, lineas: list = None):
    """Cover page carrying the context of the report."""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")

    ax.text(0.5, 0.72, config.EQUIPO, ha="center", fontsize=26, weight="bold",
            color=config.COLOR_CABECERA, transform=ax.transAxes)
    ax.text(0.5, 0.63, titulo, ha="center", fontsize=19,
            color="#455A64", transform=ax.transAxes)
    ax.text(0.5, 0.56, subtitulo, ha="center", fontsize=13,
            color="#78909C", transform=ax.transAxes)

    for i, linea in enumerate(lineas or []):
        ax.text(0.5, 0.44 - i * 0.05, linea, ha="center", fontsize=11,
                color="#546E7A", transform=ax.transAxes)

    fig.tight_layout()
    return fig


# ============================================================
# LOAD REPORT
# ============================================================

def informe_carga(w: pd.DataFrame, r: pd.DataFrame,
                  fecha_ref: pd.Timestamp) -> bytes:
    """Wellness and RPE. Contains health data."""
    dias_l = config.VENTANA_LARGA
    dias_c = config.VENTANA_CORTA
    figs = [portada(
        "Informe de carga",
        f"Datos hasta {fecha_ref:%d-%m-%Y}",
        [f"Ventana de análisis: {dias_l} días",
         f"Molestias: últimos {dias_c} días",
         "",
         "Contiene datos de salud. Uso restringido al cuerpo técnico."])]

    if not w.empty:
        w_l = mod_w.ventana(w, fecha_ref, dias_l)
        w_c = mod_w.ventana(w, fecha_ref, dias_c)

        figs.append(charts.matriz_hooper(
            w_l, mod_w.media_equipo(w_l), fecha_ref, dias_l))

        figs.append(tables.tabla_a_figura(
            mod_w.tabla_promedios(w_l),
            f"Wellness — promedios últimos {dias_l} días",
            colores=tables.color_wellness,
            anchos=tables.ANCHOS_WELLNESS, fontsize=8.5))

        detalle, resumen = mod_w.molestias(w, w_c, dias_c)
        if detalle.empty:
            figs.append(charts.figura_vacia(
                f"Sin molestias reportadas en los últimos {dias_c} días",
                "Molestias"))
        else:
            figs.append(tables.tabla_a_figura(
                detalle, f"Molestias reportadas — últimos {dias_c} días",
                anchos=tables.ANCHOS_MOLESTIAS,
                wrap_cols=["Zona / descripción"], wrap_ancho=65, fontsize=8.5))
            figs.append(tables.tabla_a_figura(
                resumen, "Resumen de molestias por jugadora",
                anchos=tables.ANCHOS_RESUMEN_MOLESTIAS,
                wrap_cols=["Zona más reciente"], wrap_ancho=55, fontsize=8.5))
    else:
        figs.append(charts.figura_vacia("Sin registros de wellness", "Wellness"))

    if not r.empty:
        r_l = mod_rpe.ventana(r, fecha_ref, dias_l)
        figs.append(charts.matriz_rpe(
            r_l, mod_rpe.media_equipo(r_l), fecha_ref, dias_l))
        figs.append(tables.tabla_a_figura(
            mod_rpe.tabla_promedios(r_l),
            f"RPE — promedios últimos {dias_l} días",
            colores=tables.color_rpe, anchos=tables.ANCHOS_RPE, fontsize=8.5))
    else:
        figs.append(charts.figura_vacia("Sin registros de RPE", "RPE"))

    return _a_bytes(figs)


# ============================================================
# MATCH REPORT
# ============================================================

def informe_partido(a: pd.DataFrame, g: pd.DataFrame, matches: pd.DataFrame,
                    cal: pd.DataFrame, nombres: dict, equipo_id: int,
                    fecha_ref: pd.Timestamp) -> bytes:
    """Squad performance and analysis of the next opponent."""
    proximo = opp.proximo_partido(cal, fecha_ref)
    referencia = proximo or opp.ultimo_partido(cal, fecha_ref)

    if proximo:
        subtitulo = (f"Próximo partido: {proximo['rival']} · "
                     f"{proximo['fecha']:%d-%m-%Y}")
    elif referencia:
        subtitulo = (f"Temporada finalizada · último partido: "
                     f"{referencia['rival']}")
    else:
        subtitulo = "Sin partidos en el calendario"

    figs = [portada("Informe de partido",
                    f"Datos hasta {fecha_ref:%d-%m-%Y}", [subtitulo])]

    # --- Own performance ---
    if not a.empty:
        figs.append(tables.tabla_a_figura(
            mt.resumen_jugadoras(a, g, equipo_id),
            "Rendimiento — resumen por jugadora",
            anchos=tables.ANCHOS_PARTIDOS, fontsize=8.5))
    else:
        figs.append(charts.figura_vacia("Sin partidos registrados",
                                        "Rendimiento por jugadora"))

    if not g.empty:
        n = mt.partidos_disputados(matches, equipo_id, fecha_ref)
        cf, cc = mt.conteo_tramos(g, equipo_id)
        figs.append(charts.barras_tramos(
            cf, cc, f"{config.EQUIPO} — goles por tramo ({n} partidos)"))
        figs.append(tables.tabla_a_figura(
            mt.resumen_goles(cf, cc, n), f"Resumen de goles — {n} partidos",
            anchos=tables.ANCHOS_RESUMEN, fontsize=10))

        figs.append(tables.tabla_a_figura(
            mt.clasificacion(matches[matches["fecha"] <= fecha_ref], nombres),
            "Clasificación", anchos=tables.ANCHOS_CLASIFICACION, fontsize=9))
    else:
        figs.append(charts.figura_vacia("Sin goles registrados", "Goles"))

    # --- Opponent ---
    if referencia and not g.empty:
        rival, rival_id = referencia["rival"], referencia["rival_id"]
        n_rival = mt.partidos_disputados(matches, rival_id, fecha_ref)

        top, total = opp.maximas_goleadoras(g, rival_id)
        if top.empty:
            figs.append(charts.figura_vacia(
                f"Sin goles registrados de {rival}",
                f"Máximas goleadoras — {rival}"))
        else:
            figs.append(tables.tabla_a_figura(
                top, f"Máximas goleadoras — {rival} ({total} goles)",
                anchos=tables.ANCHOS_GOLEADORAS, fontsize=10))

        cfr, ccr = mt.conteo_tramos(g, rival_id)
        figs.append(charts.barras_tramos(
            cfr, ccr, f"{rival} — goles por tramo ({n_rival} partidos)",
            etiqueta_favor=f"Goles de {rival}",
            etiqueta_contra=f"Goles encajados por {rival}"))

        figs.append(tables.tabla_a_figura(
            opp.resumen_rival(g, rival_id, n_rival), f"Resumen — {rival}",
            anchos=tables.ANCHOS_RESUMEN, fontsize=10))

        figs.append(charts.contraste_tramos(
            opp.contraste_tramos(g, equipo_id, rival_id),
            config.EQUIPO, rival))

    return _a_bytes(figs)


def nombre_archivo(tipo: str, fecha_ref: pd.Timestamp) -> str:
    """Suggested download filename."""
    prefijos = {"carga": "Informe_Carga", "partido": "Informe_Partido"}
    return f"{prefijos[tipo]}_{fecha_ref:%Y%m%d}.pdf"
