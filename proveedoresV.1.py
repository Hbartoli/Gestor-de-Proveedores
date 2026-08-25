import io
import sqlite3
import pandas as pd
import streamlit as st


# Configuración de la base de datos
def conectar_db():
    conn = sqlite3.connect("proveedores.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            plazo_pago_dias INTEGER NOT NULL,
            dias_entrega INTEGER NOT NULL,
            costo_envio REAL DEFAULT 0.0,
            calificacion_calidad REAL DEFAULT 5.0
        )
    """
    )
    conn.commit()
    return conn


conn = conectar_db()


def registrar_proveedor(nombre, plazo, entrega, envio, calidad):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO proveedores (nombre, plazo_pago_dias, dias_entrega, costo_envio, calificacion_calidad)
        VALUES (?, ?, ?, ?, ?)
    """,
        (nombre, plazo, entrega, envio, calidad),
    )
    conn.commit()


def obtener_proveedores():
    return pd.read_sql_query("SELECT * FROM proveedores", conn)


# Función para convertir el DataFrame a un archivo Excel en memoria
def convertir_a_excel(df):
    output = io.BytesIO()
    # Usamos openpyxl como motor para generar el .xlsx
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Proveedores")
    return output.getvalue()


# --- INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="Gestor de Proveedores", layout="wide")
st.title("📦 Gestor y Comparador de Proveedores")

# Crear pestañas para organizar la app
tab1, tab2 = st.tabs(["➕ Registrar Proveedor", "📊 Comparativa y Análisis"])

with tab1:
    st.header("Agregar Nuevo Proveedor")
    with st.form("formulario_proveedor", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre de la empresa:")
            plazo = st.number_input(
                "Plazo de pago (días):", min_value=0, step=1, value=30
            )
            entrega = st.number_input(
                "Plazo de entrega (días):", min_value=0, step=1, value=5
            )
        with col2:
            envio = st.number_input(
                "Costo de envío ($):", min_value=0.0, step=10.0, value=0.0
            )
            calidad = st.slider(
                "Calificación de calidad:",
                min_value=1.0,
                max_value=5.0,
                value=5.0,
                step=0.1,
            )

        enviado = st.form_submit_button("Guardar Proveedor")
        if enviado:
            if nombre.strip() == "":
                st.error("El nombre del proveedor no puede estar vacío.")
            else:
                registrar_proveedor(nombre, plazo, entrega, envio, calidad)
                st.success(f"Proveedor '{nombre}' guardado correctamente.")

with tab2:
    st.header("Análisis de Condiciones")
    df = obtener_proveedores()

    if df.empty:
        st.info("Aún no hay proveedores registrados.")
    else:
        # Renombrar columnas para la visualización y reporte
        df_mostrar = df.rename(
            columns={
                "id": "ID",
                "nombre": "Proveedor",
                "plazo_pago_dias": "Plazo Pago (Días)",
                "dias_entrega": "Entrega (Días)",
                "costo_envio": "Costo Envío ($)",
                "calificacion_calidad": "Calidad (1-5)",
            }
        )

        # Filtros de ordenamiento interactivos
        criterio = st.selectbox(
            "Ordenar proveedores por:",
            [
                "ID (Orden de registro)",
                "Mejor Financiación (Mayor Plazo de Pago)",
                "Mayor Rapidez (Menor Tiempo de Entrega)",
                "Menor Costo de Envío",
                "Mayor Calidad",
            ],
        )

        if criterio == "Mejor Financiación (Mayor Plazo de Pago)":
            df_mostrar = df_mostrar.sort_values(
                by="Plazo Pago (Días)", ascending=False
            )
        elif criterio == "Mayor Rapidez (Menor Tiempo de Entrega)":
            df_mostrar = df_mostrar.sort_values(
                by="Entrega (Días)", ascending=True
            )
        elif criterio == "Menor Costo de Envío":
            df_mostrar = df_mostrar.sort_values(
                by="Costo Envío ($)", ascending=True
            )
        elif criterio == "Mayor Calidad":
            df_mostrar = df_mostrar.sort_values(
                by="Calidad (1-5)", ascending=False
            )

        # Zona de acciones: Mostrar tabla y botón de descarga alineados
        col_tabla, col_btn = st.columns([4, 1])

        with col_btn:
            st.write("")  # Espacio estético
            # Generar el archivo binario de Excel basado en el orden actual de la tabla
            datos_excel = convertir_a_excel(df_mostrar)

            st.download_button(
                label="📥 Descargar Excel",
                data=datos_excel,
                file_name="reporte_proveedores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # Mostrar tabla interactiva ocupando el ancho disponible
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

        # Gráfico comparativo rápido
        st.subheader("Visualización Comparativa")
        grafico_eje = st.radio(
            "Selecciona la métrica para el gráfico:",
            ["Plazo Pago (Días)", "Entrega (Días)", "Calidad (1-5)"],
            horizontal=True,
        )
        st.bar_chart(data=df_mostrar, x="Proveedor", y=grafico_eje)
