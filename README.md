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
├── .gitignore
├── servidor_mcp_sakila.py              # Servidor MCP para PostgreSQL/Sakila
├── servidor_mcp_ghibli_api.py           # Servidor MCP para Studio Ghibli
├── politicas/
│   ├── 00_indice.pdf                    # Índice de políticas, fuente PDF
│   ├── 01_clientes_gasto.pdf
│   ├── 02_clientes_frecuencia.pdf
│   ├── 03_actores_reconocidos.pdf
│   ├── 04_descuentos.pdf
│   ├── convert_pdfs_to_md_llm.py        # Conversor opcional de PDF a Markdown
│   └── md_llm/                          # Versiones Markdown expuestas como recursos
│       ├── 00_indice.md
│       ├── 01_clientes_gasto.md
│       ├── 02_clientes_frecuencia.md
│       ├── 03_actores_reconocidos.md
│       └── 04_descuentos.md
└── sakila/
    ├── postgres-sakila-schema.sql       # Esquema y objetos de Sakila
    └── postgres-sakila-insert-data.sql  # Datos iniciales
```

Los PDF son las fuentes de las políticas y los archivos `md_llm/` son sus
versiones en Markdown. El servidor Sakila expone estas últimas; no convierte
los PDF durante su ejecución. El archivo `.env` es local y no debe agregarse al
control de versiones.

## 3. Tecnologías y transporte

| Tecnología | Uso |
|---|---|
| Python | Implementación de los servidores. El código usa sintaxis de Python 3.10 o superior. |
| FastMCP | Registro de las tools y ejecución del servidor MCP. |
| PostgreSQL | Base de datos Sakila. |
| psycopg | Driver y `ConnectionPool` para PostgreSQL. |
| httpx | Cliente HTTP asíncrono para la API de Studio Ghibli. |
| python-dotenv | Carga de variables desde `.env`. |
| MarkItDown | Dependencia opcional para regenerar los Markdown desde los PDF. |

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
python -m pip install fastmcp httpx "psycopg[binary,pool]" python-dotenv
```

Si PowerShell bloquea la activación para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Cargar Sakila

Cree la base `sakila` en la instancia local de PostgreSQL que escucha en el
puerto `5434` y ejecute los archivos SQL en orden. Por ejemplo, con `psql` y
un rol administrador:

```powershell
createdb -U postgres -p 5434 sakila
psql -U postgres -p 5434 -d sakila -f .\sakila\postgres-sakila-schema.sql
psql -U postgres -p 5434 -d sakila -f .\sakila\postgres-sakila-insert-data.sql
```

El esquema SQL crea los objetos requeridos; no hay un paso separado de creación
de vistas requerido por los servidores. Los scripts contienen sentencias de
propiedad y permisos de PostgreSQL, por lo que la carga puede requerir un rol
con privilegios administrativos. Adapte el comando si su instalación o sus
credenciales son distintas.

Para volver a generar los Markdown a partir de los PDF, de forma opcional,
instale MarkItDown y ejecute el conversor:

```powershell
python -m pip install markitdown
python .\politicas\convert_pdfs_to_md_llm.py .\politicas
```

El conversor busca PDF directamente en el directorio indicado y guarda los
Markdown en `md_llm/`. Esta dependencia no es necesaria para ejecutar los
servidores MCP si los Markdown existentes son suficientes.

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
se obtiene de un `psycopg_pool.ConnectionPool` con entre 1 y 10 conexiones.
El filtro de la consulta es una validación adicional, no un analizador SQL
completo ni una frontera de permisos. Mantenga las credenciales de la base con
privilegios mínimos y no exponga la tool a usuarios no confiables sin controles
adicionales. No se limita automáticamente el número de filas devueltas.

### Recursos de políticas

El servidor registra cinco recursos Markdown con MIME type `text/markdown`:

| URI | Contenido |
|---|---|
| `politicas://00_indice.md` | Índice de políticas y guía de uso. |
| `politicas://01_clientes_gasto.md` | Clasificación de clientes por gasto. |
| `politicas://02_clientes_frecuencia.md` | Clasificación de clientes por frecuencia de alquiler. |
| `politicas://03_actores_reconocidos.md` | Clasificación de actores por popularidad. |
| `politicas://04_descuentos.md` | Descuentos según el segmento de gasto. |

Los recursos entregan las reglas documentadas en `politicas/md_llm/`; por sí
mismos no consultan la base ni calculan resultados actuales.

### Políticas de negocio

Las políticas definen reglas, no valores actuales. Para obtener nombres,
montos, rankings y segmentos vigentes hay que consultar Sakila con
`ejecutar_consulta_select`; los rangos que aparecen en los documentos son
observaciones de la medición original, no umbrales permanentes.

| Código | Regla |
|---|---|
| POL-01 | Para clientes activos, suma los pagos por cliente; quienes no tienen pagos cuentan con gasto cero. Destacado corresponde al 10% superior, Bajo gasto al 10% inferior y Regular al resto. Los empates se mantienen juntos, por lo que el porcentaje puede ser aproximado. |
| POL-02 | Para clientes activos, cuenta sus filas de alquiler. Frecuente es el 10% superior, Ocasional el 10% inferior y Regular el resto; también se mantienen juntos los empates. |
| POL-03 | La popularidad de un actor se mide por los alquileres de las películas en las que participa. Los empates se ordenan por ingresos y luego por ID. Estrella corresponde al decil 1, Conocido a los deciles 2–4 y Secundario a los deciles 5–10. Un alquiler cuenta completo para cada actor de la película. |
| POL-04 | Asigna un único descuento por segmento de gasto: Destacado 10%, Regular 5% y Bajo gasto 20%. No se acumulan descuentos. La combinación Bajo gasto + Ocasional tiene prioridad de contacto, pero no un porcentaje adicional. |

Las políticas aplican a clientes activos cuando así se indica y deben
calcularse con los datos actuales antes de comunicar resultados o descuentos.

### Prompts de Sakila

El servidor registra tres prompts MCP. Proporcionan instrucciones a un cliente
MCP/LLM; no ejecutan por sí solos las consultas ni aplican los descuentos:

| Prompt | Parámetros | Propósito |
|---|---|---|
| `consultar_descuentos()` | Ninguno | Si falta el criterio, solicita elegir gasto o frecuencia. Indica consultar clientes activos y sus métricas, y asignar el porcentaje solo según el segmento de gasto. |
| `clasificar_actor(nombre_actor)` | `nombre_actor: str` | Indica consultar la popularidad del actor, aplicar el desempate y los deciles de POL-03 e informar la evidencia sin inventar datos. |
| `clasificar_consumidor(gasto_total=None, frecuencia=None)` | `gasto_total: str \| None`, `frecuencia: str \| None` | Requiere al menos un valor. Indica comparar gasto y/o alquileres con los percentiles actuales; si se pasan ambos, pide explicar ambas clasificaciones y la conclusión. |

El prompt de descuentos guía la consulta con las tools SQL y especifica cómo
seleccionar ejemplos, y pide expresamente no leer ni invocar recursos MCP. Los
prompts de clasificación hacen referencia también a los recursos de políticas;
el agente cliente debe invocar las tools y recursos indicados para obtener
evidencia y reglas.

## 7. Tools de Studio Ghibli

La API base está fijada en `https://ghibliapi.dev`. El catálogo resumido se
descarga con los campos `id`, `title`, `original_title`, `director`,
`release_date` y `rt_score`, y se conserva en memoria durante 300 segundos.
El catálogo se solicita con un máximo de 250 películas. `query_ghibli_films`
devuelve resúmenes y ordena las películas sin puntuación al final cuando se
ordena por puntuación; `get_ghibli_film_details` obtiene la ficha completa
desde la API. La API externa debe estar disponible para actualizar el catálogo
y consultar detalles.

### Cliente HTTP y ciclo de vida

El servidor configura un `lifespan` con `@asynccontextmanager`. Al iniciar el
servidor se crea una única instancia compartida de `httpx.AsyncClient`, que se
reutiliza en las tools `query_ghibli_films` y `get_ghibli_film_details`.

El cliente se obtiene mediante el `Context` de FastMCP y permanece asociado al
estado del servidor durante toda su ejecución. Al finalizar el servidor, el
context manager llama automáticamente a `aclose()` para liberar las
conexiones HTTP. Esto evita crear y cerrar un cliente nuevo en cada solicitud.

La caché del catálogo y su bloqueo de acceso también forman parte del estado
del lifespan; por eso se comparten entre llamadas del mismo servidor sin usar
variables globales mutables.

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
| `director` | `str \| None` | `None` | Filtra por coincidencia parcial, sin distinguir mayúsculas; no puede ser vacío. |

La búsqueda de título también ignora mayúsculas. Si se establece un límite de
puntuación, las películas sin puntuación válida quedan excluidas. Al ordenar
por `rt_score`, las películas sin puntuación aparecen al final incluso cuando
se invierte el orden. La ordenación por `release_date` utiliza el año de
lanzamiento.

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
- La caché de Ghibli vive en memoria del proceso; se comparte entre sus
  solicitudes y se pierde cuando se reinicia el servidor.
- Los PDF de políticas y los archivos Sakila son material incluido en el
  repositorio; el proyecto no instala ni inicia PostgreSQL automáticamente.
