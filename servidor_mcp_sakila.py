"""Servidor MCP con acceso de solo lectura a la base de datos Sakila local."""

import json
import logging
import os
import re
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración del servidor y conexión a la base de datos
# ---------------------------------------------------------------------------

mcp = FastMCP("Sakila MCP Server")
logger = logging.getLogger(__name__)

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
    """Valida que la consulta sea segura y de solo lectura."""
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
def obtener_esquema_bd() -> str:
    """Devuelve el esquema público de la base de datos agrupado por tabla."""
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
        logger.exception("Error al obtener el esquema de la base de datos Sakila")
        return f"Error al obtener el esquema de la base de datos: {error}"
    finally:
        if conexion is not None:
            pool.putconn(conexion)


@mcp.tool()
def ejecutar_consulta_select(consulta: str) -> str:
    """Ejecuta una consulta SELECT segura y devuelve los resultados en JSON."""
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
        logger.exception("Error al ejecutar una consulta SQL de Sakila")
        return f"Error al ejecutar la consulta SQL: {error}"
    finally:
        if conexion is not None:
            try:
                conexion.rollback()
            except psycopg2.Error:
                logger.warning("No se pudo limpiar la conexión", exc_info=True)
            pool.putconn(conexion)


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        pool.closeall()
