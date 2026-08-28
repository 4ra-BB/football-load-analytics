"""
Football Load & Performance Analytics — Streamlit interface.

A read-only demo running on synthetic data. Everything on screen is computed
by the modules in src/; this file only decides what gets shown and where.
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src import (charts, config, data, matches as mt, opposition as opp,
                 player as pl, reports, rpe as mod_rpe, squad as sq, tables,
                 wellness as mod_w)

st.set_page_config(page_title=f"{config.EQUIPO} — Análisis",
                   page_icon="⚽", layout="wide")


# ============================================================
# DATA
# ============================================================

@st.cache_data(show_spinner="Preparando datos…")
def preparar(fecha_ref: pd.Timestamp):
    """Load every table and run all preparation once per session."""
    crudo = data.cargar_todo()
    avisos = {}

    equipo_id = data.id_equipo_propio(crudo["teams"])
    nombres = data.nombre_equipos(crudo["teams"])
    squad = sq.preparar(crudo["players"], equipo_id)

    raras = sq.posiciones_no_reconocidas(squad)
    if raras:
        avisos["Plantilla"] = {"posiciones_no_reconocidas": raras}

    w, av = mod_w.preparar(crudo["wellness"], squad)
    if av:
        avisos["Wellness"] = av

    r, av = mod_rpe.preparar(crudo["rpe"], squad)
    if av:
        avisos["RPE"] = av

    a, av = mt.preparar_appearances(crudo["appearances"], crudo["matches"],
                                    squad, equipo_id)
    if av:
        avisos["Partidos"] = av

    g, av = mt.preparar_goals(crudo["goals"], squad, equipo_id)
    if av:
        avisos["Goles"] = av

    cal = opp.calendario(crudo["matches"], equipo_id, nombres)

    return {"equipo_id": equipo_id, "nombres": nombres, "squad": squad,
            "wellness": w, "rpe": r, "appearances": a, "goals": g,
            "matches": crudo["matches"], "calendario": cal}, avisos


try:
    datos, avisos = preparar(config.FECHA_DEMO)
except Exception as e:
    st.error(f"No se pudieron cargar los datos: {e}")
    st.stop()

EQ = datos["equipo_id"]


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(config.EQUIPO)
st.sidebar.caption(f"Temporada {config.TEMPORADA} · datos sintéticos")

# The dataset is fixed, so the reference date is anchored to its last day.
# Using today() would leave the demo staring at an empty window within weeks.
fecha_ref = pd.Timestamp(
    st.sidebar.date_input(
        "Fecha de referencia", value=config.FECHA_DEMO,
        min_value=pd.Timestamp("2026-07-25"), max_value=config.FECHA_DEMO,
        help="Los datos de esta demo llegan hasta el 24-08-2026.")
).normalize()

etiqueta = st.sidebar.selectbox("Ventana de análisis",
                                list(config.VENTANAS) + ["Personalizada"],
                                index=2)
if etiqueta == "Personalizada":
    dias = st.sidebar.number_input("Número de días", min_value=3,
                                   max_value=120, value=30, step=1)
else:
    dias = config.VENTANAS[etiqueta]

dias_corta = st.sidebar.number_input(
    "Ventana de molestias (días)", min_value=1, max_value=30,
    value=config.VENTANA_CORTA, step=1,
    help="Periodo para el listado de molestias reportadas.")

seccion = st.sidebar.radio(
    "Sección",
    ["Resumen del día", "Wellness", "RPE", "Ficha de jugadora",
     "Rendimiento en partidos", "Análisis de rival", "Control de datos"])

st.sidebar.divider()
st.sidebar.subheader("Informes")

with st.sidebar:
    if st.button("Generar informe de carga", use_container_width=True):
        pdf = reports.informe_carga(datos["wellness"], datos["rpe"], fecha_ref)
        st.download_button("Descargar informe de carga", pdf,
                           reports.nombre_archivo("carga", fecha_ref),
                           mime="application/pdf", use_container_width=True)
        st.caption("Contiene datos de salud. Uso restringido.")

    if st.button("Generar informe de partido", use_container_width=True):
        pdf = reports.informe_partido(
            datos["appearances"], datos["goals"], datos["matches"],
            datos["calendario"], datos["nombres"], EQ, fecha_ref)
        st.download_button("Descargar informe de partido", pdf,
                           reports.nombre_archivo("partido", fecha_ref),
                           mime="application/pdf", use_container_width=True)

st.sidebar.divider()
st.sidebar.caption(
    "Demo pública con datos sintéticos. Ninguna persona real aparece en ellos.")


DIAS_L, DIAS_C = dias, dias_corta


# ============================================================
# DAILY SUMMARY
# ============================================================

if seccion == "Resumen del día":
    st.header(f"Resumen — {fecha_ref:%d-%m-%Y}")

    squad, w, r = datos["squad"], datos["wellness"], datos["rpe"]
    falta_w = sq.sin_registro(w, squad, fecha_ref)
    falta_r = sq.sin_registro(r, squad, fecha_ref)

    c1, c2, c3 = st.columns(3)
    c1.metric("Jugadoras en plantilla", len(squad))
    c2.metric("Wellness pendiente", len(falta_w),
              delta=f"{len(squad) - len(falta_w)} completado", delta_color="off")
    c3.metric("RPE pendiente", len(falta_r),
              delta=f"{len(squad) - len(falta_r)} completado", delta_color="off")

    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("Wellness sin completar")
        if falta_w.empty:
            st.success("Todas las jugadoras han respondido.")
        else:
            st.dataframe(falta_w, use_container_width=True, hide_index=True)
    with col_r:
        st.subheader("RPE sin completar")
        if falta_r.empty:
            st.success("Todas las jugadoras han respondido.")
        else:
            st.dataframe(falta_r, use_container_width=True, hide_index=True)

    st.caption("«Días sin responder» distingue un olvido puntual de una falta "
               "sostenida. Si no hubo sesión, el RPE pendiente es lo esperable.")

    st.divider()
    st.subheader("Alertas")
    alerta, molestia = mod_w.alertas_dia(w, fecha_ref)

    if not alerta and molestia.empty:
        st.success("Sin valores en zona de alerta ni molestias reportadas.")
    else:
        if alerta:
            st.error(f"Índice Hooper en zona de alerta "
                     f"(≥{config.HOOPER_ALERTA}): {', '.join(alerta)}")
        if not molestia.empty:
            st.warning("Molestias reportadas hoy:")
            st.dataframe(molestia, use_container_width=True, hide_index=True)
            st.caption("Comunicar al cuerpo médico el mismo día.")


# ============================================================
# WELLNESS
# ============================================================

elif seccion == "Wellness":
    st.header("Wellness")
    w = datos["wellness"]
    w_l = mod_w.ventana(w, fecha_ref, DIAS_L)
    w_c = mod_w.ventana(w, fecha_ref, DIAS_C)

    if w_l.empty:
        st.info(f"Sin registros en los últimos {DIAS_L} días.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jugadoras", w_l["jugadora"].nunique())
        c2.metric("Registros", len(w_l))
        c3.metric("Hooper medio", f"{w_l['hooper'].mean():.1f}")

        st.subheader(f"Índice Hooper por posición — últimos {DIAS_L} días")
        fig = charts.matriz_hooper(w_l, mod_w.media_equipo(w_l), fecha_ref, DIAS_L)
        st.pyplot(fig); plt.close(fig)
        st.caption("Los huecos en las líneas son días sin respuesta. No se "
                   "interpolan: la adherencia al cuestionario es información.")

        st.subheader(f"Promedios — últimos {DIAS_L} días")
        tabla = mod_w.tabla_promedios(w_l)
        cols = list(config.ETIQUETAS_ITEMS.values()) + ["Índice Hooper"]
        st.dataframe(tables.estilo_pantalla(tabla, cols, tables.color_wellness),
                     use_container_width=True)
        st.caption("«Registros» indica sobre cuántas respuestas se calcula "
                   "cada media.")

    st.subheader(f"Molestias — últimos {DIAS_C} días")
    detalle, resumen = mod_w.molestias(w, w_c, DIAS_C)
    if detalle.empty:
        st.success("Sin molestias reportadas.")
    else:
        st.dataframe(resumen, use_container_width=True, hide_index=True)
        with st.expander("Ver detalle día a día"):
            st.dataframe(detalle, use_container_width=True, hide_index=True)
        st.caption("«Días seguidos» cuenta solo días con respuesta: la ausencia "
                   "de dato no es ausencia de dolor.")


# ============================================================
# RPE
# ============================================================

elif seccion == "RPE":
    st.header("Percepción del esfuerzo")
    r_l = mod_rpe.ventana(datos["rpe"], fecha_ref, DIAS_L)

    if r_l.empty:
        st.info(f"Sin registros en los últimos {DIAS_L} días.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jugadoras", r_l["jugadora"].nunique())
        c2.metric("Sesiones", r_l["fecha"].nunique())
        c3.metric("RPE medio", f"{r_l['rpe'].mean():.1f}")

        st.subheader(f"RPE por posición — últimos {DIAS_L} días")
        fig = charts.matriz_rpe(r_l, mod_rpe.media_equipo(r_l), fecha_ref, DIAS_L)
        st.pyplot(fig); plt.close(fig)
        st.caption("Solo hay registro en días con sesión o partido: un hueco "
                   "significa que no se entrenó.")

        st.subheader(f"Promedios — últimos {DIAS_L} días")
        st.dataframe(
            tables.estilo_pantalla(mod_rpe.tabla_promedios(r_l),
                                   ["RPE medio", "RPE máx."], tables.color_rpe),
            use_container_width=True)
        st.caption("«Sesiones ≥7» separa lo que la media esconde: un mismo "
                   "promedio puede venir de sesiones homogéneas o de alternar "
                   "cargas muy dispares.")


# ============================================================
# PLAYER PROFILE
# ============================================================

elif seccion == "Ficha de jugadora":
    st.header("Ficha de jugadora")
    squad = datos["squad"]
    opciones = pl.opciones_selector(squad)

    etiqueta_jug = st.selectbox("Jugadora", list(opciones),
                                help="Escribe un dorsal o un nombre para filtrar.")
    dorsal = opciones[etiqueta_jug]
    info = pl.datos(dorsal, squad)

    st.subheader(f"{info['nombre']} · Dorsal {info['dorsal']} · "
                 f"{config.NOMBRE_POS.get(info['posicion'], info['posicion'])}")

    t1, t2, t3, t4 = st.tabs(["Evolución", "Indicadores", "Partidos", "Molestias"])

    with t1:
        series = pl.series(dorsal, datos["wellness"], datos["rpe"],
                           fecha_ref, DIAS_L)
        if series["wellness"].empty and series["rpe"].empty:
            st.info(f"Sin registros en los últimos {DIAS_L} días.")
        else:
            fig = charts.ficha_jugadora(series, info["nombre_corto"],
                                        fecha_ref, DIAS_L)
            st.pyplot(fig); plt.close(fig)
            st.caption("Los círculos rojos marcan días con molestia reportada. "
                       "La línea discontinua es la media del equipo.")

    with t2:
        st.dataframe(
            pl.indicadores(dorsal, info["nombre_corto"], datos["wellness"],
                           datos["rpe"], datos["appearances"], datos["goals"],
                           EQ, fecha_ref, DIAS_L),
            use_container_width=True, hide_index=True)
        st.caption(f"Los datos de carga corresponden a los últimos {DIAS_L} "
                   f"días; los de partidos son acumulados de temporada.")

    with t3:
        partidos_jug = pl.partidos_jugadora(dorsal, datos["appearances"],
                                            datos["goals"], EQ, datos["nombres"])
        if partidos_jug.empty:
            st.info("Sin partidos registrados.")
        else:
            fig = charts.minutos_jugadora(partidos_jug, info["nombre_corto"])
            st.pyplot(fig); plt.close(fig)
            st.dataframe(partidos_jug, use_container_width=True, hide_index=True)

    with t4:
        mol = pl.molestias(dorsal, datos["wellness"], fecha_ref, DIAS_L)
        if mol.empty:
            st.success(f"Sin molestias reportadas en los últimos {DIAS_L} días.")
        else:
            st.dataframe(mol, use_container_width=True, hide_index=True)


# ============================================================
# MATCH PERFORMANCE
# ============================================================

elif seccion == "Rendimiento en partidos":
    st.header("Rendimiento en partidos")
    a, g = datos["appearances"], datos["goals"]

    if a.empty:
        st.info("Sin partidos registrados.")
    else:
        st.subheader("Resumen por jugadora")
        st.dataframe(mt.resumen_jugadoras(a, g, EQ),
                     use_container_width=True, hide_index=True)

    if not g.empty:
        n = mt.partidos_disputados(datos["matches"], EQ, fecha_ref)
        cf, cc = mt.conteo_tramos(g, EQ)

        st.subheader("Distribución de goles por tramo")
        fig = charts.barras_tramos(
            cf, cc, f"{config.EQUIPO} — goles por tramo ({n} partidos)")
        st.pyplot(fig); plt.close(fig)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.dataframe(mt.resumen_goles(cf, cc, n),
                         use_container_width=True, hide_index=True)
        with c2:
            st.subheader("Clasificación")
            st.dataframe(
                mt.clasificacion(
                    datos["matches"][datos["matches"]["fecha"] <= fecha_ref],
                    datos["nombres"]),
                use_container_width=True, hide_index=True)


# ============================================================
# OPPOSITION
# ============================================================

elif seccion == "Análisis de rival":
    st.header("Análisis de rival")
    g, cal = datos["goals"], datos["calendario"]

    proximo = opp.proximo_partido(cal, fecha_ref)
    referencia = proximo or opp.ultimo_partido(cal, fecha_ref)

    disponibles = opp.equipos_disponibles(
        pd.DataFrame({"id": list(datos["nombres"]),
                      "nombre": list(datos["nombres"].values())}), excluir=EQ)

    por_defecto = referencia["rival_id"] if referencia else list(disponibles)[0]
    ids = list(disponibles)

    if proximo:
        cuando = "hoy" if proximo["dias"] == 0 else f"en {proximo['dias']} días"
        st.info(f"**Próximo partido:** {config.EQUIPO} vs {proximo['rival']} · "
                f"{proximo['fecha']:%d-%m-%Y} · Jornada {proximo['jornada']} · "
                f"{proximo['condicion']} · {cuando}")
    elif referencia:
        st.info(f"Temporada finalizada. Último partido: {referencia['rival']} "
                f"({referencia['fecha']:%d-%m-%Y}).")

    rival_id = st.selectbox("Equipo a analizar", ids,
                            index=ids.index(por_defecto),
                            format_func=lambda i: disponibles[i])
    rival = disponibles[rival_id]

    if g.empty:
        st.info("Sin goles registrados en la liga.")
    else:
        n_rival = mt.partidos_disputados(datos["matches"], rival_id, fecha_ref)
        cfr, ccr = mt.conteo_tramos(g, rival_id)

        c1, c2, c3 = st.columns(3)
        c1.metric("Partidos", n_rival)
        c2.metric("Goles marcados", int(cfr.sum()))
        c3.metric("Goles encajados", int(ccr.sum()))

        st.subheader("Máximas goleadoras")
        top, total = opp.maximas_goleadoras(g, rival_id)
        if top.empty:
            st.info(f"Sin goles registrados de {rival}.")
        else:
            st.dataframe(top, use_container_width=True, hide_index=True)
            st.caption("«% goles equipo» da la lectura táctica: una jugadora "
                       "que concentra buena parte de los goles se puede marcar "
                       "individualmente; un reparto plano indica otra cosa.")

        st.subheader("Distribución de goles por tramo")
        fig = charts.barras_tramos(
            cfr, ccr, f"{rival} — goles por tramo ({n_rival} partidos)",
            etiqueta_favor=f"Goles de {rival}",
            etiqueta_contra=f"Goles encajados por {rival}")
        st.pyplot(fig); plt.close(fig)

        st.dataframe(opp.resumen_rival(g, rival_id, n_rival),
                     use_container_width=True, hide_index=True)

        st.subheader("Dónde marcamos frente a dónde encajan")
        fig = charts.contraste_tramos(
            opp.contraste_tramos(g, EQ, rival_id), config.EQUIPO, rival)
        st.pyplot(fig); plt.close(fig)

        hist = opp.historial(cal, rival_id, fecha_ref)
        if not hist.empty:
            with st.expander(f"Enfrentamientos previos con {rival}"):
                st.dataframe(hist, use_container_width=True, hide_index=True)


# ============================================================
# DATA QUALITY
# ============================================================

elif seccion == "Control de datos":
    st.header("Control de datos")
    st.caption("Incidencias detectadas al preparar los datos. En la versión de "
               "producción sirven para corregir los registros en origen.")

    if not avisos:
        st.success("Sin incidencias.")
    else:
        for fuente, detalle in avisos.items():
            with st.expander(f"{fuente} — {len(detalle)} incidencias"):
                for clave, valor in detalle.items():
                    st.write(f"**{clave.replace('_', ' ').capitalize()}:** {valor}")

    st.divider()
    st.subheader("Adherencia al cuestionario")
    w, squad = datos["wellness"], datos["squad"]
    if not w.empty:
        dias_totales = w["fecha"].nunique()
        adh = (w.groupby("jugadora")["fecha"].nunique()
               .rename("Días respondidos").reset_index())
        adh["% adherencia"] = (adh["Días respondidos"] / dias_totales * 100).round(0)
        adh = adh.sort_values("% adherencia").rename(columns={"jugadora": "Jugadora"})
        st.dataframe(adh, use_container_width=True, hide_index=True)
        st.caption(f"Sobre {dias_totales} días con registros en el conjunto de "
                   f"datos. Una adherencia baja limita lo que se puede afirmar "
                   f"sobre esa jugadora.")

    st.divider()
    st.subheader("Plantilla")
    st.dataframe(squad.rename(columns={
        "dorsal": "Dorsal", "nombre": "Nombre",
        "nombre_corto": "Nombre corto", "posicion": "Posición"}),
        use_container_width=True, hide_index=True)
