-- Ejecutar una vez en pgAdmin, conectado a sakila como administrador.
CREATE ROLE sakila_mcp_readonly LOGIN PASSWORD 'CAMBIA_ESTA_CONTRASENA' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
REVOKE ALL ON SCHEMA public FROM sakila_mcp_readonly;
GRANT USAGE ON SCHEMA public TO sakila_mcp_readonly;
GRANT SELECT ON TABLE public.vista_alquileres, public.vista_catalogo TO sakila_mcp_readonly;
ALTER ROLE sakila_mcp_readonly SET default_transaction_read_only = on;
ALTER ROLE sakila_mcp_readonly SET statement_timeout = '5s';
ALTER ROLE sakila_mcp_readonly SET idle_in_transaction_session_timeout = '10s';
