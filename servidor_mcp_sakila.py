"""Servidor MCP con acceso de solo lectura a la base de datos Sakila local."""

import json
import logging
import os
import re
from pathlib import Path
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.prompts import Message


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

pool = ConnectionPool(
    min_size=1,
    max_size=10,
    kwargs={
        "dbname": "sakila",
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": "localhost",
        "port": "5434",
        "client_encoding": "UTF-8",
    },
    open=True,
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
    try:
        with pool.connection() as conexion:
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
    except psycopg.Error as error:
        logger.exception("Error al obtener el esquema de la base de datos Sakila")
        return f"Error al obtener el esquema de la base de datos: {error}"


@mcp.tool()
def ejecutar_consulta_select(consulta: str) -> str:
    """Ejecuta una consulta SELECT segura y devuelve los resultados en JSON."""
    try:
        consulta = validar_consulta(consulta)
    except ValueError as error:
        return f"Error de validación: {error}"

    try:
        with pool.connection() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta)
                columnas = [columna[0] for columna in cursor.description]
                filas = cursor.fetchall()
                resultados = [dict(zip(columnas, fila)) for fila in filas]
                return json.dumps(resultados, ensure_ascii=False, default=str)
    except psycopg.Error as error:
        logger.exception("Error al ejecutar una consulta SQL de Sakila")
        return f"Error al ejecutar la consulta SQL: {error}"


@mcp.resource("politicas://{nombre_archivo}", mime_type="text/markdown")
def leer_politica(nombre_archivo: str) -> str:
    """Devuelve el contenido Markdown de una politica local."""
    if Path(nombre_archivo).name != nombre_archivo or Path(nombre_archivo).suffix != ".md":
        raise ValueError("El recurso debe identificar un archivo .md local.")

    ruta = Path(__file__).resolve().parent / "politicas" / "md_llm" / nombre_archivo
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontro la politica Markdown: {nombre_archivo}")

    return ruta.read_text(encoding="utf-8")


# Los servidores MCP conectan agentes y LLMs con herramientas y recursos del sistema.
# Estos prompts estandarizan las instrucciones para que las consultas a esas capacidades
# y la aplicación de las políticas sean consistentes.
@mcp.prompt()
def consultar_descuentos() -> str:
    """Genera instrucciones para determinar el descuento aplicable."""
    return (
        "Determina qué descuento corresponde a la situación o al cliente descrito "
        "por el usuario. Primero consulta la política de descuentos en el recurso "
        "`politicas://04_descuentos.md` y la política de clasificación por gasto "
        "en `politicas://01_clientes_gasto.md`. Si hacen falta datos del cliente, "
        "consúltalos con la herramienta `ejecutar_consulta_select`; no deduzcas "
        "el segmento con umbrales históricos, porque la política vigente usa "
        "percentiles de clientes activos. Asigna un único descuento según el "
        "segmento actual: Destacado 10%, Regular 5% o Bajo gasto 20%. Los "
        "descuentos no se acumulan. Explica el segmento, el descuento y el "
        "fundamento; si faltan datos para decidir, indícalo en lugar de asumirlos."
    )


@mcp.prompt()
def clasificar_actor(nombre_actor: str) -> str:
    """Genera instrucciones para clasificar un actor según la política vigente."""
    return (
        f"Clasifica al actor {nombre_actor!r} según la política de actores "
        "reconocidos del recurso `politicas://03_actores_reconocidos.md`. "
        "Consulta los datos actuales con `ejecutar_consulta_select` y aplica "
        "la métrica oficial de popularidad (alquileres de las películas en las "
        "que participa), ordenando los empates por ingresos y luego por id del "
        "actor. Usa los deciles definidos en la política: Estrella para el "
        "decil 1, Conocido para los deciles 2 a 4 y Secundario para los deciles "
        "5 a 10. Informa la categoría y la evidencia consultada; si no puedes "
        "identificar al actor o no hay datos suficientes, explícalo sin inventar "
        "una clasificación."
    )


@mcp.prompt()
def clasificar_consumidor(
    gasto_total: float | None = None,
    frecuencia: int | None = None,
) -> str:
    """Genera instrucciones para clasificar un consumidor según gasto y frecuencia."""
    if gasto_total is None and frecuencia is None:
        raise ValueError("Debes proporcionar gasto_total, frecuencia o ambos.")

    instrucciones = []
    if gasto_total is not None:
        instrucciones.append(
            f"Clasifica el gasto total de USD {gasto_total:.2f} consultando "
            "`politicas://01_clientes_gasto.md`. Aplica los percentiles actuales "
            "de clientes activos: Destacado es el 10% superior, Bajo gasto el "
            "10% inferior y Regular el resto; mantén juntos los empates. No "
            "trates los rangos monetarios históricos como cortes vigentes."
        )

    if frecuencia is not None:
        instrucciones.append(
            f"Clasifica la frecuencia de {frecuencia} alquileres consultando "
            "estrictamente `politicas://02_clientes_frecuencia.md`. Aplica los "
            "percentiles actuales sobre la cantidad de alquileres de clientes "
            "activos: Frecuente es el 10% superior, Ocasional el 10% inferior "
            "y Regular el resto; mantén juntos los empates y no uses los rangos "
            "observados como cortes vigentes."
        )

    instrucciones.append(
        "Usa `ejecutar_consulta_select` para contrastar el dato proporcionado "
        "con la distribución actual correspondiente."
    )
    if gasto_total is not None and frecuencia is not None:
        instrucciones.append(
            "Determina la categoría final combinando el segmento de gasto y "
            "el nivel de frecuencia, y explica ambos resultados y la conclusión."
        )
    else:
        instrucciones.append(
            "Determina la clasificación usando únicamente el criterio "
            "proporcionado y explica el resultado."
        )
    instrucciones.append(
        "Si no puedes obtener los percentiles actuales, indícalo en lugar de "
        "inventar una clasificación."
    )
    return " ".join(instrucciones)

if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        pool.close()
