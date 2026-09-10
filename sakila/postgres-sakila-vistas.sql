CREATE OR REPLACE VIEW vista_alquileres AS
SELECT
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.email,
    r.rental_date,
    r.return_date,
    f.title AS film_title,
    cat.name AS category_name
FROM rental AS r
INNER JOIN customer AS c
    ON c.customer_id = r.customer_id
INNER JOIN inventory AS i
    ON i.inventory_id = r.inventory_id
INNER JOIN film AS f
    ON f.film_id = i.film_id
INNER JOIN film_category AS fc
    ON fc.film_id = f.film_id
INNER JOIN category AS cat
    ON cat.category_id = fc.category_id;


CREATE OR REPLACE VIEW vista_catalogo AS
SELECT
    f.film_id,
    f.title,
    f.description,
    f.release_year,
    f.rating,
    cat.name AS category,
    l.name AS language
FROM film AS f
INNER JOIN film_category AS fc
    ON fc.film_id = f.film_id
INNER JOIN category AS cat
    ON cat.category_id = fc.category_id
INNER JOIN language AS l
    ON l.language_id = f.language_id;
	