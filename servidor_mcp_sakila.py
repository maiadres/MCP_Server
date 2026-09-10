"""Servidor MCP de solo lectura para la base de datos local Sakila."""

import json
import logging
import os
import re
from typing import Any
import psycopg2
import psycopg2.pool
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Sakila MCP Server")

LOGGER = logging.getLogger(__name__)
DB_PASSWORD = os.getenv("DB_PASSWORD")
if not DB_PASSWORD:
    raise ValueError("La variable de entorno DB_PASSWORD es obligatoria.")

DB_USER = os.getenv("DB_USER", "sakila_mcp_readonly")
ALLOWED_VIEWS = {"vista_alquileres", "vista_catalogo"}
MAX_ROWS = 20

connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dbname="sakila",
    user=DB_USER,
    password=DB_PASSWORD,
    host="localhost",
    port="5434",
    client_encoding="UTF-8",
)


def validar_consulta(query_sql: str) -> str:
    """Permite un solo SELECT sobre las dos vistas autorizadas."""
    consulta = query_sql.strip().rstrip(";").strip()
    if not consulta or ";" in consulta or "--" in consulta or "/*" in consulta:
        raise ValueError("Solo se permite una consulta SQL SELECT sin comentarios.")
    if not re.match(r"^SELECT\b", consulta, flags=re.IGNORECASE):
        raise ValueError("Solo se permiten consultas SELECT simples.")
    if re.search(r"\b(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|VACUUM|SET|SHOW|pg_\w*)\b", consulta, re.IGNORECASE):
        raise ValueError("La consulta contiene una operación no permitida.")
    fuentes = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w.]*)", consulta, re.IGNORECASE)
    if not fuentes or any(fuente.lower().split(".")[-1] not in ALLOWED_VIEWS for fuente in fuentes):
        raise ValueError("Solo se permiten vista_alquileres y vista_catalogo.")
    limites = re.findall(r"\bLIMIT\s+(\d+)\b", consulta, re.IGNORECASE)
    if len(limites) > 1 or (limites and int(limites[0]) > MAX_ROWS):
        raise ValueError(f"LIMIT no puede superar {MAX_ROWS}.")
    return consulta if limites else f"{consulta} LIMIT {MAX_ROWS}"


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
def ejecutar_consulta_sakila(query_sql: str) -> list[dict[str, Any]] | dict[str, str]:
    """Ejecuta una consulta SQL de solo lectura contra las vistas de Sakila."""
    try:
        consulta = validar_consulta(query_sql)
    except ValueError as error:
        return {"error": str(error)}

    conexion = None
    try:
        conexion = connection_pool.getconn()
        conexion.autocommit = True
        with conexion.cursor() as cursor:
            cursor.execute(consulta)
            columnas = [columna[0] for columna in cursor.description]
            filas = cursor.fetchall()
            return json.loads(json.dumps([dict(zip(columnas, fila)) for fila in filas], default=str))
    except psycopg2.Error:
        LOGGER.exception("Error al ejecutar una consulta de Sakila")
        return {"error": "No fue posible ejecutar la consulta en Sakila."}
    finally:
        if conexion is not None:
            try:
                conexion.rollback()
            except psycopg2.Error:
                LOGGER.warning("No se pudo limpiar la conexión", exc_info=True)
            connection_pool.putconn(conexion)


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        connection_pool.closeall()
