import streamlit as st
import pandas as pd
from datetime import date
import os
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

# ---------- Cargar datos ----------
empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
registros = cargar_csv("registros_horas.csv", ["id_trabajador", "fecha", "horas_trabajadas"])

st.title("🧵 Sistema de Nómina - Maquiladora Textil")

tabs = st.tabs(["👤 Empleados", "⏱ Registro de horas", "💰 Nómina", "📥 Importar ZKTeco"])

# ---------- TAB 1: EMPLEADOS ----------
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
                # Verificar si ya existe
                existe = empleados[empleados["id_trabajador"] == id_trabajador]
                if not existe.empty:
                    st.error("Ya existe un trabajador con ese ID.")
                else:
                    nuevo = pd.DataFrame([{
                        "id_trabajador": int(id_trabajador),
                        "nombre": nombre.strip(),
                        "sueldo_hora": float(sueldo_hora)
                    }])
                    empleados = pd.concat([empleados, nuevo], ignore_index=True)
                    guardar_csv(empleados, "empleados.csv")
                    st.success("Empleado guardado correctamente ✅")

    st.subheader("Listado de empleados")
    st.dataframe(empleados)

# ---------- TAB 2: REGISTRO DE HORAS ----------
with tabs[1]:
    st.header("Registro de horas trabajadas")

    if empleados.empty:
        st.warning("Primero da de alta empleados en la pestaña 'Empleados'.")
    else:
        empleados["label"] = empleados["id_trabajador"].astype(str) + " - " + empleados["nombre"]
        seleccionado = st.selectbox("Selecciona empleado", empleados["label"])

        id_sel = int(seleccionado.split(" - ")[0])

        fecha_reg = st.date_input("Fecha", value=date.today())
        horas_trab = st.number_input("Horas trabajadas", min_value=0.0, step=0.5)

        if st.button("Guardar registro de horas"):
            nuevo_reg = pd.DataFrame([{
                "id_trabajador": id_sel,
                "fecha": fecha_reg.isoformat(),
                "horas_trabajadas": float(horas_trab)
            }])
            registros = pd.concat([registros, nuevo_reg], ignore_index=True)
            guardar_csv(registros, "registros_horas.csv")
            st.success("Registro de horas guardado ✅")

        st.subheader("Registros recientes")
        st.dataframe(registros.tail(20))

# ---------- TAB 3: NÓMINA ----------
with tabs[2]:
    st.header("Cálculo de nómina")

    if empleados.empty or registros.empty:
        st.warning("Necesitas tener empleados y registros de horas para calcular nómina.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            fecha_ini = st.date_input("Fecha inicio", value=date.today())
        with col2:
            fecha_fin = st.date_input("Fecha fin", value=date.today())

        f_ini = fecha_ini.isoformat()
        f_fin = fecha_fin.isoformat()

        regs_filtrados = registros[
            (registros["fecha"] >= f_ini) &
            (registros["fecha"] <= f_fin)
        ]

        if regs_filtrados.empty:
            st.info("No hay registros en el rango seleccionado.")
        else:
            data = regs_filtrados.merge(empleados, on="id_trabajador")
            data["sueldo_dia"] = data["horas_trabajadas"] * data["sueldo_hora"]

            st.subheader("Detalle por día")
            st.dataframe(data)

            nomina = data.groupby("id_trabajador").agg({
                "nombre": "first",
                "horas_trabajadas": "sum",
                "sueldo_dia": "sum"
            }).reset_index()

            nomina = nomina.rename(columns={
                "horas_trabajadas": "total_horas",
                "sueldo_dia": "total_pagar"
            })

            st.subheader("Resumen de nómina")
            st.dataframe(nomina)

            buffer = BytesIO()
            nomina.to_excel(buffer, index=False)
            buffer.seek(0)

            st.download_button(
                label="⬇️ Descargar nómina en Excel",
                data=buffer,
                file_name="nomina.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
# ---------- TAB 4: IMPORTAR DESDE ZKTECO ----------
with tabs[3]:
    st.header("📥 Importar registros desde ZKTeco")

    st.write("Sube el archivo ORIGINAL del reloj (hoja 'Reporte de Excepciones'). "
             "La app calculará automáticamente las horas trabajadas y las guardará en el sistema.")

    uploaded_file = st.file_uploader(
        "Archivo de reporte (.xls, .xlsx)",
        type=["xls", "xlsx"]
    )

    if uploaded_file is not None:
        try:
            # 1) Leer SIEMPRE la hoja correcta
            df_raw = pd.read_excel(
                uploaded_file,
                sheet_name="Reporte de Excepciones",  # 👈 nombre de la pestaña
                header=None
            )

            # 2) Buscar la primera fila donde la columna A tenga un ID numérico
            mask_ids = pd.to_numeric(df_raw[0], errors="coerce").notna()
            if not mask_ids.any():
                st.error("No encontré ninguna fila con ID numérico en la primera columna. "
                         "Revisa que sea la hoja 'Reporte de Excepciones'.")
            else:
                first_idx = mask_ids.idxmax()

                # Nos quedamos desde esa fila hacia abajo y columnas A–M (0–12)
                df = df_raw.loc[first_idx:, :12].copy()

                # 3) Poner nombres reales a las columnas
                df.columns = [
                    "id_trabajador",   # A
                    "nombre",          # B
                    "departamento",    # C
                    "fecha",           # D
                    "entrada1",        # E
                    "salida1",         # F
                    "entrada2",        # G
                    "salida2",         # H
                    "retardos_min",    # I
                    "salida_temp_min", # J
                    "falta_min",       # K
                    "total_min_excel", # L (lo que calcula el reloj)
                    "notas"            # M
                ]

                # Nos quedamos solo con filas que tengan ID
                df["id_trabajador"] = pd.to_numeric(df["id_trabajador"], errors="coerce")
                df = df[df["id_trabajador"].notna()]
                df["id_trabajador"] = df["id_trabajador"].astype(int)

                # 4) Limpiar fecha
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
                df = df[df["fecha"].notna()]  # quitamos filas sin fecha
                df["fecha"] = df["fecha"].dt.date  # nos quedamos con yyyy-mm-dd

                # 5) Limpiar textos de horas
                for col in ["entrada1", "salida1", "entrada2", "salida2"]:
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].replace({"nan": None, "": None})

                # 6) Convertir horas a datetime usando una fecha ficticia
                base_date = "2000-01-01 "

                def to_dt(col):
                    return pd.to_datetime(
                        base_date + df[col].astype(str),
                        format="%Y-%m-%d %H:%M",
                        errors="coerce"
                    )

                df["entrada1_dt"] = to_dt("entrada1")
                df["salida1_dt"] = to_dt("salida1")
                df["entrada2_dt"] = to_dt("entrada2")
                df["salida2_dt"] = to_dt("salida2")

                # 7) Calcular minutos por turno
                def diff_min(col_ini, col_fin):
                    mins = (df[col_fin] - df[col_ini]).dt.total_seconds() / 60
                    mins = mins.fillna(0)
                    mins = mins.clip(lower=0)
                    return mins

                df["min1"] = diff_min("entrada1_dt", "salida1_dt")
                df["min2"] = diff_min("entrada2_dt", "salida2_dt")

                # 8) Total de minutos y horas trabajadas
                df["min_totales"] = df["min1"] + df["min2"]
                df["horas_trabajadas"] = df["min_totales"] / 60

                st.subheader("Vista previa del cálculo de horas")
                st.dataframe(df[[
                    "id_trabajador", "fecha",
                    "entrada1", "salida1",
                    "entrada2", "salida2",
                    "min1", "min2", "min_totales",
                    "horas_trabajadas"
                ]].head(40))

                # 9) Preparar formato para el sistema
                nuevos_registros = df[[
                    "id_trabajador", "fecha", "horas_trabajadas"
                ]].copy()
                nuevos_registros["fecha"] = nuevos_registros["fecha"].astype(str)

                # 10) Cargar registros antiguos y unir
                registros_existentes = cargar_csv(
                    "registros_horas.csv",
                    ["id_trabajador", "fecha", "horas_trabajadas"]
                )

                registros_actualizados = pd.concat(
                    [registros_existentes, nuevos_registros],
                    ignore_index=True
                )

                # Guardar
                guardar_csv(registros_actualizados, "registros_horas.csv")

                st.success("Registros importados y calculados correctamente ✅")

                st.subheader("Registros acumulados (después de importar)")
                st.dataframe(registros_actualizados.tail(50))

        except Exception as e:
            st.error(f"Ocurrió un error al leer o procesar el archivo: {e}")


