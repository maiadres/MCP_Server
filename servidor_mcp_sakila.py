"""Servidor MCP de solo lectura para la base de datos local Sakila."""

import os
import json
import psycopg2
import psycopg2.pool
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Sakila MCP Server")

# Pool global reutilizable para las consultas recibidas por el servidor MCP.
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname="sakila",
    user="postgres",
    password=os.getenv("DB_PASSWORD", "TU_CONTRASEÑA"),
    host="localhost",
    port="5434",
    client_encoding="UTF-8",
)


@mcp.tool()
def leer_esquema_vistas() -> str:
    """La IA debe llamar esta herramienta antes de escribir SQL para Sakila.

    Devuelve el mapa de las únicas vistas permitidas para realizar consultas.
    """
    return (
        "Antes de escribir SQL, usa EXCLUSIVAMENTE estas dos vistas pre-calculadas: "
        "vista_alquileres (customer_id, customer_name, email, rental_date, "
        "return_date, film_title, category_name) y vista_catalogo (film_id, title, "
        "description, release_year, rating, category, language). "
        "No consultes otras tablas ni vistas."
    )


@mcp.tool()
def ejecutar_consulta_sakila(query_sql: str) -> str:
    """Ejecuta una consulta SQL de solo lectura contra las vistas de Sakila."""
    comandos_bloqueados = ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER")
    query_mayusculas = query_sql.upper()

    if any(comando in query_mayusculas for comando in comandos_bloqueados):
        return json.dumps(
            {"error": "Solo se permiten consultas de lectura; comando de mutación detectado."}
        )

    consulta = query_sql.rstrip().rstrip(";")
    if "LIMIT" not in query_mayusculas:
        consulta += " LIMIT 20"

    conexion = None
    try:
        conexion = connection_pool.getconn()
        with conexion.cursor() as cursor:
            cursor.execute(consulta)
            columnas = [columna[0] for columna in cursor.description]
            filas = cursor.fetchall()
            resultados = [dict(zip(columnas, fila)) for fila in filas]
            return json.dumps(resultados, default=str, ensure_ascii=False)
    except psycopg2.Error as error:
        return json.dumps({"error": str(error)}, ensure_ascii=False)
    finally:
        if conexion is not None:
            connection_pool.putconn(conexion)


if __name__ == "__main__":
    mcp.run()
