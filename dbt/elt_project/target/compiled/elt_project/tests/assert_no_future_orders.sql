-- "Special test: there should be no future-dated orders"
-- This test should return zero rows (zero = test passed)

SELECT order_id, order_date
FROM "dwh"."staging"."stg_orders"
WHERE order_date > CURRENT_DATE
