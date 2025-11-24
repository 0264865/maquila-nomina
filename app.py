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
# ========== TAB 4: IMPORTAR DESDE ZKTECO ==========
with tabs[3]:
    st.header("📥 Importar registros desde ZKTeco")

    uploaded_file = st.file_uploader(
        "Archivo de reporte (.xls, .xlsx o .csv)",
        type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is not None:
        try:
            # 1) Leer archivo EXCEL desde la hoja correcta
            df_raw = pd.read_excel(
                uploaded_file,
                sheet_name="Reporte de Excepciones",
                header=None,
                dtype=str
            )

            # 2) Eliminar filas completamente vacías
            df_raw = df_raw.dropna(how="all")

            # 3) Renombrar columnas según la estructura del reporte
            df_raw.columns = [
                "id_trabajador", "nombre", "departamento", "fecha",
                "entrada1", "salida1", "entrada2", "salida2",
                "retardos", "salida_temp", "falta", "min_totales_excel",
                "notas"
            ]

            # 4) Limpiar datos
            df_raw["id_trabajador"] = df_raw["id_trabajador"].astype(str).str.extract(r"(\d+)")
            df_raw["fecha"] = pd.to_datetime(df_raw["fecha"], errors="coerce")

            # 5) Función para calcular minutos entre horas tipo HH:MM
            def calcular_minutos(hora_ini, hora_fin):
                try:
                    if pd.isna(hora_ini) or pd.isna(hora_fin):
                        return 0
                    h_ini = datetime.strptime(str(hora_ini), "%H:%M")
                    h_fin = datetime.strptime(str(hora_fin), "%H:%M")
                    diff = (h_fin - h_ini).total_seconds() / 60
                    return max(diff, 0)
                except:
                    return 0

            # 6) Calcular minutos trabajados en cada horario
            df_raw["min1"] = df_raw.apply(
                lambda row: calcular_minutos(row["entrada1"], row["salida1"]),
                axis=1
            )

            df_raw["min2"] = df_raw.apply(
                lambda row: calcular_minutos(row["entrada2"], row["salida2"]),
                axis=1
            )

            # 7) Total de minutos reales
            df_raw["min_totales"] = df_raw["min1"] + df_raw["min2"]

            # 8) Convertir a horas decimales
            df_raw["horas_trabajadas"] = df_raw["min_totales"] / 60

            # 9) Mostrar vista previa
            st.subheader("Vista previa del cálculo de horas")
            st.dataframe(df_raw[[
                "id_trabajador", "fecha", "entrada1", "salida1",
                "entrada2", "salida2", "min1", "min2",
                "min_totales", "horas_trabajadas"
            ]])

            # 10) Guardar en registros_horas.csv
            registros_actuales = pd.read_csv("registros_horas.csv")

            nuevos = df_raw[[
                "id_trabajador", "fecha", "horas_trabajadas"
            ]].dropna()

            nuevos["id_trabajador"] = nuevos["id_trabajador"].astype(int)

            registros_final = pd.concat([registros_actuales, nuevos], ignore_index=True)
            registros_final.to_csv("registros_horas.csv", index=False)

            # Mensaje de éxito
            st.success("Registros importados y calculados correctamente ✔️")

            # 11) Mostrar tabla acumulada final
            st.subheader("Registros acumulados (después de importar)")
            st.dataframe(registros_final)

        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")
