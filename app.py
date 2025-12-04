import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
import re
from io import BytesIO

st.set_page_config(page_title="Nómina Maquiladora", layout="wide")

# ---------- Funciones de ayuda ----------

def cargar_csv(ruta, columnas):
    if os.path.exists(ruta):
        return pd.read_csv(ruta)
    else:
        return pd.DataFrame(columns=columnas)

def guardar_csv(df, ruta):
    df.to_csv(ruta, index=False)


# ---------- Cargar datos iniciales ----------
empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
registros = cargar_csv("registros_horas.csv", ["id_trabajador", "fecha", "horas_trabajadas"])

st.title("🧵 Sistema de Nómina - Maquiladora Textil")

tabs = st.tabs([
    "👤 Empleados",
    "⏱ Registro de horas",
    "💰 Nómina",
    "🔐 Importar Excel protegido",
    "📥 Importar ZKTeco",
])

# ============================================
# ===============  TAB 1 =====================
# ============================================

with tabs[0]:
    st.header("Catálogo de empleados")

    st.subheader("Dar de alta empleado")

    with st.form("form_empleado"):
        id_trabajador = st.number_input("ID trabajador", min_value=1, step=1)
        nombre = st.text_input("Nombre completo")
        sueldo_hora = st.number_input("Sueldo por hora (MXN)", min_value=0.0, step=1.0)

        enviado = st.form_submit_button("Guardar empleado")

        if enviado:
            if nombre.strip() == "":
                st.error("El nombre no puede ir vacío.")
            else:
                existe = empleados[empleados["id_trabajador"] == id_trabajador]

                if not existe.empty:
                    st.error("Ya existe un trabajador con ese ID.")
                else:
                    nuevo = pd.DataFrame([{
                        "id_trabajador": int(id_trabajador),
                        "nombre": nombre,
                        "sueldo_hora": float(sueldo_hora)
                    }])
                    empleados = pd.concat([empleados, nuevo], ignore_index=True)
                    guardar_csv(empleados, "empleados.csv")
                    st.success("Empleado guardado correctamente.")

    st.subheader("Empleados registrados")
    if empleados.empty:
        st.info("No hay empleados registrados.")
    else:
        st.dataframe(empleados, hide_index=True)


# ============================================
# ===============  TAB 2 =====================
# ============================================

with tabs[1]:
    st.header("Registros de horas (cargados previamente)")

    if registros.empty:
        st.warning("Aún no hay registros de horas.")
    else:
        st.dataframe(registros)


# ============================================
# ===============  TAB 3 =====================
# ============================================

with tabs[2]:
    st.header("Nómina por periodo")

    registros = cargar_csv("registros_horas.csv", ["id_trabajador", "fecha", "horas_trabajadas"])

    if registros.empty:
        st.warning("No hay registros de horas. Primero importa desde ZKTeco.")
    else:
        registros["fecha"] = pd.to_datetime(registros["fecha"], errors="coerce")
        registros = registros[registros["fecha"].notna()]

        fecha_min = registros["fecha"].min().date()
        fecha_max = registros["fecha"].max().date()

        col1, col2 = st.columns(2)
        with col1:
            inicio = st.date_input("Fecha inicial", value=fecha_min)
        with col2:
            fin = st.date_input("Fecha final", value=fecha_max)

        if inicio > fin:
            st.error("Fechas inválidas.")
        else:
            mask = (registros["fecha"].dt.date >= inicio) & (registros["fecha"].dt.date <= fin)
            periodo = registros[mask]

            if periodo.empty:
                st.warning("No hay registros en esas fechas.")
            else:
                resumen = (
                    periodo.groupby("id_trabajador", as_index=False)
                    .agg(horas_trabajadas=("horas_trabajadas", "sum"))
                )

                resumen["horas_trabajadas"] = resumen["horas_trabajadas"].round(2)

                empleados_local = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
                resumen = resumen.merge(empleados_local, on="id_trabajador", how="left")

                resumen["sueldo_hora"] = resumen["sueldo_hora"].fillna(0)
                resumen["pago"] = (resumen["horas_trabajadas"] * resumen["sueldo_hora"]).round(2)

                st.subheader("Resumen del periodo")
                st.dataframe(resumen)

                total = resumen["pago"].sum()
                st.markdown(f"### TOTAL NÓMINA: **${total:,.2f} MXN**")

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    resumen.to_excel(writer, index=False, sheet_name="Nomina")
                buffer.seek(0)

                st.download_button(
                    label="📥 Descargar Excel",
                    data=buffer,
                    file_name="nomina_periodo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ============================================
# =============== TAB 4 ======================
# ============================================

    if archivo_protegido is not None:
        nombre = archivo_protegido.name.lower()

        # Elegimos engine según la extensión
        if nombre.endswith(".xlsx"):
            engine = "openpyxl"
        else:
            engine = "xlrd"

        try:
            df = pd.read_excel(archivo_protegido, engine=engine)
        except ImportError:
            st.error(
                "Falta instalar la librería para leer Excel "
                "(openpyxl para .xlsx y xlrd para .xls). "
                "Revisa que estén en requirements.txt."
            )
            st.stop()

        st.subheader("Vista previa del archivo")
        st.dataframe(df.head(20))


# ============================================
# ========== HELPERS PARA ZKTECO =============
# ============================================

def _parse_horas_en_celda(texto):
    if not isinstance(texto, str):
        return [None, None, None, None]

    limpio = texto.replace("\n", " ").replace("\r", " ")
    horas = re.findall(r"\d{1,2}:\d{2}", limpio)
    horas = horas[:4]
    while len(horas) < 4:
        horas.append(None)
    return horas

def _diff_min(e, s):
    if not e or not s:
        return 0
    try:
        t1 = datetime.strptime(e, "%H:%M")
        t2 = datetime.strptime(s, "%H:%M")
        if t2 < t1:
            t2 += timedelta(days=1)
        return int((t2 - t1).total_seconds() // 60)
    except:
        return 0

def procesar_celda_horario(texto):
    e1, s1, e2, s2 = _parse_horas_en_celda(texto)

    obs = []
    min1 = _diff_min(e1, s1)
    min2 = 0

    if e2 and s2:
        min2 = _diff_min(e2, s2)
    elif e2 or s2:
        obs.append("❗ Segundo horario incompleto")

    if (e1 and not s1) or (s1 and not e1):
        obs.append("❗ Primer horario incompleto")

    if not e1 and not s1 and not e2 and not s2:
        obs_txt = "SIN REGISTRO"
    else:
        obs_txt = " ; ".join(obs) if obs else "OK"

    return e1, s1, e2, s2, (min1 + min2), obs_txt


# ============================================
# ================= TAB 5 =====================
# ============================================

with tabs[4]:
    st.header("Importar desde ZKTeco (Reporte de Asistencia)")

    uploaded_file = st.file_uploader(
        "Archivo ZKTeco (1_report.xls o .xlsx)",
        type=["xls", "xlsx"]
    )

    if uploaded_file is not None:
        try:
            xls = pd.ExcelFile(uploaded_file)
            if "Reporte de Asistencia" in xls.sheet_names:
                df_raw = pd.read_excel(uploaded_file, sheet_name="Reporte de Asistencia", header=None, dtype=str)
            else:
                df_raw = pd.read_excel(uploaded_file, header=None, dtype=str)

            st.subheader("Vista previa")
            st.dataframe(df_raw.head(30))

            # ---- Detectar fila de días (14, 15, 16...) ----
            fila_dias = None
            cols_dias = {}
            for i in range(len(df_raw)):
                row = df_raw.iloc[i]
                nums = []
                for j, val in enumerate(row):
                    try:
                        n = int(str(val))
                        if 1 <= n <= 31:
                            nums.append((j, n))
                    except:
                        pass
                if len(nums) >= 3:
                    fila_dias = i
                    for j, n in nums:
                        cols_dias[j] = n
                    break

            if fila_dias is None:
                st.error("No pude detectar la fila de días.")
                st.stop()

            # ---- Detectar filas con 'ID:' ----
            valores = df_raw.values
            filas_id = []
            nombre_por_fila = {}

            for i in range(valores.shape[0]):
                for j in range(valores.shape[1]):
                    v = valores[i, j]
                    if v == "ID:":
                        filas_id.append((i, j))
                    elif v == "Nombre:":
                        nombre_por_fila[i] = j

            registros_dia = []

            for fila, col_id_label in filas_id:
                id_val = df_raw.iat[fila, col_id_label + 1]
                if pd.isna(id_val):
                    continue
                id_trab = str(id_val).strip()

                col_nombre = nombre_por_fila.get(fila, None)
                if col_nombre is not None:
                    nombre = df_raw.iat[fila, col_nombre + 1]
                else:
                    nombre = ""
                nombre = "" if pd.isna(nombre) else str(nombre).strip()

                fila_datos = fila + 1

                for c, dia_mes in cols_dias.items():
                    texto = df_raw.iat[fila_datos, c]
                    e1, s1, e2, s2, mins, obs = procesar_celda_horario(texto)

                    registros_dia.append({
                        "id_trabajador": id_trab,
                        "nombre": nombre,
                        "dia": dia_mes,
                        "entrada1": e1,
                        "salida1": s1,
                        "entrada2": e2,
                        "salida2": s2,
                        "min_trabajados": mins,
                        "observaciones": obs
                    })

            detalle_df = pd.DataFrame(registros_dia)

            st.subheader("Detalle interpretado")
            st.dataframe(detalle_df)

            # ---- Resumen final ----
            resumen = (
                detalle_df.groupby(["id_trabajador", "nombre"], as_index=False)
                .agg(min_trabajados_total=("min_trabajados", "sum"))
            )

            resumen["horas_trabajadas"] = (resumen["min_trabajados_total"] / 60).round(2)

            empleados_local = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
            empleados_local["id_trabajador"] = empleados_local["id_trabajador"].astype(str)

            resumen = resumen.merge(
                empleados_local[["id_trabajador", "sueldo_hora"]],
                on="id_trabajador",
                how="left"
            )

            resumen["sueldo_hora"] = resumen["sueldo_hora"].fillna(0)
            resumen["pago_periodo"] = (resumen["horas_trabajadas"] * resumen["sueldo_hora"]).round(2)

            st.subheader("Resumen por trabajador")
            st.dataframe(resumen)

            total_nomina = resumen["pago_periodo"].sum()
            st.markdown(f"### TOTAL NÓMINA: **${total_nomina:,.2f} MXN**")

            # ---- Guardar ----
            guardar_csv(detalle_df[["id_trabajador", "dia", "min_trabajados"]]
                        .rename(columns={"dia": "fecha", "min_trabajados": "horas_trabajadas"}),
                        "registros_horas.csv")

            # ---- Descargar Excel ----
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                resumen.to_excel(writer, index=False, sheet_name="Resumen_nomina")
                detalle_df.to_excel(writer, index=False, sheet_name="Detalle_dias")
            buffer.seek(0)

            st.download_button(
                label="📥 Descargar reporte Excel",
                data=buffer,
                file_name="reporte_nomina_semana.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.success("Importación completa ✅")

        except Exception as e:
            st.error(f"Ocurrió un error procesando el archivo: {e}")





