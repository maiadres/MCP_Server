Politica de clasificacion de clientes por gasto
Sakila Rental - Quien gasto mas y quien gasto menos

Código

POL-01

1. Objetivo

Versión

Fecha de emisión

1.0

03/10/2026

Estado

Vigente

Definir una forma unica y repetible de clasificar a los clientes segun cuanto dinero gastaron, para
identificar a los de mayor valor y a los de menor gasto.

2. Alcance y metrica

(cid:127) Alcance: clientes activos (customer.active = 1).
(cid:127) Metrica: gasto total = suma de payment.amount de los pagos realizados por el cliente
(payment.customer_id). Se toma a quien pago, no al cliente del alquiler.
(cid:127) Los clientes activos sin pagos cuentan con gasto 0 y se incluyen en la clasificacion.

3. Segmentos

Segmento

Destacado

Regular

Regla

Valores observados

10% superior de gasto total

USD 144,67 a 221,55 (59 clientes)

Resto de los clientes

USD 81,76 a 144,66 (466 clientes)

Bajo gasto

10% inferior de gasto total

USD 50,85 a 80,83 (59 clientes)

Los clientes con igual gasto quedan siempre en el mismo segmento: el corte incluye a todos los
empatados, por lo que la proporcion es aproximada al 10%. Los valores observados son informativos; la
regla vigente es el percentil.

4. Como se aplica

Tablas: customer y payment. Consulta de referencia:

SELECT customer_id, total_gastado,
  CASE WHEN PERCENT_RANK() OVER (ORDER BY total_gastado DESC) < 0.10 THEN 'Destacado'
       WHEN PERCENT_RANK() OVER (ORDER BY total_gastado ASC)  < 0.10 THEN 'Bajo gasto'
       ELSE 'Regular' END AS segmento
FROM (
  SELECT c.customer_id, COALESCE(SUM(p.amount),0) AS total_gastado
  FROM customer c
  LEFT JOIN payment p ON p.customer_id = c.customer_id
  WHERE c.active = 1
  GROUP BY c.customer_id
) t

Revision

Esta politica se revisa cada 6 meses o ante un cambio relevante en el negocio. Los cortes se definen por
percentiles, por lo que se actualizan solos cuando cambian los datos.

POL-01 - Politica de clasificacion de clientes por gasto - v1.0

Página 1

