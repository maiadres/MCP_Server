"""Servidor MCP para consultar películas mediante la API pública de Studio Ghibli."""

from typing import Any
import httpx
from uuid import UUID
from fastmcp import FastMCP


GHIBLI_API_BASE_URL = "https://ghibliapi.dev"
SOURCE_LANGUAGE = "en"
mcp = FastMCP("Studio Ghibli Movie API")


async def ghibli_get(endpoint: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Ejecuta una petición GET a la API pública de Studio Ghibli."""
    try:
        async with httpx.AsyncClient(base_url=GHIBLI_API_BASE_URL, timeout=10.0) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as error:
        raise RuntimeError("La API de Studio Ghibli tardó demasiado en responder.") from error
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            raise ValueError("No se encontró la película solicitada.") from error
        raise RuntimeError("La API de Studio Ghibli devolvió un error.") from error
    except httpx.RequestError as error:
        raise RuntimeError("No fue posible conectar con la API de Studio Ghibli.") from error


def resumir_pelicula(pelicula: dict[str, Any]) -> dict[str, str | None]:
    """Reduce una película de Ghibli a los campos relevantes para el modelo."""
    return {
        "id": pelicula.get("id"),
        "title": pelicula.get("title"),
        "release_date": pelicula.get("release_date"),
        "overview": pelicula.get("description"),
        "source_language": SOURCE_LANGUAGE,
    }


@mcp.tool()
async def search_ghibli_films(query: str) -> list[dict[str, str | None]]:
    """Busca películas de Studio Ghibli por título.

    La sinopsis de la fuente está en inglés. Al responder al usuario, tradúcela
    o resúmela en español sin modificar datos objetivos como título y año.

    Args:
        query: Título completo o parcial de la película buscada.

    Returns:
        Coincidencias con identificador, título, año de estreno y sinopsis.
    """
    texto = query.casefold().strip()
    if not texto:
        raise ValueError("query no puede estar vacío.")
    data = await ghibli_get("/films")
    peliculas: list[dict[str, Any]] = data if isinstance(data, list) else []
    coincidencias = [
        pelicula
        for pelicula in peliculas
        if texto in str(pelicula.get("title", "")).casefold()
        or texto in str(pelicula.get("original_title", "")).casefold()
    ]
    return [resumir_pelicula(pelicula) for pelicula in coincidencias[:10]]


@mcp.tool()
async def get_ghibli_film_details(film_id: str) -> dict[str, str | None]:
    """Obtiene los datos principales de una película de Studio Ghibli.

    La sinopsis de la fuente está en inglés. Al responder al usuario, tradúcela
    o resúmela en español sin modificar datos objetivos como título, año,
    director, duración y puntaje.

    Args:
        film_id: Identificador UUID obtenido con search_ghibli_films.

    Returns:
        Título, sinopsis, director, productor, año, duración y puntaje de Rotten Tomatoes.
    """
    try:
        UUID(film_id)
    except ValueError as error:
        raise ValueError("film_id debe ser un UUID válido devuelto por search_ghibli_films.") from error
    data = await ghibli_get(f"/films/{film_id}")
    pelicula: dict[str, Any] = data if isinstance(data, dict) else {}
    return {
        "id": pelicula.get("id"),
        "title": pelicula.get("title"),
        "overview": pelicula.get("description"),
        "director": pelicula.get("director"),
        "producer": pelicula.get("producer"),
        "release_date": pelicula.get("release_date"),
        "running_time_minutes": pelicula.get("running_time"),
        "rotten_tomatoes_score": pelicula.get("rt_score"),
        "source_language": SOURCE_LANGUAGE,
    }


@mcp.tool()
async def list_ghibli_films(
    year: int | None = None,
    min_score: int | None = None,
) -> list[dict[str, str | None]]:
    """Lista películas de Studio Ghibli con filtros opcionales de año y puntaje.

    Las sinopsis de la fuente están en inglés. Al responder al usuario,
    tradúcelas o resúmelas en español sin alterar los datos objetivos.

    Args:
        year: Año de estreno a filtrar, por ejemplo 2001.
        min_score: Puntaje mínimo de Rotten Tomatoes entre 0 y 100.

    Returns:
        Películas coincidentes en un formato resumido.
    """
    if min_score is not None and not 0 <= min_score <= 100:
        raise ValueError("min_score debe estar entre 0 y 100.")
    if year is not None and not 1900 <= year <= 2100:
        raise ValueError("year debe estar entre 1900 y 2100.")

    data = await ghibli_get("/films")
    peliculas: list[dict[str, Any]] = data if isinstance(data, list) else []
    coincidencias = [
        pelicula
        for pelicula in peliculas
        if (year is None or pelicula.get("release_date") == str(year))
        and (min_score is None or int(pelicula.get("rt_score", 0)) >= min_score)
    ]
    return [resumir_pelicula(pelicula) for pelicula in coincidencias]


if __name__ == "__main__":
    mcp.run()

