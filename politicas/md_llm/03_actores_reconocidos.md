Politica de actores reconocidos
Sakila Rental - Seguimiento de los actores mas reconocidos
| Código | Versión | Fecha de emisión |     | Estado  |
| ------ | ------- | ---------------- | --- | ------- |
| POL-03 | 1.0     | 03/10/2026       |     | Vigente |
1. Objetivo
Definir cuando un actor se considera reconocido, para destacarlo en el catalogo y orientar
recomendaciones.
2. Metrica oficial y de apoyo
| Tipo | Metrica |     |     | Origen |
| ---- | ------- | --- | --- | ------ |
Popularidad: veces que se alquilaron las peliculas del
| Oficial |     |     |     | actor, film_actor, inventory, rental |
| ------- | --- | --- | --- | ------------------------------------ |
actor
| Apoyo | Ingresos generados por esas peliculas |     |     | payment    |
| ----- | ------------------------------------- | --- | --- | ---------- |
| Apoyo | Cantidad de peliculas en el catalogo  |     |     | film_actor |
(cid:127) El ranking se ordena por popularidad; ante empate, por ingresos y luego por id del actor.
(cid:127) El alquiler de una pelicula suma completo a cada actor que participa en ella (no se reparte entre el
elenco).
3. Niveles
Nivel Regla (decil de popularidad) Actores (de 200) Alquileres observados
| Estrella   | Decil 1: el 10% mas alquilado |     | 20  | 557 a 753 |
| ---------- | ----------------------------- | --- | --- | --------- |
| Conocido   | Deciles 2 a 4                 |     | 60  | 466 a 553 |
| Secundario | Deciles 5 a 10                |     | 120 | 216 a 465 |
4. Como se aplica
Consulta de referencia:
SELECT actor_id, actor, peliculas, alquileres, ingresos,
  NTILE(10) OVER (ORDER BY alquileres DESC, ingresos DESC, actor_id) AS decil
FROM (
  SELECT a.actor_id, a.first_name || ' ' || a.last_name AS actor,
         COUNT(DISTINCT fa.film_id) AS peliculas,
         COUNT(DISTINCT r.rental_id) AS alquileres,
         COALESCE(SUM(p.amount),0) AS ingresos
  FROM actor a
  JOIN film_actor fa ON fa.actor_id = a.actor_id
  JOIN inventory i   ON i.film_id = fa.film_id
  LEFT JOIN rental r  ON r.inventory_id = i.inventory_id
  LEFT JOIN payment p ON p.rental_id = r.rental_id
  GROUP BY a.actor_id, a.first_name, a.last_name
) t
Revision
Esta politica se revisa cada 6 meses o ante un cambio relevante en el negocio. Los cortes se definen por
percentiles, por lo que se actualizan solos cuando cambian los datos.
POL-03 - Politica de actores reconocidos - v1.0 Página 1