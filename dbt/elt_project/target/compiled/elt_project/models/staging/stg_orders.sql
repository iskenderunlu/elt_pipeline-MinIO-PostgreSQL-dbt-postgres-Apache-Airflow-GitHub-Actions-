-- Staging: ham orders → temiz tipler, normalize edilmiş değerler
-- Bu katmanda sadece temizlik yapılır, iş mantığı eklenmez.



SELECT
    order_id::VARCHAR(50)               AS order_id,
    customer_id::VARCHAR(20)            AS customer_id,
    order_date::DATE                    AS order_date,
    UPPER(TRIM(status))::VARCHAR(20)    AS status,
    amount::NUMERIC(12,2)               AS amount_usd,
    product_id::VARCHAR(20)             AS product_id,
    quantity::INTEGER                   AS quantity,
    _loaded_at                          AS loaded_at

FROM "dwh"."raw"."orders"

WHERE
    order_id    IS NOT NULL
    AND amount  IS NOT NULL
    AND amount::NUMERIC > 0