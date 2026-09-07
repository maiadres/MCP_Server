from fastmcp import FastMCP
import psycopg2
import json

mcp = FastMCP("Servidor_Sakila")

@mcp.tool()
def buscar_peliculas(palabra_clave: str) -> str:
    """
    Busca películas en la base de datos Sakila por coincidencia en el título o descripción.
    
    IMPORTANTE: La base de datos Sakila almacena su información en INGLÉS. 
    Si el usuario realiza una solicitud en español (ej. "películas de acción" o "perros"), 
    DEBES traducir el concepto al inglés (ej. "action" o "dog") ANTES de pasarlo 
    como argumento a esta herramienta.
    
    palabra_clave: Término de búsqueda (obligatoriamente en inglés).
    """
    conexion_db = {
        "dbname": "sakila",
        "user": "postgres",
        "password": "1234", # Reemplazá por tu clave de pgAdmin
        "host": "localhost",
        "port": "5434",
        "client_encoding": "UTF8"
    }
    
    try:
        conn = psycopg2.connect(**conexion_db)
        cursor = conn.cursor()
        
        query = """
            SELECT title, release_year, rating, description 
            FROM film 
            WHERE title ILIKE %s OR description ILIKE %s
            LIMIT 10;
        """
        parametro = f"%{palabra_clave}%"
        cursor.execute(query, (parametro, parametro))
        
        nombres_columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not filas:
            return f"No se encontraron películas para la búsqueda: {palabra_clave}"
            
        resultados = [dict(zip(nombres_columnas, fila)) for fila in filas]
        return json.dumps(resultados, indent=2, default=str)
        
    except Exception as e:
        return f"Error en PostgreSQL: {str(e)}"