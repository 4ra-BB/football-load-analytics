"""
Figure generation.

Every function returns a Matplotlib Figure and none of them calls plt.show()
or st.pyplot(). The caller decides whether a figure goes to the screen or into
a PDF, which is what lets the app and the report generator share the same code.
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config


def _eje_temporal(ax, fecha_ref: pd.Timestamp, dias: int):
    """Date axis with margin at both ends, so points at the edges of the
    window stay readable, and no year in the labels — within a 30-day window
    it is noise."""
    ax.set_xlim(fecha_ref - pd.Timedelta(days=dias + 1),
                fecha_ref + pd.Timedelta(days=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=9)


def _sin_datos(ax):
    ax.text(0.5, 0.5, "Sin datos", ha="center", va="center",
            transform=ax.transAxes, color="grey", fontsize=13)


def _leyenda(ax, n_series: int):
    """Only draw a legend when it stays readable."""
    if n_series <= 12:
        ax.legend(fontsize=8, loc="upper left", ncol=2, framealpha=0.9)


# ============================================================
# INTERNAL LOAD
# ============================================================

def matriz_hooper(w: pd.DataFrame, media_eq: pd.Series,
                  fecha_ref: pd.Timestamp, dias: int):
    """Hooper Index by position, in a 2x2 grid.

    Gaps in a line are left visible rather than interpolated: a missing day is
    a missing answer, and smoothing over it would hide a real adherence
    problem behind a plausible-looking curve.
    """
    posiciones = [p for p in config.ORDEN_POS
                  if p in w["posicion"].dropna().unique()]

    fig, axes = plt.subplots(2, 2, figsize=(17, 11))
    axes = axes.flatten()

    for k, ax in enumerate(axes):
        if k >= len(posiciones):
            ax.axis("off")
            continue

        pos = posiciones[k]
        sub = w[w["posicion"] == pos]

        for lo, hi, color, _ in config.HOOPER_BANDAS:
            ax.axhspan(lo, hi, color=color, alpha=0.10, zorder=0)

        if not media_eq.empty:
            ax.plot(media_eq.index, media_eq.values, color=config.COLOR_MEDIA,
                    ls="--", lw=2, alpha=0.85, label="Media equipo", zorder=1)

        for jugadora, g in sub.groupby("jugadora"):
            g = g.sort_values("fecha")
            ax.plot(g["fecha"], g["hooper"], marker="o", ms=6, lw=2,
                    label=jugadora, zorder=2)

        ax.set_ylim(3.5, 20.5)
        ax.set_yticks([4, 8, 13, 20])
        _eje_temporal(ax, fecha_ref, dias)
        ax.set_title(config.NOMBRE_POS.get(pos, pos), fontsize=15, weight="bold")
        ax.set_ylabel("Índice Hooper (↑ peor)", fontsize=10)
        ax.grid(alpha=0.2, ls=":")

        for texto, y, color in [("ALERTA", 17, "#C62828"),
                                ("Vigilar", 11, "#F57F17"),
                                ("Buen estado", 6, "#2E7D32")]:
            ax.text(0.985, y, texto, transform=ax.get_yaxis_transform(),
                    ha="right", va="center", fontsize=8.5, weight="bold",
                    color=color, alpha=0.65)

        n = sub["jugadora"].nunique()
        if n:
            _leyenda(ax, n)
        else:
            _sin_datos(ax)

    fig.suptitle(f"Índice Hooper por posición — últimos {dias} días "
                 f"(hasta {fecha_ref:%d-%m-%Y})", fontsize=18, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


def matriz_rpe(r: pd.DataFrame, media_eq: pd.Series,
               fecha_ref: pd.Timestamp, dias: int):
    """Perceived exertion by position, in a 2x2 grid."""
    posiciones = [p for p in config.ORDEN_POS
                  if p in r["posicion"].dropna().unique()]

    fig, axes = plt.subplots(2, 2, figsize=(17, 11))
    axes = axes.flatten()

    for k, ax in enumerate(axes):
        if k >= len(posiciones):
            ax.axis("off")
            continue

        pos = posiciones[k]
        sub = r[r["posicion"] == pos]

        for lo, hi, color, _ in config.RPE_BANDAS:
            ax.axhspan(lo - 0.5, hi + 0.5, color=color, alpha=0.13, zorder=0)

        if not media_eq.empty:
            ax.plot(media_eq.index, media_eq.values, color=config.COLOR_MEDIA,
                    ls="--", lw=2, alpha=0.85, label="Media equipo", zorder=1)

        for jugadora, g in sub.groupby("jugadora"):
            g = g.sort_values("fecha")
            ax.plot(g["fecha"], g["rpe"], marker="o", ms=6, lw=2,
                    label=jugadora, zorder=2)

        ax.set_ylim(-0.6, 10.6)
        ax.set_yticks([0, 2, 4, 6, 8, 10])
        _eje_temporal(ax, fecha_ref, dias)
        ax.set_title(config.NOMBRE_POS.get(pos, pos), fontsize=15, weight="bold")
        ax.set_ylabel("RPE (↑ más esfuerzo)", fontsize=10)
        ax.grid(alpha=0.2, ls=":")

        for texto, y, color in [("Máximo", 9.5, "#B71C1C"),
                                ("Muy duro", 7.5, "#E65100"),
                                ("Duro", 5.5, "#F57F17"),
                                ("Moderado", 3.5, "#9E9D24"),
                                ("Suave", 1, "#2E7D32")]:
            ax.text(0.985, y, texto, transform=ax.get_yaxis_transform(),
                    ha="right", va="center", fontsize=8.5, weight="bold",
                    color=color, alpha=0.7)

        n = sub["jugadora"].nunique()
        if n:
            _leyenda(ax, n)
        else:
            _sin_datos(ax)

    fig.suptitle(f"Percepción del esfuerzo (RPE) por posición — últimos {dias} "
                 f"días (hasta {fecha_ref:%d-%m-%Y})", fontsize=18, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


# ============================================================
# INDIVIDUAL PLAYER
# ============================================================

def ficha_jugadora(series: dict, nombre: str, fecha_ref: pd.Timestamp,
                   dias: int):
    """Hooper and RPE for one player against the team average.

    Days with reported discomfort are ringed on the Hooper line. Stacking the
    two panels on a shared axis is the point: it makes visible whether rising
    perceived effort and deteriorating wellness move together, which is the
    pattern that precedes an injury.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

    # --- Hooper ---
    ax = axes[0]
    for lo, hi, color, _ in config.HOOPER_BANDAS:
        ax.axhspan(lo, hi, color=color, alpha=0.10, zorder=0)

    w = series["wellness"]
    if not series["media_hooper"].empty:
        ax.plot(series["media_hooper"].index, series["media_hooper"].values,
                color=config.COLOR_MEDIA, ls="--", lw=2, alpha=0.8,
                label="Media equipo", zorder=1)

    if not w.empty:
        ax.plot(w["fecha"], w["hooper"], marker="o", ms=7, lw=2.5,
                color=config.COLOR_JUGADORA, label=nombre, zorder=2)
        molestias = w[w["zona"] != ""]
        if not molestias.empty:
            ax.scatter(molestias["fecha"], molestias["hooper"], s=190,
                       facecolors="none", edgecolors=config.COLOR_CONTRA,
                       lw=2.2, label="Molestia reportada", zorder=3)
    else:
        _sin_datos(ax)

    ax.set_ylim(3.5, 20.5)
    ax.set_yticks([4, 8, 13, 20])
    ax.set_ylabel("Índice Hooper (↑ peor)", fontsize=11)
    ax.set_title("Carga interna", fontsize=13, weight="bold")
    ax.grid(alpha=0.2, ls=":")
    ax.legend(fontsize=9, loc="upper left", framealpha=0.9)

    # --- RPE ---
    ax = axes[1]
    for lo, hi, color, _ in config.RPE_BANDAS:
        ax.axhspan(lo - 0.5, hi + 0.5, color=color, alpha=0.13, zorder=0)

    r = series["rpe"]
    if not series["media_rpe"].empty:
        ax.plot(series["media_rpe"].index, series["media_rpe"].values,
                color=config.COLOR_MEDIA, ls="--", lw=2, alpha=0.8,
                label="Media equipo", zorder=1)

    if not r.empty:
        ax.plot(r["fecha"], r["rpe"], marker="o", ms=7, lw=2.5,
                color=config.COLOR_RPE, label=nombre, zorder=2)
    else:
        _sin_datos(ax)

    ax.set_ylim(-0.6, 10.6)
    ax.set_yticks([0, 2, 4, 6, 8, 10])
    ax.set_ylabel("RPE (↑ más esfuerzo)", fontsize=11)
    ax.set_title("Esfuerzo percibido", fontsize=13, weight="bold")
    ax.grid(alpha=0.2, ls=":")
    ax.legend(fontsize=9, loc="upper left", framealpha=0.9)

    _eje_temporal(ax, fecha_ref, dias)

    fig.suptitle(f"{nombre} — últimos {dias} días (hasta {fecha_ref:%d-%m-%Y})",
                 fontsize=17, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def minutos_jugadora(partidos: pd.DataFrame, nombre: str):
    """Minutes played match by match.

    A drop in participation shows up here long before it moves any average,
    which is why this is a bar chart over the season rather than a summary
    statistic.
    """
    if partidos.empty:
        return figura_vacia(f"Sin partidos registrados para {nombre}")

    fig, ax = plt.subplots(figsize=(13, 4.5))

    colores = [config.COLOR_JUGADORA if t == "Sí" else "#90A4AE"
               for t in partidos["Titular"]]
    ax.bar(partidos["Jornada"], partidos["Minutos"], color=colores,
           edgecolor="white")

    ax.set_ylim(0, 100)
    ax.set_xticks(partidos["Jornada"])
    ax.set_xlabel("Jornada", fontsize=11)
    ax.set_ylabel("Minutos jugados", fontsize=11)
    ax.set_title(f"{nombre} — minutos por partido", fontsize=14, weight="bold")
    ax.grid(axis="y", alpha=0.25, ls=":")
    ax.set_axisbelow(True)

    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=config.COLOR_JUGADORA, label="Titular"),
                       Patch(color="#90A4AE", label="Suplente")],
              fontsize=9, loc="upper right")

    fig.tight_layout()
    return fig


# ============================================================
# GOALS
# ============================================================

def barras_tramos(cf: pd.Series, cc: pd.Series, titulo: str,
                  etiqueta_favor: str = "Goles a favor",
                  etiqueta_contra: str = "Goles en contra"):
    """Goals by match phase.

    The vertical rule separates the two halves. Conceding right after the
    break and fading in the closing minutes are different problems with
    different fixes, and without the split they read as one continuum.
    """
    x = np.arange(len(config.ETIQ_TRAMOS))
    ancho = 0.38

    fig, ax = plt.subplots(figsize=(13, 6.5))
    b1 = ax.bar(x - ancho / 2, cf.values, ancho, label=etiqueta_favor,
                color=config.COLOR_FAVOR, edgecolor="white")
    b2 = ax.bar(x + ancho / 2, cc.values, ancho, label=etiqueta_contra,
                color=config.COLOR_CONTRA, edgecolor="white")

    for barras in (b1, b2):
        for barra in barras:
            altura = barra.get_height()
            if altura > 0:
                ax.text(barra.get_x() + barra.get_width() / 2, altura + 0.08,
                        int(altura), ha="center", va="bottom",
                        fontsize=10, weight="bold")

    ax.axvline(2.5, color="#455A64", ls="--", lw=1.5, alpha=0.6)
    ax.text(2.5, ax.get_ylim()[1] * 0.97, " 2ª parte", fontsize=9,
            color="#455A64", va="top")

    ax.set_xticks(x)
    ax.set_xticklabels(config.ETIQ_TRAMOS, fontsize=11)
    ax.set_xlabel("Tramo del partido (minutos)", fontsize=11)
    ax.set_ylabel("Número de goles", fontsize=11)
    ax.set_title(titulo, fontsize=15, weight="bold", pad=15)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.25, ls=":")
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def contraste_tramos(datos: pd.DataFrame, propio: str, rival: str):
    """Where we score against where they concede.

    Phases where both bars are high are the ones worth preparing for; this is
    the chart that turns two separate distributions into a decision.
    """
    x = np.arange(len(datos))
    ancho = 0.38

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(x - ancho / 2, datos["Marcamos"], ancho,
           label=f"Marca {propio}", color=config.COLOR_FAVOR, edgecolor="white")
    ax.bar(x + ancho / 2, datos["Encajan"], ancho,
           label=f"Encaja {rival}", color="#EF6C00", edgecolor="white")

    ax.axvline(2.5, color="#455A64", ls="--", lw=1.5, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(datos["Tramo"], fontsize=11)
    ax.set_xlabel("Tramo del partido (minutos)", fontsize=11)
    ax.set_ylabel("Número de goles", fontsize=11)
    ax.set_title(f"Dónde marca {propio} frente a dónde encaja {rival}",
                 fontsize=15, weight="bold", pad=15)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.25, ls=":")
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def figura_vacia(mensaje: str, titulo: str = ""):
    """Placeholder figure, so a section with no data keeps its place in the
    report instead of silently disappearing."""
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.axis("off")
    ax.text(0.5, 0.5, mensaje, ha="center", va="center",
            fontsize=13, color="#546E7A", transform=ax.transAxes)
    if titulo:
        ax.set_title(titulo, fontsize=14, weight="bold", pad=12)
    fig.tight_layout()
    return fig
