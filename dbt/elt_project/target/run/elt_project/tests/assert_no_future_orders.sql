
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  -- Özel test: gelecek tarihli sipariş olmamalı
-- Bu test sıfır satır döndürmeli (sıfır = test geçti)

SELECT order_id, order_date
FROM "dwh"."staging"."stg_orders"
WHERE order_date > CURRENT_DATE
  
  
      
    ) dbt_internal_test