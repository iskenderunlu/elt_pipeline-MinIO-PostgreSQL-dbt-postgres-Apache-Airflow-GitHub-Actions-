-- Fact table: order + customer + product union
-- Analytical queries are executed from here.

{{ config(materialized='table') }}

SELECT
    o.order_id,
    o.order_date,
    DATE_TRUNC('month', o.order_date)   AS order_month,
    DATE_TRUNC('week',  o.order_date)   AS order_week,

    -- Customer Info
    o.customer_id,
    c.customer_name,
    c.city                              AS customer_city,
    c.country_code,

    -- Product Info
    o.product_id,
    p.product_name,
    p.category                          AS product_category,
    p.unit_price,

    -- Order metrics
    o.quantity,
    o.amount_usd,
    o.amount_usd / NULLIF(o.quantity, 0)   AS avg_unit_price,
    o.status,

    -- Business metrics
    CASE WHEN o.status = 'DELIVERED' THEN o.amount_usd ELSE 0 END AS revenue,
    CASE WHEN o.status = 'CANCELLED' THEN 1 ELSE 0 END            AS is_cancelled,

    o.loaded_at

FROM {{ ref('stg_orders') }}    o
LEFT JOIN {{ ref('stg_customers') }} c USING (customer_id)
LEFT JOIN {{ ref('stg_products') }}  p USING (product_id)
