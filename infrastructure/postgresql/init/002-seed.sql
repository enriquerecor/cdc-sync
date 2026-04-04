INSERT INTO customers (email, full_name)
VALUES ('alice@example.com', 'Alice Example'),
       ('bob@example.com', 'Bob Example')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (customer_id, order_number, total_amount, status)
VALUES ((SELECT id FROM customers WHERE email = 'alice@example.com'), 'ORD-0001', 149.99, 'pending'),
       ((SELECT id FROM customers WHERE email = 'bob@example.com'), 'ORD-0002', 79.50, 'confirmed')
ON CONFLICT (order_number) DO NOTHING;
