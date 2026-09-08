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
        "port": "contra",
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

@mcp.tool()
def obtener_esquema_sakila() -> str:
    """
    Devuelve el esquema de las tablas principales de la base de datos Sakila.
    ÚSALO SIEMPRE ANTES de escribir consultas SQL para conocer la estructura y relaciones.
    """
    return """
    Tablas principales:
    - film (film_id, title, description, release_year, rating)
    - inventory (inventory_id, film_id, store_id)
    - rental (rental_id, rental_date, inventory_id, customer_id, return_date)
    - customer (customer_id, first_name, last_name, active)
    
    Relaciones clave:
    - 'inventory' se une con 'film' mediante film_id.
    - 'rental' se une con 'inventory' mediante inventory_id.
    - 'rental' se une con 'customer' mediante customer_id.
    """

@mcp.tool()
def ejecutar_consulta_sakila(query_sql: str) -> str:
    """
    Ejecuta una consulta SQL de solo lectura en Sakila.
    query_sql: La consulta SELECT estricta en formato PostgreSQL.
    """
    conexion_db = {
        "dbname": "sakila",
        "user": "postgres",
        "password": "TU_CONTRASEÑA", # Asegurate de mantener tu clave real acá
        "host": "localhost",
        "port": "5432", # Usá el puerto que te funcionó en la prueba anterior
        "client_encoding": "UTF-8"
    }
    
    # Bloqueo de seguridad para evitar modificaciones en la base
    if any(palabra in query_sql.upper() for palabra in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]):
        return "Error de seguridad: Solo se permiten operaciones de lectura (SELECT)."
        
    try:
        conn = psycopg2.connect(**conexion_db)
        cursor = conn.cursor()
        
        # Límite forzado para ahorrar tokens si la IA olvida ponerlo
        if "LIMIT" not in query_sql.upper():
            query_sql += " LIMIT 20"
            
        cursor.execute(query_sql)
        nombres_columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        resultados = [dict(zip(nombres_columnas, fila)) for fila in filas]
        return json.dumps(resultados, indent=2, default=str)
        
    except Exception as e:
        return f"Error al ejecutar SQL: {str(e)}"