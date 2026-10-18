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

@mcp.resource("politicas://01_clientes_gasto.md", mime_type="text/markdown")
def leer_politica_clientes_gasto() -> str:
    """Devuelve la política Markdown de clasificación por gasto."""
    ruta = (
        Path(__file__).resolve().parent
        / "politicas"
        / "md_llm"
        / "01_clientes_gasto.md"
    )
    return ruta.read_text(encoding="utf-8")


@mcp.resource("politicas://00_indice.md", mime_type="text/markdown")
def leer_indice_politicas() -> str:
    """Devuelve el índice de las políticas Markdown disponibles."""
    ruta = (
        Path(__file__).resolve().parent
        / "politicas"
        / "md_llm"
        / "00_indice.md"
    )
    return ruta.read_text(encoding="utf-8")


@mcp.resource("politicas://02_clientes_frecuencia.md", mime_type="text/markdown")
def leer_politica_clientes_frecuencia() -> str:
    """Devuelve la política Markdown de clasificación por frecuencia."""
    ruta = (
        Path(__file__).resolve().parent
        / "politicas"
        / "md_llm"
        / "02_clientes_frecuencia.md"
    )
    return ruta.read_text(encoding="utf-8")


@mcp.resource("politicas://03_actores_reconocidos.md", mime_type="text/markdown")
def leer_politica_actores_reconocidos() -> str:
    """Devuelve la política Markdown de actores reconocidos."""
    ruta = (
        Path(__file__).resolve().parent
        / "politicas"
        / "md_llm"
        / "03_actores_reconocidos.md"
    )
    return ruta.read_text(encoding="utf-8")


@mcp.resource("politicas://04_descuentos.md", mime_type="text/markdown")
def leer_politica_descuentos() -> str:
    """Devuelve la política Markdown de descuentos."""
    ruta = (
        Path(__file__).resolve().parent
        / "politicas"
        / "md_llm"
        / "04_descuentos.md"
    )
    return ruta.read_text(encoding="utf-8")


# Los servidores MCP conectan agentes y LLMs con herramientas y recursos del sistema.
# Estos prompts estandarizan las instrucciones para que las consultas a esas capacidades
# y la aplicación de las políticas sean consistentes.
@mcp.prompt()
def consultar_descuentos() -> str:
    """Consulta descuentos disponibles según el gasto y la política vigente."""
    return (
        "Tu propósito es consultar y ofrecer los tipos de descuentos disponibles "
        "según la política vigente, junto con ejemplos de clientes a quienes se "
        "pueden aplicar, usando exclusivamente el gasto como criterio. Si el "
        "usuario todavía no indicó una consulta por gasto, solicita el monto "
        "gastado o los clientes cuyo descuento desea consultar. No ofrezcas la "
        "frecuencia como opción ni la uses para seleccionar, filtrar o clasificar "
        "clientes. Si el usuario solicita consultar por frecuencia, explica que "
        "los descuentos se determinan únicamente por gasto y pídele reformular "
        "la consulta por gasto; no consultes la base de datos hasta tener ese "
        "criterio.\n\n"
        "No leas ni invoques recursos MCP para responder. Obtén los datos actuales "
        "con las herramientas: usa `ejecutar_consulta_select` para consultar el "
        "gasto total de clientes activos; si necesitas confirmar tablas o columnas, "
        "usa `obtener_esquema_bd`. Calcula la suma de pagos por cliente desde "
        "`payment`, incluyendo con valor cero a los clientes activos sin pagos. "
        "Clasifica con los percentiles actuales de gasto de los clientes activos "
        "y mantén juntos los empates. No uses como cortes vigentes los rangos "
        "monetarios observados. No consultes ni uses la frecuencia de alquileres. "
        "No inventes clientes ni resultados.\n\n"
        "La política de descuentos asigna el porcentaje por segmento de gasto, no "
        "por frecuencia: Destacado recibe 10% (descuento por fidelidad), Regular "
        "5% (descuento base) y Bajo gasto 20% (descuento incentivo). Usa "
        "`ejecutar_consulta_select` también para obtener el segmento de gasto de "
        "los clientes de ejemplo, ya que ese segmento determina su descuento. "
        "Informa únicamente los tipos de descuento correspondientes a los clientes "
        "encontrados y muestra ejemplos con el gasto total, su segmento de gasto y "
        "el descuento aplicable. No acumules descuentos. Si las herramientas no "
        "permiten determinar un descuento, explica qué dato falta en vez de asumirlo."
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
    gasto_total: str | None = None,
    frecuencia: str | None = None,
    nombre_cliente: str | None = None,
) -> str:
    """Genera instrucciones para clasificar un consumidor según sus datos."""
    if gasto_total is None and frecuencia is None and nombre_cliente is None:
        return (
            "Antes de consultar la base de datos, solicita al usuario al menos "
            "uno de estos datos: el nombre del cliente para buscar y clasificar "
            "sus métricas actuales, el gasto total para clasificar por gasto o "
            "la cantidad de alquileres para clasificar por frecuencia. Si "
            "proporciona solo el nombre, consulta y clasifica tanto su gasto "
            "como su frecuencia. No inventes datos ni una clasificación."
        )

    instrucciones = []
    solo_nombre = (
        nombre_cliente is not None
        and gasto_total is None
        and frecuencia is None
    )
    consultar_gasto = gasto_total is not None or solo_nombre
    consultar_frecuencia = frecuencia is not None or solo_nombre

    if nombre_cliente is not None:
        instrucciones.append(
            f"Identifica al cliente {nombre_cliente!r} consultando la tabla "
            "`customer` por `first_name` y `last_name`, sin distinguir "
            "mayúsculas y minúsculas. Si hay varios resultados posibles, "
            "solicita aclaración; no elijas uno arbitrariamente. Si no hay "
            "coincidencia activa, indícalo sin clasificar. Limita las métricas "
            "del cliente objetivo al `customer_id` encontrado, pero calcula los "
            "percentiles sobre todos los clientes activos."
        )

    if consultar_gasto:
        if gasto_total is not None:
            gasto_total_numerico = float(gasto_total)
            instruccion_gasto = (
                f"Clasifica el gasto total de USD {gasto_total_numerico:.2f} "
            )
        else:
            instruccion_gasto = (
                "Obtén y clasifica el gasto total actual del cliente "
            )
        instrucciones.append(
            instruccion_gasto
            + "consultando "
            "`politicas://01_clientes_gasto.md`. Aplica los percentiles actuales "
            "de clientes activos: Destacado es el 10% superior, Bajo gasto el "
            "10% inferior y Regular el resto; mantén juntos los empates. No "
            "trates los rangos monetarios históricos como cortes vigentes."
        )

    if consultar_frecuencia:
        if frecuencia is not None:
            frecuencia_numerica = int(frecuencia)
            instruccion_frecuencia = (
                f"Clasifica la frecuencia de {frecuencia_numerica} alquileres "
            )
        else:
            instruccion_frecuencia = (
                "Obtén y clasifica la frecuencia actual de alquileres del cliente "
            )
        instrucciones.append(
            instruccion_frecuencia
            + "consultando "
            "estrictamente `politicas://02_clientes_frecuencia.md`. Aplica los "
            "percentiles actuales sobre la cantidad de alquileres de clientes "
            "activos: Frecuente es el 10% superior, Ocasional el 10% inferior "
            "y Regular el resto; mantén juntos los empates y no uses los rangos "
            "observados como cortes vigentes."
        )

    instrucciones.append(
        "Usa `ejecutar_consulta_select` para obtener las métricas solicitadas "
        "y contrastar el dato proporcionado o consultado con la distribución "
        "actual correspondiente."
    )
    if consultar_gasto and consultar_frecuencia:
        instrucciones.append(
            "Determina la categoría final combinando el segmento de gasto y "
            "el nivel de frecuencia, y explica ambos resultados y la conclusión."
        )
    else:
        instrucciones.append(
            "Determina la clasificación usando únicamente el criterio "
            "solicitado y explica el resultado."
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
