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
# ------------ TAB 4: IMPORTAR DESDE ZKTECO ------------
with tabs[3]:
    st.header("Importar reportes del reloj ZKTeco (automático)")

    st.write("Sube el archivo ORIGINAL del reloj (Reporte de Excepciones). "
             "La app detectará horas incluso si vienen mezcladas.")

    uploaded = st.file_uploader(
        "Archivo del reloj (.xls, .xlsx)",
        type=["xls", "xlsx"]
    )

    if uploaded is not None:
        try:
            df_raw = pd.read_excel(uploaded, header=None)

            st.subheader("Vista previa del archivo original")
            st.dataframe(df_raw.head(20))

            # ----------  EXTRAER HORAS AUTOMÁTICAMENTE ----------
            import re

            def extraer_horas(celda):
                """Encuentra todas las horas HH:MM en una celda sucia."""
                if pd.isna(celda):
                    return []
                texto = str(celda)
                return re.findall(r'\b\d{1,2}:\d{2}\b', texto)

            registros = []

            for idx, fila in df_raw.iterrows():

                # Columnas típicas del ZKTeco
                col_id = fila[0]
                col_fecha = fila[3] if len(fila) > 3 else None

                # Validar si es fila válida con ID y fecha real
                if not str(col_id).isdigit():
                    continue
                try:
                    fecha = pd.to_datetime(col_fecha, errors='coerce')
                except:
                    continue
                if pd.isna(fecha):
                    continue

                # Buscar horas en toda la fila
                horas = []
                for col in fila:
                    horas += extraer_horas(col)

                # Tomar solo 2 o 4 horas máximo
                horas = horas[:4]

                # Asignación flexible
                entrada1 = horas[0] if len(horas) >= 1 else None
                salida1  = horas[1] if len(horas) >= 2 else None
                entrada2 = horas[2] if len(horas) >= 3 else None
                salida2  = horas[3] if len(horas) >= 4 else None

                # Convertir horas a minutos
                def minutos(h):
                    if h is None:
                        return 0
                    t = pd.to_datetime(h, format="%H:%M")
                    return t.hour * 60 + t.minute

                min1 = max(0, minutos(salida1) - minutos(entrada1)) if entrada1 and salida1 else 0
                min2 = max(0, minutos(salida2) - minutos(entrada2)) if entrada2 and salida2 else 0

                min_totales = min1 + min2
                horas_trab = round(min_totales / 60, 2)

                registros.append({
                    "id_trabajador": int(col_id),
                    "fecha": fecha.date(),
                    "entrada1": entrada1,
                    "salida1": salida1,
                    "entrada2": entrada2,
                    "salida2": salida2,
                    "min1": min1,
                    "min2": min2,
                    "min_totales": min_totales,
                    "horas_trabajadas": horas_trab
                })

            df_final = pd.DataFrame(registros)

            st.subheader("Vista previa del cálculo de horas")
            st.dataframe(df_final)

            # Cargar registros previos
            try:
                df_prev = pd.read_csv("registros_horas.csv")
            except:
                df_prev = pd.DataFrame(columns=df_final.columns)

            df_out = pd.concat([df_prev, df_final], ignore_index=True)

            df_out.to_csv("registros_horas.csv", index=False)

            st.success("Registros importados y calculados correctamente ✔")

            st.subheader("Registros acumulados (después de importar)")
            st.dataframe(df_out.tail(50))

        except Exception as e:
            st.error(f"Error al procesar archivo: {e}")

