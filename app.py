 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/app.py b/app.py
index 65a8ac6b7e6ba86e951f249fc3fcac3920721974..9435d8977cfb77e9fa15bcccaec13ed69b9a3048 100644
--- a/app.py
+++ b/app.py
@@ -3,51 +3,57 @@ import pandas as pd
 from datetime import date, datetime
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
 
-tabs = st.tabs(["👤 Empleados", "⏱ Registro de horas", "💰 Nómina", "📥 Importar ZKTeco"])
+tabs = st.tabs([
+    "👤 Empleados",
+    "⏱ Registro de horas",
+    "💰 Nómina",
+    "🔐 Importar Excel protegido",
+    "📥 Importar ZKTeco",
+])
 
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
@@ -182,52 +188,156 @@ with tabs[2]:
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
-# ---------- TAB 4: IMPORTAR DESDE ZKTECO (REPORTE DE ASISTENCIA) ----------
+# ---------- TAB 4: IMPORTAR EXCEL PROTEGIDO (HORARIOS) ----------
 with tabs[3]:
+    st.header("Importar horarios desde un Excel protegido")
+
+    st.write(
+        "Sube el archivo original (aunque tenga celdas bloqueadas). "
+        "La app lo leerá en modo solo-lectura y no modificará el archivo. "
+        "Selecciona las columnas de ID, fecha, entrada y salida para calcular las horas."
+    )
+
+    archivo_protegido = st.file_uploader(
+        "Archivo Excel con marcas de entrada/salida",
+        type=["xls", "xlsx"],
+        key="uploader_excel_protegido",
+    )
+
+    if archivo_protegido is not None:
+        try:
+            contenido = archivo_protegido.getvalue()
+            buffer_excel = BytesIO(contenido)
+            xls = pd.ExcelFile(buffer_excel, engine="openpyxl")
+
+            hoja = st.selectbox("Hoja a leer", xls.sheet_names)
+
+            # Reposicionar el buffer para leer la hoja elegida
+            buffer_excel.seek(0)
+            df_excel = pd.read_excel(
+                BytesIO(contenido), sheet_name=hoja, engine="openpyxl"
+            )
+
+            st.subheader("Vista previa")
+            st.dataframe(df_excel.head(20))
+
+            columnas = list(df_excel.columns)
+
+            def sugerir_columna(patron):
+                for idx, col in enumerate(columnas):
+                    if re.search(patron, str(col), re.IGNORECASE):
+                        return idx
+                return 0
+
+            col_id = st.selectbox(
+                "Columna de ID trabajador",
+                columnas,
+                index=sugerir_columna(r"id|empleado|trabajador"),
+            )
+            col_fecha = st.selectbox(
+                "Columna de fecha",
+                columnas,
+                index=sugerir_columna(r"fecha|dia|día"),
+            )
+            col_entrada = st.selectbox(
+                "Columna de hora de entrada",
+                columnas,
+                index=sugerir_columna(r"entrada|in"),
+            )
+            col_salida = st.selectbox(
+                "Columna de hora de salida",
+                columnas,
+                index=sugerir_columna(r"salida|out"),
+            )
+
+            def calcular_horas(fila):
+                e = fila["entrada"]
+                s = fila["salida"]
+                if pd.isna(e) or pd.isna(s):
+                    return 0
+                try:
+                    entrada_dt = datetime.combine(date.min, pd.to_datetime(e).time())
+                    salida_dt = datetime.combine(date.min, pd.to_datetime(s).time())
+                    if salida_dt < entrada_dt:
+                        # cruza medianoche
+                        salida_dt = salida_dt.replace(day=salida_dt.day + 1)
+                    return (salida_dt - entrada_dt).total_seconds() / 3600
+                except Exception:
+                    return 0
+
+            df_limpio = pd.DataFrame({
+                "id_trabajador": df_excel[col_id],
+                "fecha": pd.to_datetime(df_excel[col_fecha], errors="coerce").dt.date,
+                "entrada": df_excel[col_entrada],
+                "salida": df_excel[col_salida],
+            })
+
+            df_limpio["horas_trabajadas"] = df_limpio.apply(calcular_horas, axis=1)
+
+            df_limpio = df_limpio.dropna(subset=["id_trabajador", "fecha"])
+            df_limpio["id_trabajador"] = df_limpio["id_trabajador"].astype(int)
+
+            st.subheader("Registros listos para importar")
+            st.dataframe(
+                df_limpio[["id_trabajador", "fecha", "horas_trabajadas"]].head(30),
+                hide_index=True,
+            )
+
+            if st.button("Agregar a registros de horas", key="importar_excel_protegido"):
+                registros_nuevos = df_limpio[["id_trabajador", "fecha", "horas_trabajadas"]]
+                registros = pd.concat([registros, registros_nuevos], ignore_index=True)
+                guardar_csv(registros, "registros_horas.csv")
+                st.success("Registros importados y guardados ✅")
+
+        except Exception as e:
+            st.error(f"No pude leer el Excel protegido: {e}")
+
+# ---------- TAB 5: IMPORTAR DESDE ZKTECO (REPORTE DE ASISTENCIA) ----------
+with tabs[4]:
     st.header("Importar desde ZKTeco (Reporte de Asistencia)")
 
     st.write(
         "Sube el archivo **1_report.xls** (o similar) que te da el reloj, "
         "sin modificarlo. La app va a leer la hoja **'Reporte de Asistencia'**, "
         "calcular horas, detectar faltas de marcas y generar el resumen de pago."
     )
 
     uploaded_file = st.file_uploader(
         "Archivo de reporte (.xls, .xlsx o .csv)",
         type=["xls", "xlsx", "csv"]
     )
 
     if uploaded_file is not None:
         try:
             # ---------- LEER ARCHIVO COMPLETO ----------
             nombre_archivo = uploaded_file.name.lower()
 
             if nombre_archivo.endswith(".csv"):
                 df_raw = pd.read_csv(uploaded_file, header=None)
             else:
                 # Forzamos hoja "Reporte de Asistencia"
                 xls = pd.ExcelFile(uploaded_file)
                 if "Reporte de Asistencia" not in xls.sheet_names:
                     st.error(
 
EOF
)




