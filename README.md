# Integración de Sakila y Studio Ghibli

## 1. Descripción general

Este proyecto contiene dos servidores independientes basados en **Model Context
Protocol (MCP)**:

- **Sakila MCP** consulta una base PostgreSQL local.
- **Studio Ghibli MCP** consulta el catálogo de películas mediante HTTP.

Ambos servidores registran sus tools con FastMCP.

## 2. Estructura del proyecto

```text
MCP/
├── README.md
├── .env                         # Configuración local; no debe publicarse
├── .gitignore
├── servidor_mcp_sakila.py       # Servidor MCP para PostgreSQL/Sakila
├── servidor_mcp_ghibli_api.py   # Servidor MCP para Studio Ghibli
└── sakila/
    ├── postgres-sakila-schema.sql
    └── postgres-sakila-insert-data.sql
```

## 3. Tecnologías y transporte

| Tecnología | Uso |
|---|---|
| Python | Implementación de los servidores. El código usa sintaxis de Python 3.10 o superior. |
| FastMCP | Registro de las tools y ejecución del servidor MCP. |
| PostgreSQL | Base de datos Sakila. |
| psycopg2 | Driver y `ThreadedConnectionPool` para PostgreSQL. |
| httpx | Cliente HTTP asíncrono para la API de Studio Ghibli. |
| python-dotenv | Carga de variables desde `.env`. |

Los dos puntos de entrada llaman a `mcp.run()` sin especificar un transporte
explícito. La ejecución está pensada para un cliente MCP que inicie cada
proceso por `stdio`; este repositorio no implementa SSE ni Streamable HTTP.

## 4. Instalación y configuración

### Requisitos

- Python compatible con la sintaxis usada por el código (3.10 o superior).
- PostgreSQL con una base llamada `sakila`.
- Un cliente compatible con MCP que pueda iniciar procesos Python.

### Crear el entorno e instalar dependencias

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install fastmcp httpx psycopg2-binary python-dotenv
```

Si PowerShell bloquea la activación para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Cargar Sakila

Cree o seleccione la base `sakila` y ejecute estos archivos SQL en orden:

```text
sakila/postgres-sakila-schema.sql
sakila/postgres-sakila-insert-data.sql
```

El esquema SQL ya define tablas y vistas. No hay un paso separado de creación
de vistas requerido por los servidores.

### Variables de entorno

Cree `.env` en la raíz del proyecto:

```env
DB_PASSWORD=REEMPLAZAR_POR_UNA_CONTRASENA_SEGURA
DB_USER=sakila_mcp_readonly
```

| Variable | Obligatoria | Valor usado |
|---|---:|---|
| `DB_PASSWORD` | Sí | No tiene valor predeterminado. El servidor falla al iniciar si falta. |
| `DB_USER` | No | `sakila_mcp_readonly` si no se define. |

El servidor Sakila se conecta a `localhost`, base `sakila` y puerto `5434`.
Estos valores están fijados en `servidor_mcp_sakila.py` y no se configuran por
variables de entorno.

El código no crea usuarios ni permisos de PostgreSQL. Configure externamente
un usuario con los permisos necesarios y evite usar `postgres`. Tenga en cuenta
que el script de esquema incluido contiene `GRANT ALL ON SCHEMA public TO
PUBLIC`; por lo tanto, no debe interpretarse como una configuración de mínimo
privilegio lista para producción.

## 5. Ejecución

Servidor Sakila:

```powershell
python servidor_mcp_sakila.py
```

Servidor Studio Ghibli:

```powershell
python servidor_mcp_ghibli_api.py
```

También puede usar directamente el intérprete del entorno virtual:

```powershell
.\.venv\Scripts\python.exe .\servidor_mcp_sakila.py
.\.venv\Scripts\python.exe .\servidor_mcp_ghibli_api.py
```

Después de modificar un servidor, reinicie el proceso iniciado por el cliente
MCP.

## 6. Tools de Sakila

### `obtener_esquema_bd()`

No recibe parámetros. Consulta `information_schema.columns` para el esquema
`public` y devuelve un **string JSON** agrupado por tabla. Cada columna contiene
`column_name` y `data_type`.

Ejemplo:

```text
obtener_esquema_bd()
```

### `ejecutar_consulta_select(consulta)`

Recibe una consulta SQL como string y devuelve un **string JSON** con una lista
de diccionarios. La consulta debe:

- comenzar por `SELECT`, ignorando espacios y mayúsculas;
- ser una única sentencia;
- no contener comentarios `--` ni `/*`;
- no contener `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`,
  `TRUNCATE`, `GRANT`, `REVOKE`, `COPY`, `CALL`, `DO`, `VACUUM`, `SET` ni
  `SHOW`.

Se permite un punto y coma final, pero no múltiples sentencias. La tool no
aplica un límite automático de filas.

Ejemplo:

```text
ejecutar_consulta_select(
  "SELECT title, release_year, rating FROM film WHERE rating = 'PG' LIMIT 10"
)
```

Los errores de validación y de PostgreSQL se devuelven como texto. La conexión
se obtiene de un `ThreadedConnectionPool` con entre 1 y 10 conexiones.

## 7. Tools de Studio Ghibli

La API base está fijada en `https://ghibliapi.dev`. El catálogo resumido se
descarga con los campos `id`, `title`, `original_title`, `director`,
`release_date` y `rt_score`, y se conserva en memoria durante 300 segundos.

### `query_ghibli_films(...)`

Devuelve una lista con estos campos:

```json
[
  {
    "id": "uuid",
    "title": "Film title",
    "release_date": "2001",
    "rotten_tomatoes_score": 95
  }
]
```

Parámetros:

| Parámetro | Tipo | Default | Restricciones y comportamiento |
|---|---|---:|---|
| `title_contains` | `str \| None` | `None` | Busca el texto en `title` u `original_title`; no puede ser vacío. |
| `year` | `int \| None` | `None` | Entre 1980 y el año actual. |
| `min_score` | `int \| None` | `None` | Entre 0 y 100. |
| `max_score` | `int \| None` | `None` | Entre 0 y 100; no puede ser menor que `min_score`. |
| `sort_by` | `str` | `"rt_score"` | Solo `rt_score`, `release_date` o `title`. |
| `descending` | `bool` | `False` | Invierte el orden cuando es `True`. |
| `limit` | `int` | `50` | Entre 1 y 250. |
| `director` | `str \| None` | `None` | Filtra por coincidencia parcial; no puede ser vacío. |

Ejemplos:

```text
query_ghibli_films(title_contains="Totoro", limit=10)

query_ghibli_films(year=2001, min_score=90)

query_ghibli_films(sort_by="rt_score", descending=False, limit=5)
```

### `get_ghibli_film_details(film_id)`

Recibe `film_id` como string. Debe ser un UUID válido. Consulta
`/films/{film_id}` y devuelve:

```json
{
  "id": "uuid",
  "title": "Film title",
  "overview": "Original description",
  "director": "Director",
  "producer": "Producer",
  "running_time_minutes": 119,
  "original_title": "Original title",
  "original_title_romanised": "Romanised title",
  "url": "https://ghibliapi.dev/films/uuid",
  "source_language": "en"
}
```

Un UUID inválido produce un error de validación. Una respuesta HTTP 404 se
transforma en un error que indica que no se encontró la película. Los timeouts,
errores de conexión y otros errores HTTP se transforman en errores controlados.

## 8. Límites y seguridad

- La validación SQL es una defensa adicional; no sustituye los permisos de
  PostgreSQL.
- El usuario de PostgreSQL debe configurarse fuera del código y tener solo los
  permisos requeridos.
- Las credenciales solo se leen desde `DB_PASSWORD` y `DB_USER`; no las incluya
  en el código ni en el control de versiones.
- Sakila no limita automáticamente el número de filas devueltas.
- Ghibli usa un timeout HTTP de 10 segundos por solicitud.


