CREATE TABLE IF NOT EXISTS customers
(
    id         BIGSERIAL PRIMARY KEY,
    email      TEXT        NOT NULL UNIQUE,
    full_name  TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders
(
    id           BIGSERIAL PRIMARY KEY,
    customer_id  BIGINT         NOT NULL REFERENCES customers (id),
    order_number TEXT           NOT NULL UNIQUE,
    total_amount NUMERIC(10, 2) NOT NULL,
    status       TEXT           NOT NULL,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);
