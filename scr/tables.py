"""
Table rendering and traffic-light colouring.

PDF assembly goes through PdfPages, which only accepts Matplotlib figures, so
tables destined for a report are drawn as figures rather than written as text.
The colouring functions live here so that the on-screen table and the printed
one cannot drift apart.
"""

import textwrap

import matplotlib.pyplot as plt
import pandas as pd

from src import config


# ============================================================
# TRAFFIC LIGHTS
# ============================================================

ITEMS_ETIQUETADOS = list(config.ETIQUETAS_ITEMS.values())


def color_wellness(valor, columna: str) -> str | None:
    """Background colour for the wellness averages table."""
    try:
        v = float(valor)
    except (ValueError, TypeError):
        return None

    if columna == "Índice Hooper":
        if v >= config.HOOPER_ALERTA:
            return config.HOOPER_COLOR_TABLA["alerta"]
        if v >= 9:
            return config.HOOPER_COLOR_TABLA["vigilar"]
        return config.HOOPER_COLOR_TABLA["bueno"]

    if columna in ITEMS_ETIQUETADOS and v >= config.UMBRAL_ITEM:
        return config.HOOPER_COLOR_TABLA["alerta"]

    return None


def color_rpe(valor, columna: str) -> str | None:
    """Background colour for the RPE table, following the scale bands."""
    if columna not in ("RPE medio", "RPE máx."):
        return None
    try:
        v = float(valor)
    except (ValueError, TypeError):
        return None

    for lo, hi, color, _ in config.RPE_BANDAS:
        if lo <= v <= hi + 0.99:
            return color
    return None


def estilo_pantalla(df: pd.DataFrame, columnas: list, funcion_color):
    """Styler for displaying a coloured table in the interface."""
    return (df.style
            .apply(lambda s: [f"background-color: {c}"
                              if (c := funcion_color(v, s.name)) else ""
                              for v in s], subset=columnas)
            .hide(axis="index"))


# ============================================================
# TABLE AS FIGURE
# ============================================================

def tabla_a_figura(df: pd.DataFrame, titulo: str, alto_fila: float = 0.40,
                   fontsize: int = 9, colores=None, anchos: dict = None,
                   wrap_cols: list = None, wrap_ancho: int = 45):
    """Render a DataFrame as a Matplotlib figure.

    colores    : function (value, column) -> background colour or None
    anchos     : {column: relative weight}, for columns holding long text
    wrap_cols  : columns whose contents are wrapped across lines
    wrap_ancho : characters per line before wrapping

    Both the figure height and the individual cell height derive from the row
    count, so a one-row table is not squashed into a sliver and a thirty-row
    one does not overlap itself.
    """
    if df.empty:
        df = pd.DataFrame({"Resultado": ["Sin datos"]})

    d = df.copy().astype(str)

    lineas_max = 1
    if wrap_cols:
        presentes = [c for c in wrap_cols if c in d.columns]
        for c in presentes:
            d[c] = d[c].map(lambda x: "\n".join(textwrap.wrap(x, wrap_ancho)) or x)
        if presentes:
            lineas_max = int(d[presentes].map(lambda x: x.count("\n") + 1).max().max())

    n_filas = len(d) + 1                      # rows plus header
    alto_por_fila = alto_fila * lineas_max

    ancho_fig = max(9, sum((anchos or {}).get(c, 1.6) for c in d.columns))
    alto_fig = n_filas * alto_por_fila + 0.9

    fig, ax = plt.subplots(figsize=(ancho_fig, alto_fig))
    ax.axis("off")

    tabla = ax.table(cellText=d.values, colLabels=d.columns,
                     cellLoc="center", loc="center")
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(fontsize)

    alto_celda = 1.0 / n_filas
    total_ancho = sum((anchos or {}).get(c, 1.0) for c in d.columns)

    for (fila, col), celda in tabla.get_celld().items():
        nombre_col = d.columns[col]
        celda.set_edgecolor("#cccccc")
        celda.set_height(alto_celda)
        if anchos:
            celda.set_width(anchos.get(nombre_col, 1.0) / total_ancho)

        if fila == 0:
            celda.set_facecolor(config.COLOR_CABECERA)
            celda.set_text_props(color="white", weight="bold")
        else:
            if wrap_cols and nombre_col in wrap_cols:
                celda.set_text_props(ha="left", va="center")
            if colores:
                fondo = colores(df.iloc[fila - 1, col], nombre_col)
                if fondo:
                    celda.set_facecolor(fondo)

    ax.set_title(titulo, fontsize=13, weight="bold", pad=14)
    # subplots_adjust rather than tight_layout: with the axis switched off,
    # tight_layout miscalculates the margins and compresses the table.
    fig.subplots_adjust(top=0.82, bottom=0.06, left=0.02, right=0.98)
    return fig


def figura_texto(lineas: list, titulo: str, columna: str = "Jugadora"):
    """Figure from a plain list of lines, for blocks that are not really
    tables."""
    if not lineas:
        lineas = ["Sin registros"]
    return tabla_a_figura(pd.DataFrame({columna: lineas}), titulo,
                          anchos={columna: 4.0})


# ============================================================
# COLUMN WIDTHS
# ============================================================

ANCHOS_WELLNESS = {"Jugadora": 2.6, "Posición": 1.2, "Registros": 1.0}

ANCHOS_MOLESTIAS = {"Jugadora": 2.0, "Posición": 1.1, "Fecha": 0.9,
                    "Zona / descripción": 7.0, "Dolor (1-5)": 1.0}

ANCHOS_RESUMEN_MOLESTIAS = {"Jugadora": 2.0, "Posición": 1.1,
                            "Zona más reciente": 6.0, "Reportes": 1.1,
                            "Días seguidos": 1.4}

ANCHOS_RPE = {"Jugadora": 2.6, "Posición": 1.2, "RPE medio": 1.2,
              "RPE máx.": 1.1, "Sesiones ≥7": 1.3, "Sesiones": 1.1}

ANCHOS_PARTIDOS = {"Jugadora": 2.6, "Posición": 1.2, "PJ": 0.8, "Titular": 1.0,
                   "Min. tot.": 1.2, "Min./partido": 1.4, "Goles": 1.0,
                   "Asist.": 1.0, "TA": 0.7, "TR": 0.7}

ANCHOS_GOLEADORAS = {"Jugadora": 3.0, "Goles": 1.0, "Partidos con gol": 1.8,
                     "Minuto medio": 1.4, "% goles equipo": 1.6}

ANCHOS_RESUMEN = {"Indicador": 4.5, "Valor": 1.8}

ANCHOS_CLASIFICACION = {"Pos": 0.7, "Equipo": 2.5, "PJ": 0.8, "G": 0.7,
                        "E": 0.7, "P": 0.7, "GF": 0.8, "GC": 0.8,
                        "DG": 0.8, "Pts": 0.9}
