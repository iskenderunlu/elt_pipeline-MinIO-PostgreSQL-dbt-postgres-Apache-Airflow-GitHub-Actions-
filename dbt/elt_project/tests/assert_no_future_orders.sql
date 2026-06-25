-- Özel test: gelecek tarihli sipariş olmamalı
-- Bu test sıfır satır döndürmeli (sıfır = test geçti)

SELECT order_id, order_date
FROM {{ ref('stg_orders') }}
WHERE order_date > CURRENT_DATE
