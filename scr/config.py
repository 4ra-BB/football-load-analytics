"""
Everything that can change without changing the logic — thresholds, colour
bands, time windows and file names — lives here and nowhere else.

Column names are kept in Spanish because that is how they exist in the
production database and in the questionnaires the players actually fill in.
Renaming them for the sake of an English codebase would add a translation
layer that serves nobody.
"""

from datetime import date
from pathlib import Path

# ============================================================
# TEAM
# ============================================================
EQUIPO = "Jaguares"
TEMPORADA = "2026"

ORDEN_POS = ["Por", "Def", "MC", "Del"]
NOMBRE_POS = {"Por": "Porteras", "Def": "Defensas",
              "MC": "Mediocampo", "Del": "Delanteras"}

# The demo runs on a fixed dataset. Anchoring the reference date to the last
# day with records keeps the app populated instead of drifting into an empty
# window as real time moves on.
FECHA_DEMO = date(2026, 8, 24)

# ============================================================
# TIME WINDOWS (days)
# ============================================================
VENTANA_LARGA = 30    # evolution charts and averages
VENTANA_CORTA = 7     # recent discomfort
VENTANAS = {"7 días": 7, "15 días": 15, "30 días": 30}

# ============================================================
# WELLNESS
# Five items on a 1-5 scale, all pointing the same way:
# 1 = optimal state, 5 = worst possible. No inversion before summing.
# ============================================================
ITEMS_WELLNESS = ["sueño", "fatiga", "dolor", "estres", "animo"]
ITEMS_HOOPER = ["sueño", "fatiga", "dolor", "estres"]

ETIQUETAS_ITEMS = {
    "sueño":  "Sueño",
    "fatiga": "Fatiga",
    "dolor":  "Dolor muscular",
    "estres": "Estrés",
    "animo":  "Ánimo",
}

ESCALA_WELLNESS = (1, 5)
UMBRAL_ITEM = 4       # own convention, not part of the club's methodology

HOOPER_RANGO = (4, 20)
HOOPER_BANDAS = [
    (4,  8,  "#2E7D32", "Buen estado"),
    (9,  13, "#F9A825", "Vigilar"),
    (14, 20, "#C62828", "Alerta"),
]
HOOPER_COLOR_TABLA = {"bueno": "#c8e6c9", "vigilar": "#fff9c4", "alerta": "#ffcdd2"}
HOOPER_ALERTA = 14

# ============================================================
# RPE — Borg CR10
# 0 = complete rest, 10 = maximal effort. Raw perceived value,
# not multiplied by session duration.
# ============================================================
ESCALA_RPE = (0, 10)
RPE_ALTO = 7          # threshold for a demanding session
RPE_BANDAS = [
    (0,  2,  "#4CAF50", "Suave"),
    (3,  4,  "#FFEB3B", "Moderado"),
    (5,  6,  "#F0C040", "Duro"),
    (7,  8,  "#E88C30", "Muy duro"),
    (9,  10, "#E15241", "Máximo"),
]

# ============================================================
# MATCHES
# Stoppage time is normalised: 45+x -> 45, 90+x -> 90.
# ============================================================
TRAMOS = [
    (1,  14, "0-14"),
    (15, 29, "15-29"),
    (30, 45, "30-Final 1T"),
    (46, 59, "45-59"),
    (60, 74, "60-74"),
    (75, 90, "75-Final 2T"),
]
ETIQ_TRAMOS = [t[2] for t in TRAMOS]
CORTES_TRAMOS = [0] + [hi for _, hi, _ in TRAMOS]

MINUTOS_MAX = 100     # above this, a registration error is likely

# ============================================================
# COLOURS
# ============================================================
COLOR_FAVOR = "#2E7D32"
COLOR_CONTRA = "#C62828"
COLOR_MEDIA = "#263238"
COLOR_CABECERA = "#37474F"
COLOR_JUGADORA = "#1565C0"
COLOR_RPE = "#EF6C00"

# ============================================================
# DATA SOURCES
# Exported from PostgreSQL (Supabase); see sql/ for the schema.
# ============================================================
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FICHEROS = {
    "teams":       "teams.csv",
    "players":     "players.csv",
    "matches":     "matches.csv",
    "goals":       "goals.csv",
    "appearances": "appearances.csv",
    "wellness":    "wellness.csv",
    "rpe":         "rpe.csv",
}

# Columns each file must contain. Checked on load so that a malformed
# export fails immediately and explicitly, rather than three modules later.
COLUMNAS = {
    "teams":       ["id", "nombre", "es_propio"],
    "players":     ["id", "equipo_id", "dorsal", "nombre", "nombre_corto",
                    "posicion", "activa"],
    "matches":     ["id", "jornada", "fecha", "local_id", "visita_id",
                    "goles_local", "goles_visita"],
    "goals":       ["id", "jornada", "equipo_id", "rival_id", "dorsal", "minuto"],
    "appearances": ["id", "partido_id", "dorsal", "titular", "min_entra",
                    "min_sale", "asistencias", "amarillas", "rojas"],
    "wellness":    ["id", "dorsal", "fecha", "sueño", "fatiga", "dolor",
                    "estres", "animo", "zona"],
    "rpe":         ["id", "dorsal", "fecha", "rpe"],
}
