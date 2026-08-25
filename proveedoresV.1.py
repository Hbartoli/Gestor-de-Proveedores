import io
import sqlite3
import pandas as pd
import streamlit as st


# Configuración de la base de datos local
def conectar_db():
    conn = sqlite3.connect("proveedores.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
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
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO proveedores (nombre, plazo_pago_dias, dias_entrega, costo_envio, calificacion_calidad)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(nombre) DO UPDATE SET
                plazo_pago_dias=excluded.plazo_pago_dias,
                dias_entrega=excluded.dias_entrega,
                costo_envio=excluded.costo_envio,
                calificacion_calidad=excluded.calificacion_calidad
        """,
            (nombre, plazo, entrega, envio, calidad),
        )
        conn.commit()
    except Exception as e:
        st.error(f"Error al guardar en la base de datos: {e}")


def obtener_proveedores():
    return pd.read_sql_query("SELECT * FROM proveedores", conn)


def convertir_a_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Proveedores")
    return output.getvalue()


# --- INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="Gestor de Proveedores", layout="wide")
st.title("📦 Gestor Inteligente de Proveedores")

# Pestañas principales
tab1, tab2, tab3 = st.tabs(
    [
        "➕ Registro Individual",
        "📥 Carga Masiva (Excel)",
        "📊 Comparativa y Puntuación",
    ]
)

# TAB 1: REGISTRO INDIVIDUAL
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
                st.success(
                    f"Proveedor '{nombre}' procesado correctamente (Guardado/Actualizado)."
                )

# TAB 2: CARGA MASIVA DESDE EXCEL
with tab2:
    st.header("Subir Archivo de Excel")
    st.markdown(
        """
    **Instrucciones para la carga:**
    1. Descarga el reporte actual desde la pestaña de análisis para usarlo como plantilla, o crea un archivo con las siguientes columnas exactas:
    `Proveedor`, `Plazo Pago (Días)`, `Entrega (Días)`, `Costo Envío ($)`, `Calidad (1-5)`
    2. Modifica los datos o añade nuevas filas.
    3. Sube el archivo aquí abajo. El sistema añadirá los nuevos y actualizará los existentes si el nombre coincide.
    """
    )

    archivo_subido = st.file_uploader(
        "Elige tu archivo Excel (.xlsx)", type=["xlsx"]
    )

    if archivo_subido is not None:
        try:
            df_subido = pd.read_excel(archivo_subido)

            # Mapeo de columnas esperadas
            columnas_esperadas = {
                "Proveedor": "nombre",
                "Plazo Pago (Días)": "plazo",
                "Entrega (Días)": "entrega",
                "Costo Envío ($)": "envio",
                "Calidad (1-5)": "calidad",
            }

            # Validar que existan las columnas requeridas
            if not all(col in df_subido.columns for col in columnas_esperadas):
                st.error(
                    "❌ El archivo no tiene el formato correcto de columnas. Descarga la plantilla en la siguiente pestaña."
                )
            else:
                conteo_nuevos = 0
                for _, fila in df_subido.iterrows():
                    registrar_proveedor(
                        nombre=str(fila["Proveedor"]),
                        plazo=int(fila["Plazo Pago (Días)"]),
                        entrega=int(fila["Entrega (Días)"]),
                        envio=float(fila["Costo Envío ($)"]),
                        calidad=float(fila["Calidad (1-5)"]),
                    )
                    conteo_nuevos += 1

                st.success(
                    f"🎉 ¡Proceso completado! Se procesaron {conteo_nuevos} proveedores exitosamente."
                )
        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")

# TAB 3: COMPARATIVA Y METRICA PONDERADA
with tab3:
    st.header("Análisis Ponderado y Decisiones")

    df = obtener_proveedores()

    if df.empty:
        st.info("Aún no hay proveedores registrados.")
    else:
        # Configuración de Pesos de la Métrica Ponderada
        st.subheader("⚙️ Ajuste de Pesos (Prioridades del Negocio)")
        st.caption(
            "Distribuye la importancia de cada variable. La suma debe dar 100%."
        )

        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1:
            w_plazo = st.slider("Importancia Plazo Pago (%)", 0, 100, 30, step=5)
        with col_w2:
            w_entrega = st.slider(
                "Importancia Rapidez Entrega (%)", 0, 100, 30, step=5
            )
        with col_w3:
            w_envio = st.slider("Importancia Menor Costo (%)", 0, 100, 20, step=5)
        with col_w4:
            w_calidad = st.slider("Importancia Calidad (%)", 0, 100, 20, step=5)

        suma_pesos = w_plazo + w_entrega + w_envio + w_calidad

        if suma_pesos != 100:
            st.warning(
                f"⚠️ Los pesos suman {suma_pesos}%. Ajusta los valores para que sumen exactamente 100%."
            )

        # Copia para formatear datos
        df_mostrar = df.rename(
            columns={
                "nombre": "Proveedor",
                "plazo_pago_dias": "Plazo Pago (Días)",
                "dias_entrega": "Entrega (Días)",
                "costo_envio": "Costo Envío ($)",
                "calificacion_calidad": "Calidad (1-5)",
            }
        ).drop(columns=["id"])

        # --- CÁLCULO DE MÉTRICA PONDERADA (NORMALIZACIÓN MIN-MAX) ---
        # 1. Plazo de pago: Más es mejor
        max_plazo = (
            df_mostrar["Plazo Pago (Días)"].max()
            if df_mostrar["Plazo Pago (Días)"].max() != 0
            else 1
        )
        score_plazo = df_mostrar["Plazo Pago (Días)"] / max_plazo

        # 2. Entrega: Menos es mejor
        min_entrega = df_mostrar["Entrega (Días)"].min()
        max_entrega = df_mostrar["Entrega (Días)"].max()
        if max_entrega == min_entrega:
            score_entrega = 1.0
        else:
            score_entrega = (max_entrega - df_mostrar["Entrega (Días)"]) / (
                max_entrega - min_entrega
            )

        # 3. Costo Envío: Menos es mejor
        min_envio = df_mostrar["Costo Envío ($)"].min()
        max_envio = df_mostrar["Costo Envío ($)"].max()
        if max_envio == min_envio:
            score_envio = 1.0
        else:
            score_envio = (max_envio - df_mostrar["Costo Envío ($)"]) / (
                max_envio - min_envio
            )

        # 4. Calidad: Más es mejor (escala fija de 1 a 5)
        score_calidad = df_mostrar["Calidad (1-5)"] / 5.0

        # Cálculo Final de la Puntuación (Escala 1 a 100)
        df_mostrar["Puntuación Score"] = (
            (score_plazo * w_plazo)
            + (score_entrega * w_entrega)
            + (score_envio * w_envio)
            + (score_calidad * w_calidad)
        )
        df_mostrar["Puntuación Score"] = (
            df_mostrar["Puntuación Score"].round(1)
        )

        # Ordenar automáticamente por el mejor Score recalculado
        df_mostrar = df_mostrar.sort_values(
            by="Puntuación Score", ascending=False
        )

        # Botón de Descarga Excel (Mantiene el orden y añade el Score)
        st.subheader("📋 Tabla Comparativa")
        datos_excel = convertir_a_excel(df_mostrar)
        st.download_button(
            label="📥 Descargar Reporte Actual a Excel",
            data=datos_excel,
            file_name="analisis_proveedores.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Mostrar tabla interactiva
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

        # Gráfico dinámico basado en la puntuación
        st.subheader("📈 Ranking de Proveedores")
        st.bar_chart(data=df_mostrar, x="Proveedor", y="Puntuación Score")

