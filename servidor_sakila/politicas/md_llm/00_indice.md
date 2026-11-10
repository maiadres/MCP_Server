Indice de politicas
Sakila Rental - Listado de politicas disponibles
| Código | Versión | Fecha de emisión | Estado  |
| ------ | ------- | ---------------- | ------- |
| POL-00 | 1.0     | 03/10/2026       | Vigente |
1. Politicas vigentes
| Codigo | Politica | Responde a la pregunta |     |
| ------ | -------- | ---------------------- | --- |
POL-01 Clientes por gasto Quien gasto mas y quien gasto menos
POL-02 Clientes por frecuencia Quien alquila mas y quien alquila menos
POL-03 Actores reconocidos Cuales son los actores mas reconocidos
| POL-04 | Descuentos | Que descuento ofrecer a cada segmento |     |
| ------ | ---------- | ------------------------------------- | --- |
2. Como usar las politicas
(cid:127) Las politicas definen reglas, no datos. Los valores (nombres, montos, rankings) se obtienen consultando
la base.
(cid:127) POL-04 depende de POL-01 y POL-02: leer primero esas dos.
(cid:127) Los clientes se clasifican por percentil (10% superior e inferior), manteniendo juntos a los empatados; los
actores, por deciles con desempate fijo. Los cortes se ajustan solos a los datos.
3. Base de datos
Tablas principales: customer, rental, payment, actor, film_actor, inventory, film.
POL-00 - Indice de politicas - v1.0 Página 1