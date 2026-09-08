from fastmcp import FastMCP
import requests
import sqlite3
import os
# Inicializamos el servidor
mcp = FastMCP("WorldBank_ETL")

# Detectar la carpeta real donde está este script y guardar la BD ahí
directorio_actual = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(directorio_actual, "datos_banco_mundial.db")

def init_db():
    """Inicializa la base de datos y crea la tabla si no existe."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metricas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pais TEXT,
            indicador TEXT,
            anio INTEGER,
            valor REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@mcp.tool()
def cargar_datos_api_a_db(indicador: str, pais: str, anio_inicio: int, anio_fin: int) -> str:
    """
    1. EXTRACCIÓN Y PERSISTENCIA (Ahorro de tokens)
    Descarga datos del Banco Mundial y los guarda directo en la BD local.
    El LLM NUNCA lee el JSON completo, solo recibe el mensaje de éxito.
    - indicador: ej. 'IT.NET.SECR' (servidores seguros), 'IT.NET.USER.ZS' (usuarios internet).
    - pais: Código ISO, ej. 'AR' (Argentina), 'BR' (Brasil).
    """
    url = f"http://api.worldbank.org/v2/country/{pais}/indicator/{indicador}"
    params = {"date": f"{anio_inicio}:{anio_fin}", "format": "json", "per_page": 200}
    
    try:
        respuesta = requests.get(url, params=params)
        datos = respuesta.json()
        
        if len(datos) > 1 and datos[1]:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            insertados = 0
            for registro in datos[1]:
                valor = registro.get('value')
                if valor is not None:
                    anio = int(registro['date'])
                    # Guardamos directo en disco. Esta herramienta SÍ tiene permisos de escritura.
                    cursor.execute(
                        "INSERT INTO metricas (pais, indicador, anio, valor) VALUES (?, ?, ?, ?)",
                        (pais, indicador, anio, valor)
                    )
                    insertados += 1
            
            conn.commit()
            conn.close()
            return f"Éxito: Se descargaron e insertaron {insertados} registros históricos en la tabla 'metricas'."
        
        return "No hay datos en la API para esa búsqueda."
    except Exception as e:
        return f"Error en la extracción: {str(e)}"

@mcp.tool()
def ejecutar_query_sql(query: str) -> str:
    """
    2. ANÁLISIS (Consumo eficiente y Seguro)
    Ejecuta consultas SQL de solo lectura. 
    SOLO se permiten comandos SELECT. Intentos de DELETE, DROP, UPDATE o INSERT serán bloqueados.
    La tabla es 'metricas' y sus columnas son: id, pais, indicador, anio, valor.
    """
    query_limpia = query.strip().upper()
    if not query_limpia.startswith("SELECT") and not query_limpia.startswith("WITH"):
        return "Error de seguridad: Esta herramienta es de solo lectura. Solo se permiten sentencias SELECT (o WITH para CTEs)."

    try:
        # Conexión estricta de solo lectura a nivel archivo
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        columnas = [desc[0] for desc in cursor.description]
        conn.close()
        
        if not resultados:
            return "La consulta se ejecutó correctamente pero no devolvió resultados."
            
        res_str = f"Columnas: {columnas}\n"
        for fila in resultados:
            res_str += f"{fila}\n"
        
        return res_str
        
    except sqlite3.OperationalError as e:
        return f"Error de SQLite (posible intento de escritura bloqueado): {str(e)}"
    except Exception as e:
        return f"Error SQL: {str(e)}"

@mcp.tool()
def guardar_reporte_disco(nombre_archivo: str, contenido: str) -> str:
    """
    3. EXPORTACIÓN
    Guarda el informe final estructurado en un archivo físico (.md, .csv, .html).
    """
    try:
        ruta_completa = os.path.join(os.getcwd(), nombre_archivo)
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return f"¡Reporte guardado con éxito en {ruta_completa}!"
    except Exception as e:
        return f"Error al guardar: {str(e)}"

@mcp.resource("estudios://fasta/maestria/plan")
def obtener_plan_estudios() -> str:
    """Recurso estático: Plan de estudios de la Maestría en Ciberseguridad e Informática Forense."""
    ruta_pdf = "C:/Users/famil/Downloads/Maia/MCP-1/Plan_de_estudios_2023-_Ingenieria-Online (1).pdf" 
    
    if not os.path.exists(ruta_pdf):
        return "Error: El archivo PDF del plan de estudios no se encontró en el servidor."
        
    try:
        lector_pdf = PdfReader(ruta_pdf)
        texto_extraido = "Plan de Estudios - Maestria\n\n"
        
        # Iteramos sobre todas las páginas para extraer el texto
        for pagina in lector_pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_extraido += texto + "\n"
                
        return texto_extraido
        
    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}"
if __name__ == "__main__":
    mcp.run()
