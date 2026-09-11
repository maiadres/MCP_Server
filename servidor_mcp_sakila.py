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
pool = psycopg2.pool.ThreadedConnectionPool(
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
    """Valida que la consulta sea una única operación de lectura."""
    consulta = query_sql.strip().rstrip(";").strip()
    if not consulta or ";" in consulta or "--" in consulta or "/*" in consulta:
        raise ValueError("Solo se permite una consulta SQL SELECT sin comentarios.")
    if not re.match(r"^SELECT\b", consulta, flags=re.IGNORECASE):
        raise ValueError("Solo se permiten consultas SELECT.")
    if re.search(
        r"\b(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|VACUUM|SET|SHOW)\b",
        consulta,
        re.IGNORECASE,
    ):
        raise ValueError("La consulta contiene una operación no permitida.")
    return consulta


@mcp.tool()
def obtener_esquema_base_datos() -> str:
    """Devuelve el esquema de las tablas públicas agrupado por tabla."""
    conexion = None
    try:
        conexion = pool.getconn()
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public';"
            )
            esquema: dict[str, list[dict[str, str]]] = {}
            for nombre_tabla, nombre_columna, tipo_dato in cursor.fetchall():
                esquema.setdefault(nombre_tabla, []).append(
                    {"column_name": nombre_columna, "data_type": tipo_dato}
                )
            return json.dumps(esquema, ensure_ascii=False, default=str)
    except psycopg2.Error as error:
        LOGGER.exception("Error al obtener el esquema de Sakila")
        return f"Error al obtener el esquema de la base de datos: {error}"
    finally:
        if conexion is not None:
            pool.putconn(conexion)


@mcp.tool()
def ejecutar_consulta_sql(consulta: str) -> str:
    """Ejecuta una consulta SELECT de solo lectura contra la base de datos."""
    try:
        consulta = validar_consulta(consulta)
    except ValueError as error:
        return f"Error de validación: {error}"

    conexion = None
    try:
        conexion = pool.getconn()
        conexion.autocommit = True
        with conexion.cursor() as cursor:
            cursor.execute(consulta)
            columnas = [columna[0] for columna in cursor.description]
            filas = cursor.fetchall()
            resultados = [dict(zip(columnas, fila)) for fila in filas]
            return json.dumps(resultados, ensure_ascii=False, default=str)
    except psycopg2.Error as error:
        LOGGER.exception("Error al ejecutar una consulta de Sakila")
        return f"Error al ejecutar la consulta SQL: {error}"
    finally:
        if conexion is not None:
            try:
                conexion.rollback()
            except psycopg2.Error:
                LOGGER.warning("No se pudo limpiar la conexión", exc_info=True)
            pool.putconn(conexion)


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        pool.closeall()
