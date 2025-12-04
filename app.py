import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
from io import BytesIO
import base64

# Configuración de la página
st.set_page_config(
    page_title="Sistema Nómina Textil",
    page_icon="👕",
    layout="wide"
)

# Rutas de archivos (usando los archivos de tu repositorio)
EMPLEADOS_CSV = "empleados.csv"
REGISTROS_CSV = "registros_horas.csv"

# Cargar datos existentes o inicializar DataFrames vacíos
def cargar_datos():
    """Carga los datos de empleados y registros desde archivos CSV"""
    try:
        empleados_df = pd.read_csv(EMPLEADOS_CSV)
        # Asegurar que las columnas necesarias existan
        columnas_requeridas = ['ID', 'Nombre', 'Sueldo_Semanal', 'Sueldo_Diario', 'Sueldo_Hora', 'Fecha_Alta', 'Activo']
        for col in columnas_requeridas:
            if col not in empleados_df.columns:
                empleados_df[col] = np.nan
    except FileNotFoundError:
        # Crear DataFrame vacío con las columnas necesarias
        empleados_df = pd.DataFrame(columns=[
            'ID', 'Nombre', 'Sueldo_Semanal', 'Sueldo_Diario', 
            'Sueldo_Hora', 'Fecha_Alta', 'Activo'
        ])
    
    try:
        registros_df = pd.read_csv(REGISTROS_CSV)
        # Asegurar que las columnas necesarias existan
        columnas_registros = ['ID_Trabajador', 'Nombre', 'Fecha', 'Hora_Entrada', 
                              'Hora_Salida', 'Horas_Trabajadas', 'Minutos_Trabajados', 
                              'Total_Horas_Decimal']
        for col in columnas_registros:
            if col not in registros_df.columns:
                registros_df[col] = np.nan
    except FileNotFoundError:
        registros_df = pd.DataFrame(columns=[
            'ID_Trabajador', 'Nombre', 'Fecha', 'Hora_Entrada', 
            'Hora_Salida', 'Horas_Trabajadas', 'Minutos_Trabajados', 
            'Total_Horas_Decimal'
        ])
    
    return empleados_df, registros_df

# Guardar datos a CSV
def guardar_datos(empleados_df, registros_df):
    """Guarda los DataFrames a archivos CSV"""
    empleados_df.to_csv(EMPLEADOS_CSV, index=False)
    registros_df.to_csv(REGISTROS_CSV, index=False)

# Cargar datos al inicio
if 'datos_cargados' not in st.session_state:
    st.session_state.empleados, st.session_state.registros = cargar_datos()
    st.session_state.datos_cargados = True

# Título principal
st.title("👕 Sistema de Nómina - Maquiladora Textil")
st.markdown("---")

# Función para calcular sueldos según ley mexicana
def calcular_sueldos(sueldo_semanal):
    """Calcula sueldo diario y por hora según ley mexicana"""
    sueldo_diario = sueldo_semanal / 7
    sueldo_hora = sueldo_diario / 8
    return round(sueldo_diario, 2), round(sueldo_hora, 2)

# Función para procesar archivo Excel
def procesar_excel(uploaded_file):
    """Lee y procesa el archivo Excel del mostrador"""
    try:
        # Leer el archivo Excel
        df = pd.read_excel(uploaded_file)
        
        st.success(f"Archivo cargado: {uploaded_file.name}")
        st.write("Vista previa de datos:")
        st.dataframe(df.head())
        
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {str(e)}")
        return None

# Función para calcular horas trabajadas
def calcular_horas_trabajadas(entrada, salida):
    """Calcula horas y minutos trabajados"""
    if pd.isna(entrada) or pd.isna(salida):
        return 0, 0, 0
    
    # Convertir a datetime si son strings
    if isinstance(entrada, str):
        entrada = pd.to_datetime(entrada, errors='coerce')
    if isinstance(salida, str):
        salida = pd.to_datetime(salida, errors='coerce')
    
    if pd.isna(entrada) or pd.isna(salida):
        return 0, 0, 0
    
    # Calcular diferencia
    diferencia = salida - entrada
    horas = diferencia.seconds // 3600
    minutos = (diferencia.seconds % 3600) // 60
    
    # Convertir a horas decimales (ej: 8:30 = 8.5)
    total_decimal = horas + (minutos / 60)
    
    return horas, minutos, round(total_decimal, 2)

# Barra lateral para navegación
st.sidebar.title("📊 Navegación")
opcion = st.sidebar.radio(
    "Selecciona una opción:",
    ["🏠 Inicio", "👥 Alta de Trabajadores", "📤 Cargar Asistencia", 
     "📊 Reporte de Nómina", "💾 Exportar Datos", "⚙️ Configuración"]
)

# --- PÁGINA DE INICIO ---
if opcion == "🏠 Inicio":
    st.header("Bienvenido al Sistema de Nómina")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'Activo' in st.session_state.empleados.columns:
            trabajadores_activos = st.session_state.empleados[
                st.session_state.empleados['Activo'] == True
            ]
            st.metric("Trabajadores Activos", len(trabajadores_activos))
        else:
            st.metric("Trabajadores Activos", 0)
    
    with col2:
        st.metric("Registros de Asistencia", len(st.session_state.registros))
    
    with col3:
        if 'Total_Horas_Decimal' in st.session_state.registros.columns:
            total_horas = st.session_state.registros['Total_Horas_Decimal'].sum()
            st.metric("Horas Totales Trabajadas", f"{total_horas:.1f}")
        else:
            st.metric("Horas Totales Trabajadas", 0)
    
    st.markdown("---")
    st.subheader("📋 Instrucciones Rápidas")
    
    instrucciones = """
    1. **Alta de Trabajadores**: Registra a cada empleado con su sueldo base
    2. **Cargar Asistencia**: Sube el archivo Excel del mostrador
    3. **Reporte de Nómina**: Genera cálculos automáticos de horas y pagos
    4. **Exportar Datos**: Descarga reportes en Excel o CSV
    5. **Configuración**: Administra los archivos de datos
    """
    st.info(instrucciones)
    
    # Mostrar vista previa de datos
    with st.expander("📁 Vista previa de datos"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Empleados:**")
            st.dataframe(st.session_state.empleados.head(), use_container_width=True)
        with col2:
            st.write("**Registros recientes:**")
            st.dataframe(st.session_state.registros.head(), use_container_width=True)

# --- ALTA DE TRABAJADORES ---
elif opcion == "👥 Alta de Trabajadores":
    st.header("👥 Registro de Trabajadores")
    
    with st.form("form_trabajador"):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre completo del trabajador")
            sueldo_semanal = st.number_input(
                "Sueldo semanal ($)", 
                min_value=0.0, 
                value=2500.0,
                step=100.0
            )
        
        with col2:
            # Calcular automáticamente
            if sueldo_semanal > 0:
                sueldo_diario, sueldo_hora = calcular_sueldos(sueldo_semanal)
                st.metric("Sueldo Diario", f"${sueldo_diario:.2f}")
                st.metric("Sueldo por Hora", f"${sueldo_hora:.2f}")
        
        submitted = st.form_submit_button("Guardar Trabajador")
        
        if submitted and nombre:
            # Verificar si el nombre ya existe
            if nombre in st.session_state.empleados['Nombre'].values:
                st.error(f"❌ El trabajador {nombre} ya está registrado.")
            else:
                # Generar ID único
                if not st.session_state.empleados.empty and 'ID' in st.session_state.empleados.columns:
                    nuevo_id = st.session_state.empleados['ID'].max() + 1
                else:
                    nuevo_id = 1
                
                # Calcular sueldos
                sueldo_diario, sueldo_hora = calcular_sueldos(sueldo_semanal)
                
                # Crear nuevo registro
                nuevo_trabajador = pd.DataFrame([{
                    'ID': nuevo_id,
                    'Nombre': nombre,
                    'Sueldo_Semanal': sueldo_semanal,
                    'Sueldo_Diario': sueldo_diario,
                    'Sueldo_Hora': sueldo_hora,
                    'Fecha_Alta': datetime.date.today().strftime("%Y-%m-%d"),
                    'Activo': True
                }])
                
                # Agregar a la lista
                st.session_state.empleados = pd.concat(
                    [st.session_state.empleados, nuevo_trabajador],
                    ignore_index=True
                )
                
                # Guardar en CSV
                guardar_datos(st.session_state.empleados, st.session_state.registros)
                
                st.success(f"✅ Trabajador {nombre} registrado exitosamente!")
    
    st.markdown("---")
    st.subheader("📋 Lista de Trabajadores")
    
    if not st.session_state.empleados.empty:
        # Mostrar tabla de trabajadores
        trabajadores_display = st.session_state.empleados.copy()
        
        # Filtrar columnas si existen
        columnas_a_mostrar = ['ID', 'Nombre', 'Sueldo_Semanal', 'Sueldo_Diario', 
                              'Sueldo_Hora', 'Fecha_Alta', 'Activo']
        columnas_disponibles = [col for col in columnas_a_mostrar if col in trabajadores_display.columns]
        
        st.dataframe(
            trabajadores_display[columnas_disponibles],
            use_container_width=True,
            hide_index=True
        )
        
        # Opción para desactivar/activar trabajador
        with st.expander("🔧 Gestión de Trabajadores"):
            trabajadores_activos = st.session_state.empleados[
                (st.session_state.empleados['Activo'] == True) | 
                (pd.isna(st.session_state.empleados['Activo']))
            ]
            
            if not trabajadores_activos.empty:
                trabajador_a_editar = st.selectbox(
                    "Seleccionar trabajador para editar:",
                    options=trabajadores_activos['Nombre'].tolist()
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Desactivar Trabajador"):
                        idx = st.session_state.empleados[
                            st.session_state.empleados['Nombre'] == trabajador_a_editar
                        ].index[0]
                        st.session_state.empleados.at[idx, 'Activo'] = False
                        guardar_datos(st.session_state.empleados, st.session_state.registros)
                        st.success(f"Trabajador {trabajador_a_editar} desactivado")
                        st.rerun()
                    
                    # Mostrar estado actual
                    estado_actual = st.session_state.empleados[
                        st.session_state.empleados['Nombre'] == trabajador_a_editar
                    ]['Activo'].values[0]
                    st.write(f"Estado actual: {'Activo' if estado_actual else 'Inactivo'}")
                
                with col2:
                    # Actualizar sueldo
                    sueldo_actual = float(st.session_state.empleados[
                        st.session_state.empleados['Nombre'] == trabajador_a_editar
                    ]['Sueldo_Semanal'].values[0])
                    
                    nuevo_sueldo = st.number_input(
                        "Nuevo sueldo semanal",
                        value=sueldo_actual,
                        key="nuevo_sueldo"
                    )
                    
                    if st.button("Actualizar Sueldo"):
                        idx = st.session_state.empleados[
                            st.session_state.empleados['Nombre'] == trabajador_a_editar
                        ].index[0]
                        
                        st.session_state.empleados.at[idx, 'Sueldo_Semanal'] = nuevo_sueldo
                        sueldo_diario, sueldo_hora = calcular_sueldos(nuevo_sueldo)
                        st.session_state.empleados.at[idx, 'Sueldo_Diario'] = sueldo_diario
                        st.session_state.empleados.at[idx, 'Sueldo_Hora'] = sueldo_hora
                        
                        guardar_datos(st.session_state.empleados, st.session_state.registros)
                        
                        st.success("Sueldo actualizado!")
                        st.rerun()
    else:
        st.info("No hay trabajadores registrados. Agrega el primero usando el formulario arriba.")

# --- CARGAR ASISTENCIA ---
elif opcion == "📤 Cargar Asistencia":
    st.header("📤 Cargar Archivo de Asistencia")
    
    st.info("""
    **Formato esperado del archivo Excel:**
    - Columnas mínimas requeridas: 
      - Nombre del empleado
      - Fecha (formato reconocible)
      - Hora de entrada
      - Hora de salida
    """)
    
    # Uploader de archivo
    uploaded_file = st.file_uploader(
        "Sube el archivo Excel del mostrador",
        type=['xlsx', 'xls', 'csv']
    )
    
    if uploaded_file:
        # Determinar tipo de archivo
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"Archivo cargado: {uploaded_file.name}")
        st.write("Vista previa de datos:")
        st.dataframe(df.head())
        
        st.markdown("---")
        st.subheader("🔧 Configurar Columnas")
        
        # Mostrar columnas disponibles
        st.write("**Columnas en tu archivo:**")
        st.write(df.columns.tolist())
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            col_nombre = st.selectbox(
                "Columna con Nombres:",
                options=df.columns.tolist()
            )
        
        with col2:
            col_fecha = st.selectbox(
                "Columna con Fecha:",
                options=df.columns.tolist()
            )
        
        with col3:
            col_entrada = st.selectbox(
                "Columna Hora Entrada:",
                options=df.columns.tolist()
            )
        
        with col4:
            col_salida = st.selectbox(
                "Columna Hora Salida:",
                options=df.columns.tolist()
            )
        
        if st.button("Procesar Asistencia", type="primary"):
            with st.spinner("Procesando registros..."):
                nuevos_registros = []
                
                for idx, row in df.iterrows():
                    nombre = row[col_nombre]
                    fecha = row[col_fecha]
                    entrada = row[col_entrada]
                    salida = row[col_salida]
                    
                    # Calcular horas trabajadas
                    horas, minutos, total_decimal = calcular_horas_trabajadas(entrada, salida)
                    
                    # Buscar ID del trabajador
                    trabajador_info = st.session_state.empleados[
                        st.session_state.empleados['Nombre'] == nombre
                    ]
                    
                    id_trabajador = trabajador_info['ID'].values[0] if not trabajador_info.empty else None
                    
                    nuevo_registro = {
                        'ID_Trabajador': id_trabajador,
                        'Nombre': nombre,
                        'Fecha': fecha,
                        'Hora_Entrada': entrada,
                        'Hora_Salida': salida,
                        'Horas_Trabajadas': horas,
                        'Minutos_Trabajados': minutos,
                        'Total_Horas_Decimal': total_decimal
                    }
                    
                    nuevos_registros.append(nuevo_registro)
                
                # Agregar a registros existentes
                if nuevos_registros:
                    nuevos_df = pd.DataFrame(nuevos_registros)
                    st.session_state.registros = pd.concat(
                        [st.session_state.registros, nuevos_df],
                        ignore_index=True
                    )
                    
                    # Guardar en CSV
                    guardar_datos(st.session_state.empleados, st.session_state.registros)
                    
                    st.success(f"✅ {len(nuevos_registros)} registros procesados exitosamente!")
                    
                    # Mostrar resumen
                    st.subheader("📈 Resumen del Procesamiento")
                    st.dataframe(
                        nuevos_df.head(10),
                        use_container_width=True
                    )
    
    # Mostrar historial de registros
    if not st.session_state.registros.empty:
        st.markdown("---")
        st.subheader("📋 Historial de Registros")
        
        st.dataframe(
            st.session_state.registros,
            use_container_width=True
        )

# --- REPORTE DE NÓMINA ---
elif opcion == "📊 Reporte de Nómina":
    st.header("📊 Reporte de Nómina")
    
    if st.session_state.registros.empty:
        st.warning("No hay registros de asistencia para generar reporte.")
    else:
        # Seleccionar período
        col1, col2 = st.columns(2)
        
        with col1:
            # Convertir fecha a formato datetime para obtener min/max
            try:
                registros_fecha = st.session_state.registros.copy()
                registros_fecha['Fecha'] = pd.to_datetime(registros_fecha['Fecha'], errors='coerce')
                fecha_min = registros_fecha['Fecha'].min().date()
                fecha_max = registros_fecha['Fecha'].max().date()
            except:
                fecha_min = datetime.date.today()
                fecha_max = datetime.date.today()
            
            fecha_inicio = st.date_input(
                "Fecha inicio",
                value=fecha_min
            )
        
        with col2:
            fecha_fin = st.date_input(
                "Fecha fin",
                value=fecha_max
            )
        
        if st.button("Generar Reporte de Nómina", type="primary"):
            # Filtrar por fecha
            registros_filtrados = st.session_state.registros.copy()
            registros_filtrados['Fecha_dt'] = pd.to_datetime(registros_filtrados['Fecha'], errors='coerce').dt.date
            
            if fecha_inicio and fecha_fin:
                registros_filtrados = registros_filtrados[
                    (registros_filtrados['Fecha_dt'] >= fecha_inicio) &
                    (registros_filtrados['Fecha_dt'] <= fecha_fin)
                ]
            
            # Agrupar por trabajador
            resumen_nomina = []
            
            for nombre in registros_filtrados['Nombre'].unique():
                registros_trabajador = registros_filtrados[
                    registros_filtrados['Nombre'] == nombre
                ]
                
                # Obtener información del trabajador
                trabajador_info = st.session_state.empleados[
                    st.session_state.empleados['Nombre'] == nombre
                ]
                
                if not trabajador_info.empty:
                    sueldo_hora = trabajador_info['Sueldo_Hora'].values[0]
                    
                    # Calcular totales
                    total_horas = registros_trabajador['Total_Horas_Decimal'].sum()
                    total_pagar = total_horas * sueldo_hora
                    
                    resumen_nomina.append({
                        'Trabajador': nombre,
                        'Días Trabajados': len(registros_trabajador),
                        'Horas Totales': round(total_horas, 2),
                        'Sueldo por Hora': f"${sueldo_hora:.2f}",
                        'Total a Pagar': f"${total_pagar:.2f}",
                        'Período': f"{fecha_inicio} al {fecha_fin}"
                    })
            
            if resumen_nomina:
                df_resumen = pd.DataFrame(resumen_nomina)
                
                st.success(f"Reporte generado para {len(resumen_nomina)} trabajadores")
                
                # Mostrar reporte
                st.subheader("📋 Resumen de Nómina")
                st.dataframe(df_resumen, use_container_width=True)
                
                # Estadísticas
                col1, col2, col3 = st.columns(3)
                
                total_horas = df_resumen['Horas Totales'].sum()
                total_pagar = sum([
                    float(x.replace('$', '').replace(',', '')) 
                    for x in df_resumen['Total a Pagar']
                ])
                
                with col1:
                    st.metric("Total Trabajadores", len(resumen_nomina))
                
                with col2:
                    st.metric("Horas Totales", f"{total_horas:.1f}")
                
                with col3:
                    st.metric("Total a Pagar", f"${total_pagar:.2f}")
                
                # Gráfico de horas por trabajador
                st.subheader("📊 Distribución de Horas")
                chart_data = df_resumen[['Trabajador', 'Horas Totales']].copy()
                chart_data = chart_data.set_index('Trabajador')
                st.bar_chart(chart_data)
                
                # Opción para descargar reporte
                st.markdown("---")
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_resumen.to_excel(writer, sheet_name='Resumen_Nomina', index=False)
                    registros_filtrados.to_excel(writer, sheet_name='Detalle_Registros', index=False)
                
                st.download_button(
                    label="📥 Descargar Reporte Completo (Excel)",
                    data=output.getvalue(),
                    file_name=f"reporte_nomina_{fecha_inicio}_al_{fecha_fin}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("No hay datos para el período seleccionado.")

# --- EXPORTAR DATOS ---
elif opcion == "💾 Exportar Datos":
    st.header("💾 Exportar Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Exportar Trabajadores")
        if not st.session_state.empleados.empty:
            # Convertir a Excel
            output_trabajadores = BytesIO()
            with pd.ExcelWriter(output_trabajadores, engine='openpyxl') as writer:
                st.session_state.empleados.to_excel(writer, sheet_name='Trabajadores', index=False)
            
            st.download_button(
                label="📥 Descargar Lista de Trabajadores (Excel)",
                data=output_trabajadores.getvalue(),
                file_name=f"trabajadores_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # También ofrecer CSV
            csv_trabajadores = st.session_state.empleados.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Lista de Trabajadores (CSV)",
                data=csv_trabajadores,
                file_name=f"trabajadores_{datetime.date.today()}.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay trabajadores para exportar.")
    
    with col2:
        st.subheader("Exportar Asistencia")
        if not st.session_state.registros.empty:
            # Convertir a Excel
            output_asistencia = BytesIO()
            with pd.ExcelWriter(output_asistencia, engine='openpyxl') as writer:
                st.session_state.registros.to_excel(writer, sheet_name='Asistencia', index=False)
            
            st.download_button(
                label="📥 Descargar Registros de Asistencia (Excel)",
                data=output_asistencia.getvalue(),
                file_name=f"asistencia_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # También ofrecer CSV
            csv_asistencia = st.session_state.registros.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Registros de Asistencia (CSV)",
                data=csv_asistencia,
                file_name=f"asistencia_{datetime.date.today()}.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay registros de asistencia para exportar.")
    
    st.markdown("---")
    st.subheader("Generar Reporte Personalizado")
    
    # Opciones de reporte
    tipo_reporte = st.selectbox(
        "Tipo de reporte:",
        ["Resumen Semanal", "Resumen Mensual", "Detallado por Trabajador"]
    )
    
    if st.button("Generar Reporte Personalizado"):
        if not st.session_state.registros.empty:
            with st.spinner("Generando reporte..."):
                # Aquí puedes personalizar el reporte según el tipo seleccionado
                st.success("Reporte generado exitosamente!")
                
                # Ejemplo simple de reporte personalizado
                if tipo_reporte == "Resumen Semanal":
                    st.write("**Resumen Semanal**")
                    # Agregar lógica específica
                elif tipo_reporte == "Resumen Mensual":
                    st.write("**Resumen Mensual**")
                    # Agregar lógica específica
                else:
                    st.write("**Detallado por Trabajador**")
                    # Agregar lógica específica
        else:
            st.warning("No hay datos para generar el reporte.")

# --- CONFIGURACIÓN ---
elif opcion == "⚙️ Configuración":
    st.header("⚙️ Configuración del Sistema")
    
    st.subheader("📁 Archivos de Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Empleados:** {EMPLEADOS_CSV}")
        if os.path.exists(EMPLEADOS_CSV):
            file_size = os.path.getsize(EMPLEADOS_CSV) / 1024  # KB
            st.write(f"Tamaño: {file_size:.2f} KB")
            st.write(f"Registros: {len(st.session_state.empleados)}")
            
            with open(EMPLEADOS_CSV, "rb") as file:
                st.download_button(
                    label="Descargar Archivo de Empleados",
                    data=file,
                    file_name=EMPLEADOS_CSV,
                    mime="text/csv"
                )
        else:
            st.warning("Archivo no encontrado")
    
    with col2:
        st.write(f"**Registros de horas:** {REGISTROS_CSV}")
        if os.path.exists(REGISTROS_CSV):
            file_size = os.path.getsize(REGISTROS_CSV) / 1024  # KB
            st.write(f"Tamaño: {file_size:.2f} KB")
            st.write(f"Registros: {len(st.session_state.registros)}")
            
            with open(REGISTROS_CSV, "rb") as file:
                st.download_button(
                    label="Descargar Archivo de Registros",
                    data=file,
                    file_name=REGISTROS_CSV,
                    mime="text/csv"
                )
        else:
            st.warning("Archivo no encontrado")
    
    st.markdown("---")
    st.subheader("🔄 Mantenimiento")
    
    if st.button("Recargar Datos desde Archivos"):
        st.session_state.empleados, st.session_state.registros = cargar_datos()
        st.success("Datos recargados exitosamente!")
        st.rerun()
    
    st.warning("⚠️ **Zona de peligro**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Limpiar Registros de Asistencia"):
            st.session_state.registros = pd.DataFrame(columns=[
                'ID_Trabajador', 'Nombre', 'Fecha', 'Hora_Entrada', 
                'Hora_Salida', 'Horas_Trabajadas', 'Minutos_Trabajados', 
                'Total_Horas_Decimal'
            ])
            guardar_datos(st.session_state.empleados, st.session_state.registros)
            st.success("Registros de asistencia limpiados")
            st.rerun()
    
    with col2:
        if st.button("Restaurar Datos de Ejemplo"):
            # Crear datos de ejemplo
            empleados_ejemplo = pd.DataFrame([
                {
                    'ID': 1,
                    'Nombre': 'Juan Pérez',
                    'Sueldo_Semanal': 2800.00,
                    'Sueldo_Diario': 400.00,
                    'Sueldo_Hora': 50.00,
                    'Fecha_Alta': '2024-01-01',
                    'Activo': True
                },
                {
                    'ID': 2,
                    'Nombre': 'María García',
                    'Sueldo_Semanal': 3150.00,
                    'Sueldo_Diario': 450.00,
                    'Sueldo_Hora': 56.25,
                    'Fecha_Alta': '2024-01-01',
                    'Activo': True
                }
            ])
            
            st.session_state.empleados = empleados_ejemplo
            guardar_datos(st.session_state.empleados, st.session_state.registros)
            st.success("Datos de ejemplo restaurados")
            st.rerun()

# Pie de página
st.markdown("---")
st.caption("Sistema de Nómina para Maquiladora Textil © 2024")

# Nota: Para ejecutar la aplicación
st.sidebar.markdown("---")
st.sidebar.subheader("🛠 Instalación")
st.sidebar.code("""
pip install streamlit pandas openpyxl
streamlit run app.py
""")
