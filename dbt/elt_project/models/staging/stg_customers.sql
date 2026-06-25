{{ config(materialized='view') }}

SELECT
    customer_id::VARCHAR(20)                AS customer_id,
    INITCAP(TRIM(customer_name))            AS customer_name,
    LOWER(TRIM(email))                      AS email,
    INITCAP(TRIM(city))                     AS city,
    UPPER(TRIM(country))::CHAR(2)           AS country_code,
    signup_date::DATE                       AS signup_date,
    _loaded_at                              AS loaded_at

FROM {{ source('raw', 'customers') }}

WHERE customer_id IS NOT NULL
