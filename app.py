import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
from io import BytesIO
import re


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
    st.header("💰 Nómina por periodo")

    # Cargar datos siempre que existan
    empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
    registros = cargar_csv("registros_horas.csv", ["id_trabajador", "fecha", "horas_trabajadas"])

    if empleados.empty:
        st.warning("Primero da de alta empleados en la pestaña 👤 Empleados.")
    elif registros.empty:
        st.warning("Aún no hay registros de horas. Importa un archivo del reloj en 📥 Importar ZKTeco.")
    else:
        # Convertir fecha
        registros["fecha"] = pd.to_datetime(registros["fecha"], errors="coerce")
        registros = registros[registros["fecha"].notna()]

        # Rango de fechas para el periodo de nómina
        fecha_min = registros["fecha"].min().date()
        fecha_max = registros["fecha"].max().date()

        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input(
                "Fecha inicial del periodo",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max
            )
        with col2:
            fecha_fin = st.date_input(
                "Fecha final del periodo",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max
            )

        if fecha_inicio > fecha_fin:
            st.error("La fecha inicial no puede ser mayor que la fecha final.")
        else:
            # Filtrar registros del periodo
            mask = (registros["fecha"].dt.date >= fecha_inicio) & \
                   (registros["fecha"].dt.date <= fecha_fin)
            regs_periodo = registros[mask]

            if regs_periodo.empty:
                st.warning("No hay registros de horas en ese rango de fechas.")
            else:
                # Agrupar horas por trabajador
                horas_por_trabajador = (
                    regs_periodo
                    .groupby("id_trabajador")["horas_trabajadas"]
                    .sum()
                    .reset_index()
                )

                # Unir con catálogo de empleados (para nombre y sueldo)
                nomina = horas_por_trabajador.merge(
                    empleados,
                    on="id_trabajador",
                    how="left"
                )

                # Calcular pago
                nomina["horas_trabajadas"] = nomina["horas_trabajadas"].round(2)
                nomina["sueldo_hora"] = nomina["sueldo_hora"].round(2)
                nomina["pago"] = (nomina["horas_trabajadas"] * nomina["sueldo_hora"]).round(2)

                # Ordenar columnas bonitas
                nomina = nomina[[
                    "id_trabajador",
                    "nombre",
                    "horas_trabajadas",
                    "sueldo_hora",
                    "pago"
                ]].sort_values("id_trabajador")

                # Mostrar tabla resumen (esta es la que le enseñas al jefe)
                st.subheader("Resumen de nómina por trabajador")
                st.dataframe(nomina, hide_index=True)

                # Total de la nómina
                total_nomina = nomina["pago"].sum().round(2)
                st.markdown(
                    f"### 🧾 Total de la nómina del {fecha_inicio} al {fecha_fin}: **${total_nomina:,.2f} MXN**"
                )

                # Detalle opcional por día, por si algún día lo ocupas
                with st.expander("Ver detalle por día (opcional)"):
                    detalle = regs_periodo.merge(
                        empleados[["id_trabajador", "nombre"]],
                        on="id_trabajador",
                        how="left"
                    )
                    detalle["fecha"] = detalle["fecha"].dt.date
                    detalle["horas_trabajadas"] = detalle["horas_trabajadas"].round(2)
                    st.dataframe(
                        detalle[["id_trabajador", "nombre", "fecha", "horas_trabajadas"]],
                        hide_index=True
                    )

                # Botón para descargar el reporte en Excel
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    nomina.to_excel(writer, index=False, sheet_name="Nomina_resumen")
                    detalle.to_excel(writer, index=False, sheet_name="Detalle_por_dia")
                buffer.seek(0)

                st.download_button(
                    label="💾 Descargar reporte de nómina en Excel",
                    data=buffer,
                    file_name=f"nomina_{fecha_inicio}_a_{fecha_fin}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
# ---------- TAB 4: IMPORTAR DESDE ZKTECO ----------
with tabs[3]:
    st.header("📥 Importar desde ZKTeco (Reporte de Asistencia)")

    st.write(
        "Sube el archivo **1_report.xls** (o similar) que te da el reloj, "
        "sin modificarlo. La app va a leer la hoja **'Reporte de Asistencia'**, "
        "calcular horas, detectar faltas de marcas y guardar todo para la nómina."
    )

    uploaded_file = st.file_uploader(
        "Archivo de reporte (.xls, .xlsx o .csv)",
        type=["xls", "xlsx", "csv"],
    )

    if uploaded_file is not None:
        try:
            # 1) Leer el archivo (de preferencia .xls / .xlsx)
            if uploaded_file.name.lower().endswith(".csv"):
                df_raw = pd.read_csv(uploaded_file, header=None)
            else:
                df_raw = pd.read_excel(
                    uploaded_file,
                    sheet_name="Reporte de Asistencia",
                    header=None
                )

            st.subheader("Vista previa del archivo original")
            st.dataframe(df_raw.head(25))

            # 2) Sacar el periodo: "Periodo: 2025-11-14 ~ 2025-11-21"
            periodo_str = None
            for row in df_raw.astype(str).values:
                for val in row:
                    if "Periodo" in val:
                        periodo_str = val
                        break
                if periodo_str:
                    break

            inicio_periodo = None
            fin_periodo = None
            if periodo_str:
                m = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})", periodo_str)
                if m:
                    inicio_periodo = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                    fin_periodo = datetime.strptime(m.group(2), "%Y-%m-%d").date()

            # 3) Encontrar la fila de encabezados (donde aparece "ID:" o "ID")
            header_row_idx = None
            header_clean = None
            for i, row in df_raw.iterrows():
                row_str = row.astype(str).str.strip()
                row_cl = row_str.str.replace(":", "", regex=False)  # quita los ':'
                if any(val == "ID" for val in row_cl):
                    header_row_idx = i
                    header_clean = row_cl
                    break

            if header_row_idx is None:
                st.error("No encontré la fila con el encabezado 'ID'. Revisa que sea la hoja correcta.")
            else:
                # 4) Construir cuerpo con encabezados limpios
                df_body = df_raw.iloc[header_row_idx + 1 :].reset_index(drop=True)
                df_body.columns = header_clean

                # columnas clave
                col_id = "ID"
                col_nombre = "Nombre"

                # columnas de días (14, 15, 16, 17, etc.)
                day_cols = [
                    c for c in df_body.columns
                    if str(c).strip().isdigit()
                ]
                # respetar el orden en el archivo
                day_cols = [c for c in df_body.columns if c in day_cols]

                # asignar fecha real a cada columna de día usando el inicio del periodo
                if inicio_periodo is not None:
                    col_to_date = {
                        col: inicio_periodo + timedelta(days=i)
                        for i, col in enumerate(day_cols)
                    }
                else:
                    col_to_date = {col: str(col) for col in day_cols}

                # --- Funciones auxiliares ---
                def parse_times(cell):
                    """Regresa lista de horas tipo ['08:03','13:58','15:03','19:02']."""
                    if pd.isna(cell):
                        return []
                    text = str(cell)
                    return re.findall(r"(\d{1,2}:\d{2})", text)

                def minutos_entre(t1, t2):
                    t1_dt = datetime.strptime(t1, "%H:%M")
                    t2_dt = datetime.strptime(t2, "%H:%M")
                    return int((t2_dt - t1_dt).total_seconds() // 60)

                registros_list = []

                # 5) Recorrer cada persona y cada día
                for _, row in df_body.iterrows():
                    id_trab = row.get(col_id, None)
                    nombre = row.get(col_nombre, None)

                    if pd.isna(id_trab) or str(id_trab).strip() == "":
                        continue

                    for col in day_cols:
                        cell = row[col]
                        tiempos = parse_times(cell)
                        fecha_val = col_to_date[col]

                        if isinstance(fecha_val, date):
                            fecha_dt = fecha_val
                        else:
                            fecha_dt = fecha_val

                        entrada1 = salida1 = entrada2 = salida2 = None
                        observ = []
                        minutos = 0

                        # analizar cuántas marcas hay
                        if len(tiempos) == 0:
                            observ.append("SIN REGISTRO")
                        elif len(tiempos) == 1:
                            entrada1 = tiempos[0]
                            observ.append("FALTA SALIDA (solo una marca)")
                        elif len(tiempos) == 2:
                            entrada1, salida1 = tiempos[0], tiempos[1]
                            minutos += minutos_entre(entrada1, salida1)
                            observ.append("SIN 2° HORARIO")
                        elif len(tiempos) == 3:
                            entrada1, salida1 = tiempos[0], tiempos[1]
                            entrada2 = tiempos[2]
                            minutos += minutos_entre(entrada1, salida1)
                            observ.append("FALTA SALIDA 2° HORARIO")
                        else:
                            entrada1, salida1, entrada2, salida2 = (
                                tiempos[0],
                                tiempos[1],
                                tiempos[2],
                                tiempos[3],
                            )
                            minutos += minutos_entre(entrada1, salida1)
                            minutos += minutos_entre(entrada2, salida2)
                            if len(tiempos) > 4:
                                observ.append("Más de 4 marcas, revisar")

                        # minutos esperados según el día (horarios Dalay)
                        if isinstance(fecha_dt, date):
                            weekday = fecha_dt.weekday()  # 0 = lunes
                            if weekday in (0, 2, 4):      # lun/mie/vie
                                min_esperados = 10 * 60   # 10 horas
                            elif weekday in (1, 3):       # mar/jue
                                min_esperados = 9 * 60    # 9 horas
                            else:
                                min_esperados = 0
                        else:
                            min_esperados = None

                        if not min_esperados:
                            min_falt = None
                        else:
                            min_falt = max(min_esperados - minutos, 0)
                            if min_falt > 0 and "SIN REGISTRO" not in observ:
                                observ.append("MINUTOS FALTANTES")

                        registros_list.append(
                            {
                                "id_trabajador": id_trab,
                                "nombre": nombre,
                                "fecha": fecha_dt,
                                "entrada1": entrada1,
                                "salida1": salida1,
                                "entrada2": entrada2,
                                "salida2": salida2,
                                "min_trabajados": minutos,
                                "min_esperados": min_esperados,
                                "min_faltantes": min_falt,
                                "observaciones": "; ".join(observ),
                            }
                        )

                registros_df = pd.DataFrame(registros_list)

                # 6) Detalle por día (para revisar marcas y faltantes)
                st.subheader("Detalle por día")
                st.dataframe(registros_df, hide_index=True)

                # 7) Pasar a horas y preparar para nómina
                registros_df["horas_trabajadas"] = registros_df["min_trabajados"] / 60.0

                registros_nomina = registros_df[["id_trabajador", "fecha", "horas_trabajadas"]]

                # 8) Guardar en registros_horas.csv (se sumará en la pestaña Nómina)
                registros_anteriores = cargar_csv(
                    "registros_horas.csv",
                    ["id_trabajador", "fecha", "horas_trabajadas"],
                )
                registros_totales = pd.concat(
                    [registros_anteriores, registros_nomina],
                    ignore_index=True,
                )
                guardar_csv(registros_totales, "registros_horas.csv")

                st.success("Registros importados, calculados y guardados correctamente ✅")

                # 9) RESUMEN POR TRABAJADOR (HORAS Y SUELDO)
                st.subheader("Resumen por trabajador (horas y pago del periodo)")

                # sumar minutos por trabajador
                resumen = (
                    registros_df.groupby(["id_trabajador", "nombre"], as_index=False)
                    .agg(
                        min_trabajados_total=("min_trabajados", "sum"),
                        min_esperados_total=("min_esperados", "sum"),
                        min_faltantes_total=("min_faltantes", "sum"),
                    )
                )
                resumen["horas_trabajadas"] = resumen["min_trabajados_total"] / 60.0

                # unir con sueldos (pestaña Empleados)
                emp = empleados.copy()
                emp["id_trabajador"] = emp["id_trabajador"].astype(str)
                resumen["id_trabajador"] = resumen["id_trabajador"].astype(str)

                resumen = resumen.merge(
                    emp[["id_trabajador", "sueldo_hora"]],
                    on="id_trabajador",
                    how="left",
                )

                resumen["sueldo_hora"] = resumen["sueldo_hora"].fillna(0.0)
                resumen["pago_periodo"] = resumen["horas_trabajadas"] * resumen["sueldo_hora"]

                st.dataframe(
                    resumen[
                        [
                            "id_trabajador",
                            "nombre",
                            "horas_trabajadas",
                            "sueldo_hora",
                            "pago_periodo",
                            "min_trabajados_total",
                            "min_esperados_total",
                            "min_faltantes_total",
                        ]
                    ],
                    hide_index=True,
                )

                total_nomina = resumen["pago_periodo"].sum()
                st.markdown(f"### 💵 Total de nómina del periodo: **${total_nomina:,.2f} MXN**")

        except Exception as e:
            st.error(f"Ocurrió un error al leer el archivo: {e}")




