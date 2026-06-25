{{ config(materialized='view') }}

SELECT
    product_id::VARCHAR(20)             AS product_id,
    TRIM(product_name)                  AS product_name,
    INITCAP(TRIM(category))             AS category,
    unit_price::NUMERIC(12,2)           AS unit_price

FROM {{ source('raw', 'products') }}

WHERE product_id IS NOT NULL
