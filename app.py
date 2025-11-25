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
        "Sube el archivo del reloj (por ejemplo **1_report.xlsx**) sin modificarlo. "
        "La app leerá la hoja **'Reporte de Asistencia'**, calculará las horas trabajadas "
        "por trabajador y sacará el pago usando el sueldo por hora que diste de alta en 👤 Empleados."
    )

    uploaded_file = st.file_uploader(
        "Archivo de reporte (.xlsx o .csv)",
        type=["xlsx", "csv"],
    )

    if uploaded_file is not None:
        try:
            # 1) Leer archivo
            if uploaded_file.name.lower().endswith(".csv"):
                df_raw = pd.read_csv(uploaded_file, header=None)
            else:
                df_raw = pd.read_excel(
                    uploaded_file,
                    sheet_name="Reporte de Asistencia",
                    header=None
                )

            # 2) Leer rango de periodo: "2025-11-14 ~ 2025-11-21"
            periodo_texto = str(df_raw.iloc[2, 2])
            m = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})", periodo_texto)
            if m:
                inicio_periodo = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                fin_periodo = datetime.strptime(m.group(2), "%Y-%m-%d").date()
            else:
                inicio_periodo = None
                fin_periodo = None

            # 3) Buscar fila con los días (14, 15, 16, 17, etc.)
            days_row_idx = None
            for i, row in df_raw.iterrows():
                vals = row.tolist()
                nums = [
                    v for v in vals
                    if isinstance(v, (int, float)) and not (pd.isna(v))
                ]
                if len(nums) >= 2 and str(df_raw.iloc[i + 1, 0]).strip() == "ID:":
                    days_row_idx = i
                    break

            if days_row_idx is None:
                st.error("No encontré la fila con los días del periodo.")
            else:
                days_row = df_raw.iloc[days_row_idx]

                # Mapa: columna -> día del mes (14,15,...)
                col_day = {}
                for col_idx, val in days_row.items():
                    if isinstance(val, (int, float)) and not pd.isna(val):
                        col_day[col_idx] = int(val)

                # Función para mapear día (14,15...) a fecha real del periodo
                def map_day_to_date(day_num, start_date, end_date):
                    if not start_date or not end_date:
                        return None
                    for offset in range((end_date - start_date).days + 1):
                        d = start_date + timedelta(days=offset)
                        if d.day == day_num:
                            return d
                    return None

                # Buscar filas con "ID:"
                id_rows = [
                    i for i, v in enumerate(df_raw[0].astype(str))
                    if v.strip() == "ID:"
                ]

                def parse_times_cell(text):
                    if pd.isna(text):
                        return []
                    s = str(text)
                    return re.findall(r"(\d{1,2}:\d{2})", s)

                def minutos_entre(t1, t2):
                    t1_dt = datetime.strptime(t1, "%H:%M")
                    t2_dt = datetime.strptime(t2, "%H:%M")
                    return int((t2_dt - t1_dt).total_seconds() // 60)

                registros = []

                # 4) Recorrer cada trabajador (par de filas: ID + horarios)
                for id_row in id_rows:
                    fila_id = df_raw.iloc[id_row]

                    # ID numérico (en la fila del ID)
                    id_val = None
                    for v in fila_id:
                        if isinstance(v, (int, float)) and not pd.isna(v):
                            id_val = int(v)
                            break
                        if isinstance(v, str) and v.strip().isdigit():
                            id_val = int(v)
                            break

                    # Nombre (buscamos "Nombre:" y el valor 2 columnas después)
                    nombre = None
                    name_idx = None
                    for idx, val in enumerate(fila_id):
                        if isinstance(val, str) and val.strip() == "Nombre:":
                            name_idx = idx
                            break
                    if name_idx is not None and name_idx + 2 < len(fila_id):
                        posible_nombre = fila_id[name_idx + 2]
                        if isinstance(posible_nombre, str):
                            nombre = posible_nombre.strip()

                    # Fila con los horarios
                    fila_horas = df_raw.iloc[id_row + 1]

                    # Revisar cada columna que represente un día
                    for col_idx, day_num in col_day.items():
                        cell = fila_horas[col_idx]
                        tiempos = parse_times_cell(cell)
                        if not tiempos:
                            # sin registro ese día
                            continue

                        fecha = map_day_to_date(day_num, inicio_periodo, fin_periodo)

                        entrada1 = salida1 = entrada2 = salida2 = None
                        minutos = 0

                        # Reglas: tú escogiste NO calcular segundo horario si está incompleto
                        if len(tiempos) == 1:
                            entrada1 = tiempos[0]
                            # sin salida1 -> 0 minutos
                        elif len(tiempos) == 2:
                            entrada1, salida1 = tiempos[0], tiempos[1]
                            minutos += minutos_entre(entrada1, salida1)
                        elif len(tiempos) == 3:
                            entrada1, salida1, entrada2 = tiempos[0], tiempos[1], tiempos[2]
                            minutos += minutos_entre(entrada1, salida1)
                            # segundo horario pendiente, NO lo calculamos
                        else:
                            entrada1, salida1, entrada2, salida2 = (
                                tiempos[0],
                                tiempos[1],
                                tiempos[2],
                                tiempos[3],
                            )
                            minutos += minutos_entre(entrada1, salida1)
                            minutos += minutos_entre(entrada2, salida2)
                            # ignoramos marcas extra si las hay

                        # minutos esperados según día de la semana (Dalay)
                        min_esperados = None
                        if isinstance(fecha, date):
                            weekday = fecha.weekday()  # 0=lun
                            if weekday in (0, 2, 4):      # lun/mie/vie
                                min_esperados = 10 * 60   # 10 horas
                            elif weekday in (1, 3):       # mar/jue
                                min_esperados = 9 * 60    # 9 horas
                            else:
                                min_esperados = 0

                        min_faltantes = None
                        if min_esperados:
                            min_faltantes = max(min_esperados - minutos, 0)

                        registros.append(
                            {
                                "id_trabajador": id_val,
                                "nombre": nombre,
                                "fecha": fecha,
                                "dia": day_num,
                                "min_trabajados": minutos,
                                "min_esperados": min_esperados,
                                "min_faltantes": min_faltantes,
                            }
                        )

                if not registros:
                    st.warning("No se encontraron registros de horarios en el archivo.")
                else:
                    registros_df = pd.DataFrame(registros)

                    # 5) Crear horas_trabajadas y lo que se guardará para la nómina
                    registros_df["horas_trabajadas"] = registros_df["min_trabajados"] / 60.0

                    registros_nomina = registros_df[["id_trabajador", "fecha", "horas_trabajadas"]].copy()

                    # 6) Guardar / acumular en registros_horas.csv
                    registros_anteriores = cargar_csv(
                        "registros_horas.csv",
                        ["id_trabajador", "fecha", "horas_trabajadas"],
                    )
                    registros_totales = pd.concat(
                        [registros_anteriores, registros_nomina],
                        ignore_index=True,
                    )
                    guardar_csv(registros_totales, "registros_horas.csv")

                    # 7) RESUMEN FINAL POR TRABAJADOR (LO QUE QUIERE EL JEFE)
                    resumen = (
                        registros_df.groupby(["id_trabajador", "nombre"], as_index=False)
                        .agg(
                            min_trabajados_total=("min_trabajados", "sum"),
                        )
                    )
                    resumen["horas_trabajadas"] = resumen["min_trabajados_total"] / 60.0

                    # Cargar sueldos desde empleados.csv
                    empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
                    if not empleados.empty:
                        # Asegurar mismo tipo para unir
                        empleados["id_trabajador"] = empleados["id_trabajador"].astype(int)
                        resumen["id_trabajador"] = resumen["id_trabajador"].astype(int)

                        resumen = resumen.merge(
                            empleados[["id_trabajador", "sueldo_hora"]],
                            on="id_trabajador",
                            how="left",
                        )
                    else:
                        resumen["sueldo_hora"] = 0.0

                    resumen["sueldo_hora"] = resumen["sueldo_hora"].fillna(0.0)
                    resumen["pago_periodo"] = resumen["horas_trabajadas"] * resumen["sueldo_hora"]

                    resumen["horas_trabajadas"] = resumen["horas_trabajadas"].round(2)
                    resumen["pago_periodo"] = resumen["pago_periodo"].round(2)

                    resumen = resumen[
                        ["id_trabajador", "nombre", "horas_trabajadas", "sueldo_hora", "pago_periodo"]
                    ].sort_values("id_trabajador")

                    st.subheader("Resumen final de horas y pago por trabajador (solo este archivo)")
                    st.dataframe(resumen, hide_index=True)

                    total_nomina = resumen["pago_periodo"].sum()
                    st.markdown(
                        f"### 💵 Total de nómina de este reporte: **${total_nomina:,.2f} MXN**"
                    )

                    # 8) Botón para descargar el reporte en Excel
                    from io import BytesIO
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                        resumen.to_excel(writer, index=False, sheet_name="Nomina_resumen")
                    buffer.seek(0)

                    st.download_button(
                        label="💾 Descargar reporte de nómina en Excel",
                        data=buffer,
                        file_name="nomina_reporte_asistencia.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

        except Exception as e:
            st.error(f"Ocurrió un error al leer el archivo: {e}")





