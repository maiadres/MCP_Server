# Integración de Sakila y Studio Ghibli

## 1. Descripción General

MCP_Server es un proyecto de integración de fuentes de datos mediante **Model Context Protocol (MCP)**. Expone dos servidores independientes para que un cliente compatible con MCP pueda consultar información estructurada sin acceder directamente a la base de datos ni a la API externa.

El servidor **Sakila MCP** permite inspeccionar el esquema público de PostgreSQL y ejecutar consultas dinámicas de solo lectura sobre la base de datos. El servidor **Studio Ghibli MCP** consulta la API pública de Studio Ghibli y entrega datos resumidos de sus películas.

Características principales:

- Separación de responsabilidades entre datos internos (Sakila) y datos externos (Studio Ghibli).
- Herramientas MCP con tipos, docstrings y respuestas estructuradas.
- Protección de Sakila mediante un pool de conexiones, validación de consultas `SELECT` y usuario de mínimo privilegio.
- Consultas HTTP asíncronas, con validación de parámetros y errores controlados en el servidor Ghibli.
- Variables de entorno para credenciales.

## 2. Arquitectura y Diseño

### Estructura de directorios

```text
MCP/
├── .env                              # Credenciales locales
├── .gitignore                        # Exclusión de secretos, entornos y cachés
├── servidor_mcp_sakila.py             # Servidor MCP para PostgreSQL/Sakila
├── servidor_mcp_ghibli_api.py         # Servidor MCP para la API Studio Ghibli
├── sakila/
│   ├── postgres-sakila-schema.sql     # Esquema de Sakila
│   └── postgres-sakila-insert-data.sql# Datos de Sakila
├── .venv/                             # Entorno virtual local
```

### Componentes y flujo de datos

```text
Cliente MCP (Claude, Codex u otro)
        │
        ├── stdio ──> servidor_mcp_sakila.py
        │                  │
        │                  ├── obtener_esquema_base_datos()
        │                  ├── ejecutar_consulta_sql(consulta)
        │                  ├── validar_consulta()
        │                  ├── ThreadedConnectionPool
        │                  └── PostgreSQL / esquema public
        │
        └── stdio ──> servidor_mcp_ghibli_api.py
                           │
                           ├── validación de parámetros
                           ├── httpx asíncrono
                           └── API pública Studio Ghibli
```

El diseño sigue una arquitectura de **adaptadores**: cada servidor encapsula el protocolo y particularidades de una fuente. Las funciones decoradas con `@mcp.tool()` constituyen la interfaz pública para el modelo; las funciones auxiliares permanecen privadas y centralizan validación, acceso HTTP o acceso a datos.

En Sakila, el flujo es: herramienta MCP → inspección del esquema o validación de un único `SELECT` → pool PostgreSQL → respuesta JSON estructurada. En Ghibli, el flujo es: herramienta MCP → validación → petición HTTP asíncrona → filtrado de campos → respuesta resumida.

## 3. Stack Tecnológico

| Tecnología | Uso | Justificación técnica |
|---|---|---|
| Python 3.11+ | Lenguaje de implementación | Tipado moderno, asincronía nativa y ecosistema para MCP y PostgreSQL. |
| FastMCP | Framework de ambos servidores | Registra herramientas mediante decoradores y expone el protocolo MCP por `stdio`. |
| PostgreSQL | Base de datos interna Sakila | Base relacional consultada dinámicamente mediante el esquema `public`. |
| psycopg2 | Driver PostgreSQL | Proporciona el pool de conexiones seguro para hilos. |
| httpx | Cliente HTTP asíncrono | Consume Studio Ghibli sin bloquear el ciclo asíncrono. |
| python-dotenv | Configuración local | Carga `DB_USER` y `DB_PASSWORD` desde `.env`, sin incorporarlos al código. |
| Studio Ghibli API | Fuente externa | API pública de películas sin clave de acceso. |

## 4. Guía de Instalación y Configuración

### Prerrequisitos

- Python 3.11 o superior.
- PostgreSQL ejecutándose localmente con la base `sakila` disponible.
- Un cliente compatible con MCP configurado para iniciar procesos Python por `stdio`.
- PowerShell en Windows para los comandos de este documento.

### Clonar y preparar el entorno

```powershell
git clone <URL_DEL_REPOSITORIO>
cd MCP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install fastmcp httpx psycopg2-binary python-dotenv
```

Si PowerShell bloquea la activación del entorno virtual para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Cargar Sakila

En pgAdmin, cree o seleccione la base `sakila` y ejecute, en este orden:

```text
sakila/postgres-sakila-schema.sql
sakila/postgres-sakila-insert-data.sql
```

No es necesario crear vistas para iniciar el servidor actual. Solo se requieren el esquema y los datos de Sakila.

### Configurar credenciales

Cree un archivo `.env` en la raíz del repositorio:

```env
DB_USER=sakila_mcp_readonly
DB_PASSWORD=REEMPLAZAR_POR_UNA_CONTRASENA_SEGURA
```

El usuario debe tener permiso `CONNECT` sobre la base `sakila` y permiso `SELECT` sobre las tablas y vistas que se quieran consultar del esquema `public`. No use el usuario administrador `postgres` para el servidor MCP. Verifique además que el puerto configurado en `servidor_mcp_sakila.py` (`5434`) coincida con su instalación local.

### Ejecución local y producción

El transporte predeterminado de FastMCP es `stdio`; por eso no hay puerto HTTP, paso de compilación ni comando de build independiente.

Desarrollo, servidor Sakila:

```powershell
python servidor_mcp_sakila.py
```

Desarrollo, servidor Studio Ghibli:

```powershell
python servidor_mcp_ghibli_api.py
```

Producción: configure el cliente MCP o el supervisor de procesos para ejecutar exactamente los mismos comandos usando el entorno virtual del proyecto:

```powershell
C:\ruta\a\MCP\.venv\Scripts\python.exe C:\ruta\a\MCP\servidor_mcp_sakila.py
C:\ruta\a\MCP\.venv\Scripts\python.exe C:\ruta\a\MCP\servidor_mcp_ghibli_api.py
```

Tras modificar un servidor, reinicie el proceso o recargue la configuración MCP del cliente para que detecte las herramientas y docstrings actualizados.

## 5. Uso y Ejemplos

### Herramientas de Sakila

`obtener_esquema_base_datos()` consulta `information_schema.columns` y devuelve un string JSON agrupado por tabla, con el nombre de cada columna y su tipo de dato. Es recomendable llamar primero a esta herramienta para que la IA conozca la estructura actual de la base de datos.

`ejecutar_consulta_sql(consulta)` recibe SQL libre de solo lectura y devuelve un string JSON con una lista de diccionarios. Solo acepta consultas que comiencen por `SELECT`, ignorando espacios iniciales y mayúsculas/minúsculas. También rechaza comentarios, múltiples sentencias y operaciones como `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE`, `COPY`, `CALL`, `DO`, `VACUUM`, `SET` y `SHOW`.

Ejemplo:

```text
obtener_esquema_base_datos()

ejecutar_consulta_sql(
  "SELECT title, release_year, rating FROM film WHERE rating = 'PG' LIMIT 10"
)
```

No se aplica un límite automático de filas. Incluye un `LIMIT` apropiado para evitar respuestas demasiado grandes. Los errores de PostgreSQL se devuelven como string sin crashear el servidor.

### Herramientas de Studio Ghibli

Buscar una película por título:

```text
search_ghibli_films(query="Totoro")
```

Obtener detalles usando el UUID devuelto por la búsqueda:

```text
get_ghibli_film_details(
  film_id="58611129-2dbc-4a81-a72f-77ddfc1b1b49"
)
```

Filtrar por año y puntaje de Rotten Tomatoes:

```text
list_ghibli_films(year=2001, min_score=90)
```

Las sinopsis de Ghibli provienen en inglés. Las herramientas incluyen `source_language: "en"`; el cliente de IA debe presentar o resumir el contenido en español sin alterar fechas, puntajes, créditos ni títulos de origen.

## 6. Decisiones de Diseño

**Servidores separados.** Sakila y Ghibli se ejecutan de manera independiente para aislar dependencias, fallos y superficies de seguridad. Una indisponibilidad de la API externa no debe afectar la base local.

**Principio de mínimo privilegio.** El servidor Sakila no debe usar un administrador de PostgreSQL. Se diseñó para un usuario de solo lectura con acceso `SELECT` sobre las tablas que se quieran consultar. La validación del SQL es una defensa adicional, no un reemplazo de los permisos reales de la base.

**Control de contexto y rendimiento.** Ghibli limita las búsquedas por título a 10 resultados y ambos servidores devuelven campos resumidos. En Sakila, el cliente debe incluir `LIMIT` en las consultas, porque la herramienta no impone un límite automático.

**Asincronía para la API externa.** Ghibli usa `httpx.AsyncClient` para evitar bloqueos durante solicitudes de red. También diferencia timeouts, errores de transporte, respuestas 404 y errores del proveedor.

**Idioma de la fuente externa.** La API de Studio Ghibli no ofrece localización al español. Se preserva el dato original y se indica su idioma para que la capa conversacional pueda traducirlo de forma transparente.
