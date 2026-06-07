CREATE TABLE IF NOT EXISTS crm_accounts
(
    id             BIGSERIAL PRIMARY KEY,
    account_code   TEXT           NOT NULL UNIQUE,
    name           TEXT           NOT NULL,
    segment        TEXT           NOT NULL,
    status         TEXT           NOT NULL,
    annual_revenue NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_contacts
(
    id              BIGSERIAL PRIMARY KEY,
    account_id      BIGINT      NOT NULL REFERENCES crm_accounts (id),
    contact_code    TEXT        NOT NULL UNIQUE,
    email           TEXT        NOT NULL UNIQUE,
    full_name       TEXT        NOT NULL,
    role_title      TEXT        NOT NULL,
    lifecycle_stage TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_opportunities
(
    id               BIGSERIAL PRIMARY KEY,
    account_id       BIGINT         NOT NULL REFERENCES crm_accounts (id),
    opportunity_code TEXT           NOT NULL UNIQUE,
    title            TEXT           NOT NULL,
    stage            TEXT           NOT NULL,
    expected_amount  NUMERIC(12, 2) NOT NULL,
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crm_activities
(
    id            BIGSERIAL PRIMARY KEY,
    account_id    BIGINT      NOT NULL REFERENCES crm_accounts (id),
    contact_id    BIGINT REFERENCES crm_contacts (id),
    activity_code TEXT        NOT NULL UNIQUE,
    activity_type TEXT        NOT NULL,
    subject       TEXT        NOT NULL,
    status        TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_suppliers
(
    id           BIGSERIAL PRIMARY KEY,
    supplier_code TEXT           NOT NULL UNIQUE,
    name         TEXT           NOT NULL,
    status       TEXT           NOT NULL,
    rating_score NUMERIC(10, 2) NOT NULL,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_products
(
    id          BIGSERIAL PRIMARY KEY,
    supplier_id BIGINT         NOT NULL REFERENCES ops_suppliers (id),
    sku         TEXT           NOT NULL UNIQUE,
    name        TEXT           NOT NULL,
    category    TEXT           NOT NULL,
    unit_cost   NUMERIC(10, 2) NOT NULL,
    status      TEXT           NOT NULL,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_warehouses
(
    id             BIGSERIAL PRIMARY KEY,
    warehouse_code TEXT           NOT NULL UNIQUE,
    name           TEXT           NOT NULL,
    region         TEXT           NOT NULL,
    capacity_units NUMERIC(12, 2) NOT NULL,
    status         TEXT           NOT NULL,
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_inventory_movements
(
    id            BIGSERIAL PRIMARY KEY,
    product_id    BIGINT         NOT NULL REFERENCES ops_products (id),
    warehouse_id  BIGINT         NOT NULL REFERENCES ops_warehouses (id),
    movement_code TEXT           NOT NULL UNIQUE,
    movement_type TEXT           NOT NULL,
    quantity      NUMERIC(12, 2) NOT NULL,
    reason        TEXT           NOT NULL,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales_orders
(
    id           BIGSERIAL PRIMARY KEY,
    account_id   BIGINT         NOT NULL REFERENCES crm_accounts (id),
    contact_id   BIGINT REFERENCES crm_contacts (id),
    order_number TEXT           NOT NULL UNIQUE,
    status       TEXT           NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales_order_lines
(
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT         NOT NULL REFERENCES sales_orders (id),
    product_id  BIGINT         NOT NULL REFERENCES ops_products (id),
    line_code   TEXT           NOT NULL UNIQUE,
    quantity    NUMERIC(12, 2) NOT NULL,
    unit_price  NUMERIC(10, 2) NOT NULL,
    line_status TEXT           NOT NULL,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales_invoices
(
    id             BIGSERIAL PRIMARY KEY,
    order_id       BIGINT         NOT NULL REFERENCES sales_orders (id),
    invoice_number TEXT           NOT NULL UNIQUE,
    status         TEXT           NOT NULL,
    amount_due     NUMERIC(12, 2) NOT NULL,
    issued_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales_payments
(
    id                BIGSERIAL PRIMARY KEY,
    invoice_id        BIGINT         NOT NULL REFERENCES sales_invoices (id),
    payment_reference TEXT           NOT NULL UNIQUE,
    status            TEXT           NOT NULL,
    amount_paid       NUMERIC(12, 2) NOT NULL,
    paid_at           TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);
