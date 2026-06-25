-- ──────────────────────────────────────────────
-- Data Warehouse Schema (Medallion Architecture)
-- raw      → Raw Data from S3
-- staging  → cleaned with dbt
-- marts    → business logic, analytical queries
-- ──────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Raw orders table
CREATE TABLE IF NOT EXISTS raw.orders (
    order_id        TEXT PRIMARY KEY,
    customer_id     TEXT,
    order_date      TEXT,
    status          TEXT,
    amount          TEXT,
    product_id      TEXT,
    quantity        TEXT,
    _loaded_at      TIMESTAMP DEFAULT NOW()
);

-- Raw customers table
CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id     TEXT PRIMARY KEY,
    customer_name   TEXT,
    email           TEXT UNIQUE,
    city            TEXT,
    country         TEXT,
    signup_date     TEXT,
    _loaded_at      TIMESTAMP DEFAULT NOW()
);

-- Raw products table
CREATE TABLE IF NOT EXISTS raw.products (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT,
    category        TEXT,
    unit_price      TEXT,
    _loaded_at      TIMESTAMP DEFAULT NOW()
);

-- Watermark table for Incremental load
CREATE TABLE IF NOT EXISTS raw._load_watermarks (
    table_name      TEXT PRIMARY KEY,
    last_loaded_at  TIMESTAMP
);

INSERT INTO raw._load_watermarks (table_name, last_loaded_at)
VALUES ('orders', '2024-01-01'::TIMESTAMP),
       ('customers', '2024-01-01'::TIMESTAMP),
       ('products', '2024-01-01'::TIMESTAMP)
ON CONFLICT DO NOTHING;
