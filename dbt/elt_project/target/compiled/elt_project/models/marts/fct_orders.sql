-- Fact tablosu: sipariş + müşteri + ürün birleşimi
-- Analitik sorgular buradan çalışır.



SELECT
    o.order_id,
    o.order_date,
    DATE_TRUNC('month', o.order_date)   AS order_month,
    DATE_TRUNC('week',  o.order_date)   AS order_week,

    -- Müşteri bilgileri
    o.customer_id,
    c.customer_name,
    c.city                              AS customer_city,
    c.country_code,

    -- Ürün bilgileri
    o.product_id,
    p.product_name,
    p.category                          AS product_category,
    p.unit_price,

    -- Sipariş metrikleri
    o.quantity,
    o.amount_usd,
    o.amount_usd / NULLIF(o.quantity, 0)   AS avg_unit_price,
    o.status,

    -- İş metrikleri
    CASE WHEN o.status = 'DELIVERED' THEN o.amount_usd ELSE 0 END AS revenue,
    CASE WHEN o.status = 'CANCELLED' THEN 1 ELSE 0 END            AS is_cancelled,

    o.loaded_at

FROM "dwh"."staging"."stg_orders"    o
LEFT JOIN "dwh"."staging"."stg_customers" c USING (customer_id)
LEFT JOIN "dwh"."staging"."stg_products"  p USING (product_id)