Politica de clasificacion de clientes por frecuencia
Sakila Rental - Quien alquila mas y quien alquila menos

Código

POL-02

1. Objetivo

Versión

Fecha de emisión

1.0

03/10/2026

Estado

Vigente

Distinguir a los clientes por cuantas veces alquilan, de forma independiente del dinero gastado. Un cliente
puede gastar poco porque alquila poco, o porque alquila seguido peliculas de bajo precio.

2. Alcance y metrica

(cid:127) Alcance: clientes activos (customer.active = 1).
(cid:127) Metrica: cantidad de alquileres = filas de rental asociadas al cliente.

3. Niveles

Nivel

Frecuente

Regular

Ocasional

Regla

Valores observados

10% superior en alquileres

33 a 46 alquileres (74 clientes)

Resto de los clientes

22 a 32 alquileres (429 clientes)

10% inferior en alquileres

12 a 21 alquileres (81 clientes)

Los clientes con igual cantidad de alquileres quedan siempre en el mismo nivel: el corte incluye a todos
los empatados, por lo que la proporcion es aproximada al 10% (en la medicion actual, entre 13% y 14%).
Los valores observados son informativos; la regla vigente es el percentil.

4. Cruce con la politica de gasto (POL-01)

Gasto / Frecuencia

Lectura

Destacado + Frecuente

Cliente clave

Accion sugerida

Retener y reconocer

Destacado + Ocasional

Alquila poco, ticket alto

Mantener contacto

Bajo gasto + Frecuente

Alquila seguido, ticket bajo

Ofrecer peliculas de mayor valor

Bajo gasto + Ocasional

Cliente en riesgo

Prioridad de reactivacion (ver POL-04)

5. Como se aplica

Tabla: rental. Consulta de referencia:

SELECT customer_id, alquileres,
  CASE WHEN PERCENT_RANK() OVER (ORDER BY alquileres DESC) < 0.10 THEN 'Frecuente'
       WHEN PERCENT_RANK() OVER (ORDER BY alquileres ASC)  < 0.10 THEN 'Ocasional'
       ELSE 'Regular' END AS nivel
FROM (
  SELECT c.customer_id, COUNT(r.rental_id) AS alquileres
  FROM customer c
  LEFT JOIN rental r ON r.customer_id = c.customer_id
  WHERE c.active = 1
  GROUP BY c.customer_id
) t

Revision

Esta politica se revisa cada 6 meses o ante un cambio relevante en el negocio. Los cortes se definen por
percentiles, por lo que se actualizan solos cuando cambian los datos.

POL-02 - Politica de clasificacion de clientes por frecuencia - v1.0

Página 1

