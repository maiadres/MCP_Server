# Integración de Sakila y Studio Ghibli

## 1. Descripción general

Este proyecto contiene dos servidores independientes basados en **Model Context
Protocol (MCP)**:

- **Sakila MCP** consulta la base PostgreSQL `sakila` del servicio `postgres`
  de Docker Compose.
- **Studio Ghibli MCP** consulta el catálogo de películas mediante HTTP.

Ambos servidores registran sus primitivas con FastMCP.

## 2. Estructura del proyecto

```text
MCP/
├── README.md
├── mcp-config.json
├── .gitignore
├── .env.example                         # Variables para Docker Compose
├── docker-compose.yml
├── servidor_ghibli/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── servidor_mcp_ghibli_api.py
└── servidor_sakila/
    ├── Dockerfile
    ├── requirements.txt
    ├── servidor_mcp_sakila.py
    ├── politicas/                       # Políticas y recursos Markdown
    └── sakila/
        ├── 01-postgres-sakila-schema.sql
        ├── 02-postgres-sakila-insert-data.sql
        └── 03-usuario-mcp.sh
```

Los PDF son las fuentes de las políticas de sakila y los archivos
`servidor_sakila/politicas/md_llm/` son sus versiones en Markdown. El servidor
Sakila expone estas últimas; no convierte los PDF durante su ejecución.

## 3. Tecnologías y transporte

| Tecnología | Uso |
|---|---|
| Python | Implementación de los servidores. El código requiere Python 3.11 o superior. |
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

- Docker Desktop instalado y abierto.
- Un cliente compatible con MCP y transporte `stdio`.
- Docker Compose, que permite definir y ejecutar PostgreSQL y los servidores
  como servicios de contenedores con una configuración común. En Docker Desktop
  se usa mediante `docker compose`.

Compruebe que Docker y Compose estén disponibles:

```sh
docker --version
docker compose version
```

El servidor Sakila consulta la base PostgreSQL `sakila` y ofrece herramientas
de consulta de solo lectura, además de recursos y prompts. El
servidor Studio Ghibli consulta la API pública de películas: permite buscar y
filtrar el catálogo, y obtener los detalles de las películas.

Para ejecutar los servidores directamente con Python, de forma opcional,
instale las dependencias desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\servidor_sakila\requirements.txt
python -m pip install -r .\servidor_ghibli\requirements.txt
```

La ejecución directa del servidor Sakila también requiere una base accesible y las variables de
conexión correspondientes.

Para regenerar opcionalmente los Markdown de políticas a partir de sus PDF,
instale MarkItDown y ejecute el conversor:

```powershell
python -m pip install markitdown
python .\servidor_sakila\politicas\convert_pdfs_to_md_llm.py .\servidor_sakila\politicas
```

Esta dependencia no es necesaria para ejecutar los servidores si los Markdown
existentes son suficientes.

### Variables de entorno

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CAMBIAR_POR_UNA_CONTRASENA_SEGURA
DB_USER=sakila_mcp_readonly
DB_PASSWORD=contrasena
```

| Variable | Uso |
|---|---|
| `POSTGRES_USER` | Usuario superusuario creado por la imagen de PostgreSQL; en el ejemplo es `postgres`. |
| `POSTGRES_PASSWORD` | Contraseña de ese superusuario. |
| `DB_USER` | Nombre del rol de solo lectura que se crea para Sakila; en el ejemplo es `sakila_mcp_readonly`. |
| `DB_PASSWORD` | Contraseña del rol de solo lectura. |

El servicio `postgres` usa `POSTGRES_USER` y `POSTGRES_PASSWORD` para la
inicialización de PostgreSQL. El script `03-usuario-mcp.sh` crea `DB_USER` con
`DB_PASSWORD` y le concede permisos de lectura. El servicio `sakila_server`
recibe esas credenciales de solo lectura como `POSTGRES_USER` y
`POSTGRES_PASSWORD`; dentro de Compose, se conecta a `postgres:5432`. El
healthcheck y el comando de verificación del Compose usan el nombre `postgres`,
que es el valor de `POSTGRES_USER` del archivo de ejemplo.
Dentro del contenedor `sakila_server`, `POSTGRES_USER` y `POSTGRES_PASSWORD`
son las credenciales de solo lectura (`DB_USER` y `DB_PASSWORD`), no las del
superusuario: el código del servidor lee esos nombres de variables.

### Carga de la base

Al inicializar un volumen de datos vacío, PostgreSQL ejecuta los archivos de
`servidor_sakila/sakila` en orden alfabético: `01-postgres-sakila-schema.sql`
crea el esquema, `02-postgres-sakila-insert-data.sql` carga los datos y
`03-usuario-mcp.sh` crea el usuario de solo lectura. Los scripts de
`/docker-entrypoint-initdb.d` solo se ejecutan cuando el directorio de datos
está vacío.

### Puesta en marcha

1. Copie el archivo de ejemplo a `.env` desde la raíz del proyecto y cambie
   ambas contraseñas de ejemplo:

   ```powershell
   Copy-Item .env.example .env
   ```

   En macOS o Linux:

   ```sh
   cp .env.example .env
   ```

2. Construya las imágenes:

   ```sh
   docker compose build
   ```

3. Inicie PostgreSQL:

   ```sh
   docker compose up -d postgres
   ```

4. Compruebe los registros y las tablas:

   ```sh
   docker compose logs postgres
   docker compose exec postgres psql -U postgres -d sakila -c "\dt"
   ```

   También puede conectarse a PostgreSQL desde pgAdmin con host `localhost`,
   puerto `5433`, usuario `postgres` y la contraseña definida en
   `POSTGRES_PASSWORD`.

5. Pruebe cada servidor MCP con `docker compose run --rm -T <servicio>`:

   ```sh
   docker compose run --rm -T sakila_server
   docker compose run --rm -T ghibli_server
   ```

   El proceso usa `stdio`;
   
### Configuración del cliente MCP (`stdio`)

Agregue la configuración al archivo MCP que use el cliente; el formato y la
ubicación varían según el cliente. Por ejemplo, VS Code usa `.vscode/mcp.json`
con la propiedad `servers`, mientras que clientes que admiten `mcpServers`
usan esa propiedad en su configuración. Reemplace `RUTA/AL/PROYECTO` por la
ruta absoluta del proyecto. Para un cliente con formato `mcpServers`:

```json
{
  "mcpServers": {
    "sakila": {
      "command": "docker",
      "args": [
        "compose", "-f", "RUTA/AL/PROYECTO/docker-compose.yml",
        "run", "--rm", "-T", "sakila_server"
      ]
    },
    "ghibli": {
      "command": "docker",
      "args": [
        "compose", "-f", "RUTA/AL/PROYECTO/docker-compose.yml",
        "run", "--rm", "-T", "ghibli_server"
      ]
    }
  }
}
```

En VS Code, el mismo comando se configura en `.vscode/mcp.json` con este
formato:

```json
{
  "servers": {
    "sakila": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "compose", "-f", "RUTA/AL/PROYECTO/docker-compose.yml",
        "run", "--rm", "-T", "sakila_server"
      ]
    },
    "ghibli": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "compose", "-f", "RUTA/AL/PROYECTO/docker-compose.yml",
        "run", "--rm", "-T", "ghibli_server"
      ]
    }
  }
}
```

Guarde el archivo y reinicie el cliente MCP para que cargue la configuración.
Tras cambiar código Python, ejecute `docker compose build` de nuevo antes de
reiniciar el cliente para que use las imágenes actualizadas.

### Comandos útiles

```sh
docker compose ps
docker compose logs -f
docker compose down
docker compose down -v
```

`docker compose down -v` también elimina el volumen `mcp_pg_data` y, con él,
los datos guardados de PostgreSQL.

### Solución de problemas

| Problema | Solución |
|---|---|
| `connection refused` al conectar con PostgreSQL | Desde el equipo host use `localhost:5433`; desde un contenedor, el host es `postgres` y el puerto `5432`. Compruebe que PostgreSQL esté listo con `docker compose logs postgres`. |
| `role does not exist` | Compruebe que `DB_USER` y `DB_PASSWORD` coincidan con el rol esperado. Los scripts de inicialización solo crean el rol al inicializar un volumen vacío; para volver a ejecutarlos, `docker compose down -v` elimina los datos y después `docker compose up -d postgres` crea un volumen nuevo. |
| Las tablas aparecen vacías | Los SQL solo se ejecutan cuando el volumen está vacío. Para volver a cargarlos, ejecute `docker compose down -v` y luego `docker compose up -d postgres`. Esto borra permanentemente los datos guardados. |
| El cliente agota el tiempo de espera al iniciar el servidor | Ejecute `docker compose build` antes de iniciar el cliente y confirme que la construcción termine correctamente. Hay que volver a hacer build después de cambiar código Python. |
| Error de protocolo MCP | No escriba mensajes de depuración con `print()` en `stdout`, porque está reservado para el protocolo MCP. Envíe los mensajes de diagnóstico a `stderr`. |

## 5. Ejecución

Servidor Sakila:

```powershell
python .\servidor_sakila\servidor_mcp_sakila.py
```

Servidor Studio Ghibli:

```powershell
python .\servidor_ghibli\servidor_mcp_ghibli_api.py
```

También puede usar directamente el intérprete del entorno virtual:

```powershell
.\.venv\Scripts\python.exe .\servidor_sakila\servidor_mcp_sakila.py
.\.venv\Scripts\python.exe .\servidor_ghibli\servidor_mcp_ghibli_api.py
```

La ejecución directa requiere las dependencias de los respectivos archivos
`requirements.txt` y una base Sakila accesible con las credenciales de entorno
esperadas por el servidor. Para Docker Compose, siga la puesta en marcha
anterior. Al ejecutar directamente, reinicie el proceso tras cambiar el código;
con Docker Compose, vuelva a hacer build y reinicie el cliente MCP.

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

Los recursos entregan las reglas documentadas en
`servidor_sakila/politicas/md_llm/`; por sí mismos no consultan la base ni
calculan resultados actuales.

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
| `consultar_descuentos()` | Ninguno | Consulta exclusivamente por gasto. Si se solicita una consulta por frecuencia, indica que los descuentos se determinan por gasto y pide reformular la consulta; asigna el porcentaje según el segmento de gasto. |
| `clasificar_actor(nombre_actor)` | `nombre_actor: str` | Indica consultar la popularidad del actor, aplicar el desempate y los deciles de POL-03 e informar la evidencia sin inventar datos. |
| `clasificar_consumidor(gasto_total=None, frecuencia=None, nombre_cliente=None)` | `gasto_total: str \| None`, `frecuencia: str \| None`, `nombre_cliente: str \| None` | Trata parámetros vacíos o con solo espacios como no proporcionados. Si no se proporciona ningún dato, pide nombre, gasto total o cantidad de alquileres. Con nombre, indica filtrar el cliente objetivo por nombre y consultar sus datos actuales; si solo se pasa el nombre, clasifica gasto y frecuencia. Calcula percentiles sobre todos los clientes activos. |

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
- El servidor Sakila usa las credenciales de solo lectura configuradas en
  `DB_USER` y `DB_PASSWORD` por Docker Compose; no incluya credenciales en el
  código ni en el control de versiones.
- Sakila no limita automáticamente el número de filas devueltas.
- Ghibli usa un timeout HTTP de 10 segundos por solicitud.
- La caché de Ghibli vive en memoria del proceso; se comparte entre sus
  solicitudes y se pierde cuando se reinicia el servidor.
- Los PDF de políticas y los archivos Sakila son material incluido en el
  repositorio. 
