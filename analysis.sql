
CREATE TABLE IF NOT EXISTS customers (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    amount NUMERIC(10, 2) NOT NULL,
    ordered_at DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    attrs JSONB NOT NULL
);

TRUNCATE TABLE orders, customers, products RESTART IDENTITY CASCADE;

INSERT INTO customers (id, name, city) VALUES
(1, 'Arun', 'Chennai'),
(2, 'Priya', 'Mumbai'),
(3, 'Rahul', 'Chennai'),
(4, 'Divya', 'Bangalore');

INSERT INTO orders (id, customer_id, amount, ordered_at) VALUES
(101, 1, 700.00, '2026-01-05'),
(102, 1, 600.00, '2026-02-10'),
(103, 2, 300.00, '2026-01-20'),
(104, 1, 150.00, '2026-02-15'), -- Custom 1
(105, 2, 850.00, '2026-02-18'), -- Custom 2 (Makes Priya's total > 1000)
(106, 4, 450.00, '2026-02-20'), -- Custom 3
(107, 4, 900.00, '2026-02-22'), -- Custom 4 (Makes Divya's total > 1000)
(108, 1, 200.00, '2026-02-25'), -- Custom 5
(109, 2, 100.00, '2026-02-28'); -- Custom 6

INSERT INTO products (id, name, attrs) VALUES
(1, 'Laptop A', '{"brand": "Dell", "ram": 16}'),
(2, 'Laptop B', '{"brand": "HP", "ram": 8}');


SELECT c.id, c.name, SUM(o.amount) AS total_sales
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
HAVING SUM(o.amount) > 1000;



SELECT c.id, c.name, c.city
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;


WITH CustomerCitySales AS (
    SELECT c.city, c.name, SUM(o.amount) as total_spent,
           ROW_NUMBER() OVER (PARTITION BY c.city ORDER BY SUM(o.amount) DESC) as rn
    FROM customers c
    JOIN orders o ON c.id = o.customer_id
    GROUP BY c.city, c.name
)
SELECT city, name, total_spent
FROM CustomerCitySales
WHERE rn = 1;

SELECT 
    id AS order_id,
    customer_id,
    amount,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS order_rank_by_amount,
    LAG(amount, 1) OVER (PARTITION BY customer_id ORDER BY ordered_at ASC) AS previous_order_amount
FROM orders;
