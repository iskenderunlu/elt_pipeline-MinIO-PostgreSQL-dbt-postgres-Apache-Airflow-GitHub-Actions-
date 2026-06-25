-- Dimension table: Customer segmentation and summary metrics



WITH order_summary AS (
    SELECT
        customer_id,
        COUNT(*)                            AS total_orders,
        SUM(amount_usd)                     AS total_spent,
        MAX(order_date)                     AS last_order_date,
        MIN(order_date)                     AS first_order_date,
        SUM(CASE WHEN status = 'DELIVERED'
                 THEN amount_usd ELSE 0 END) AS delivered_revenue
    FROM "dwh"."staging"."stg_orders"
    GROUP BY customer_id
)

SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    c.city,
    c.country_code,
    c.signup_date,

    -- Order metrics
    COALESCE(os.total_orders, 0)        AS total_orders,
    COALESCE(os.total_spent, 0)         AS total_spent_usd,
    COALESCE(os.delivered_revenue, 0)   AS delivered_revenue_usd,
    os.first_order_date,
    os.last_order_date,

    -- Segment
    CASE
        WHEN COALESCE(os.total_spent, 0) >= 10000 THEN 'VIP'
        WHEN COALESCE(os.total_spent, 0) >= 3000  THEN 'Regular'
        ELSE 'New'
    END AS customer_segment

FROM "dwh"."staging"."stg_customers" c
LEFT JOIN order_summary os USING (customer_id)
