"""Servidor MCP para consultar películas mediante la API pública de Studio Ghibli."""

import asyncio
import time
from typing import Any, Literal
import httpx
from uuid import UUID
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuración del servidor MCP para Studio Ghibli
# ---------------------------------------------------------------------------
GHIBLI_API_BASE_URL = "https://ghibliapi.dev"
SOURCE_LANGUAGE = "en"
CACHE_TTL_SECONDS = 300

mcp = FastMCP("Studio Ghibli Movie API")

# Cache en memoria para evitar repetir la carga completa del catálogo.
_catalogo_cache: list[dict[str, Any]] | None = None
_catalogo_cache_expira_en = 0.0
_catalogo_cache_lock = asyncio.Lock()


async def ghibli_get(endpoint: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Obtiene datos de la API pública de Studio Ghibli."""
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


# ---------------------------------------------------------------------------
# Carga del catálogo y cache
# ---------------------------------------------------------------------------


async def get_film_catalog() -> list[dict[str, Any]]:
    """Devuelve el catálogo de películas en caché."""
    global _catalogo_cache, _catalogo_cache_expira_en

    ahora = time.monotonic()
    if _catalogo_cache is not None and ahora < _catalogo_cache_expira_en:
        return _catalogo_cache

    # Evita varias descargas simultáneas cuando la caché caduca.
    async with _catalogo_cache_lock:
        ahora = time.monotonic()
        if _catalogo_cache is not None and ahora < _catalogo_cache_expira_en:
            return _catalogo_cache

        data = await ghibli_get(
            "/films?fields=id,title,original_title,director,release_date,rt_score&limit=250"
        )
        _catalogo_cache = data if isinstance(data, list) else []
        _catalogo_cache_expira_en = time.monotonic() + CACHE_TTL_SECONDS
        return _catalogo_cache


# ---------------------------------------------------------------------------
# Helpers para normalizar y ordenar resultados
# ---------------------------------------------------------------------------

def summarize_film(film: dict[str, Any]) -> dict[str, Any]:
    """Devuelve un resumen compacto de la película."""
    return {
        "id": film.get("id"),
        "title": film.get("title"),
        "release_date": film.get("release_date"),
        "rotten_tomatoes_score": rt_score_value(film),
    }


def rt_score_value(film: dict[str, Any]) -> int:
    """Convierte el puntaje a entero para ordenar sin errores."""
    try:
        return int(film.get("rt_score", 0))
    except (TypeError, ValueError):
        return 0


def filter_and_sort_films(
    films: list[dict[str, Any]],
    title_contains: str | None,
    year: int | None,
    min_score: int | None,
    max_score: int | None,
    sort_by: Literal["rt_score", "release_date", "title"],
    descending: bool,
    limit: int,
    director: str | None,
) -> list[dict[str, Any]]:
    """Aplica filtros, orden y límite a la lista de películas."""
    text = title_contains.casefold().strip() if title_contains else None
    if title_contains is not None and not text:
        raise ValueError("title_contains no puede estar vacío.")
    director_text = director.casefold().strip() if director else None
    if director is not None and not director_text:
        raise ValueError("director no puede estar vacío.")

    matches = []
    for film in films:
        title = str(film.get("title", ""))
        original_title = str(film.get("original_title", ""))
        score = film.get("rt_score")
        score_value = rt_score_value(film)

        if text and text not in title.casefold() and text not in original_title.casefold():
            continue
        if director_text and director_text not in str(film.get("director", "")).casefold():
            continue
        if year is not None and film.get("release_date") != str(year):
            continue
        if min_score is not None and (score in (None, "") or score_value < min_score):
            continue
        if max_score is not None and (score in (None, "") or score_value > max_score):
            continue
        matches.append(film)

    if sort_by == "rt_score":
        matches.sort(key=rt_score_value, reverse=descending)
    elif sort_by == "release_date":
        matches.sort(
            key=lambda film: int(film.get("release_date", 0)),
            reverse=descending,
        )
    else:
        matches.sort(
            key=lambda film: str(film.get("title", "")).casefold(),
            reverse=descending,
        )

    return [summarize_film(film) for film in matches[:limit]]


# ---------------------------------------------------------------------------
# Tools públicas del servidor MCP
# ---------------------------------------------------------------------------

@mcp.tool()
async def query_ghibli_films(
    title_contains: str | None = None,
    year: int | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    sort_by: Literal["rt_score", "release_date", "title"] = "rt_score",
    descending: bool = False,
    limit: int = 50,
    director: str | None = None,
) -> list[dict[str, Any]]:
    """Busca películas livianamente y devuelve id, título, año y puntuación.

    Usá esta herramienta para filtrar o comparar películas y obtener sus ids.
    Para ver el director, la duración o la sinopsis, primero obtené el id aquí
    y después llamá a get_ghibli_film_details.
    """
    if year is not None and not 1900 <= year <= 2100:
        raise ValueError("year debe estar entre 1900 y 2100.")
    if min_score is not None and not 0 <= min_score <= 100:
        raise ValueError("min_score debe estar entre 0 y 100.")
    if max_score is not None and not 0 <= max_score <= 100:
        raise ValueError("max_score debe estar entre 0 y 100.")
    if min_score is not None and max_score is not None and min_score > max_score:
        raise ValueError("min_score no puede ser mayor que max_score.")
    if not 1 <= limit <= 250:
        raise ValueError("limit debe estar entre 1 y 250.")

    films = await get_film_catalog()
    return filter_and_sort_films(
        films,
        title_contains,
        year,
        min_score,
        max_score,
        sort_by,
        descending,
        limit,
        director,
    )

@mcp.tool()
async def get_ghibli_film_details(film_id: str) -> dict[str, Any]:
    """Devuelve la ficha completa de una película a partir de su id.

    Usá esta herramienta después de query_ghibli_films para consultar la
    sinopsis, el director, el productor, la duración y otros metadatos.
    """
    try:
        UUID(film_id)
    except ValueError as error:
        raise ValueError("film_id debe ser un UUID válido devuelto por query_ghibli_films.") from error

    data = await ghibli_get(f"/films/{film_id}")
    film: dict[str, Any] = data if isinstance(data, dict) else {}
    return {
        "id": film.get("id"),
        "title": film.get("title"),
        "overview": film.get("description"),
        "director": film.get("director"),
        "producer": film.get("producer"),
        "running_time_minutes": int(film["running_time"]) if film.get("running_time") else None,
        "original_title": film.get("original_title"),
        "original_title_romanised": film.get("original_title_romanised"),
        "url": film.get("url"),
        "source_language": SOURCE_LANGUAGE,
    }

if __name__ == "__main__":
    mcp.run()

