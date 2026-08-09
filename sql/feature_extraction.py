import pandas as pd
from sqlalchemy import create_engine, text

USER = "..."
PASSWORD = "..."
HOST = "localhost"
DB = "churn_project"

engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DB}")

query = """
WITH

customers_filtered AS (
    SELECT *
    FROM customers
    WHERE registration_date < @cut_date
),

orders_filtered AS (
    SELECT o.*
    FROM orders o
    JOIN customers_filtered USING(customer_id)
    WHERE o.order_date < @cut_date
),

sessions_filtered AS (
    SELECT s.*
    FROM sessions s
    JOIN customers_filtered USING(customer_id)
    WHERE s.session_date < @cut_date
),

order_level AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        CASE
            WHEN status_date >= @cut_date THEN 'Completed'
            ELSE COALESCE(status, 'Completed')
        END AS status,
        CASE
            WHEN status_date >= @cut_date THEN order_date
            ELSE status_date
        END AS status_date
    FROM orders_filtered
),

item_level AS (
    SELECT
        oi.order_item_id,
        oi.product_id,
        oi.quantity,
        oi.price_at_purchase,
        oi.order_id,
        CASE
            WHEN ofl.status_date > @cut_date THEN 0
            ELSE COALESCE(oi.returned, 0)
        END AS returned
    FROM orders_filtered ofl
    JOIN order_items oi USING(order_id)
),

successful_orders_for_intervals AS (
    SELECT
        ol.order_id,
        ol.customer_id,
        ol.order_date
    FROM order_level ol
    JOIN item_level il USING(order_id)
    WHERE 
        (
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il2
                    WHERE il2.order_id = ol.order_id
                      AND il2.returned = 0
                )
            )
        )
        AND ol.order_date < DATE_SUB(@cut_date, INTERVAL 90 DAY)
),

intervals AS (
    SELECT
        customer_id,
        DATEDIFF(
            order_date,
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS interval_days
    FROM successful_orders_for_intervals
),

order_frequency AS (
    SELECT
        customer_id,
        AVG(interval_days) AS avg_interval
    FROM intervals
    GROUP BY customer_id
),

order_values AS (
    SELECT 
    customer_id,
    COUNT(*) AS orders_count,
    SUM(order_total) AS total_orders_value,
    SUM(items_bought) AS total_items_per_customer
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            SUM(il.price_at_purchase * il.quantity) AS order_total,
            SUM(il.quantity) AS items_bought
        FROM order_level ol
        JOIN item_level il USING(order_id)
        WHERE ol.order_date < DATE_SUB(@cut_date, INTERVAL 90 DAY)
        GROUP BY ol.order_id, ol.customer_id
    ) t
    GROUP BY t.customer_id
),
  
succ_order_values AS (
    SELECT
        t.customer_id,
        AVG(order_total) AS avg_order_value,
        MIN(order_total) AS min_order_value,
        SUM(order_total) AS total_succ_orders_value,
        COUNT(*) AS succ_orders_count,
        AVG(items_bought) AS avg_items_per_order,
        SUM(items_bought) AS total_succ_items_per_customer
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            SUM(CASE WHEN il.returned = 0 THEN il.price_at_purchase * il.quantity ELSE 0 END) AS order_total,
            SUM(CASE WHEN il.returned = 0 THEN il.quantity ELSE 0 END) AS items_bought
        FROM order_level ol
        JOIN item_level il USING(order_id)
        WHERE (
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il2
                    WHERE il2.order_id = ol.order_id
                      AND il2.returned = 0
                )
            )
        )
          AND ol.order_date < DATE_SUB(@cut_date, INTERVAL 90 DAY)
        GROUP BY ol.order_id, ol.customer_id
    ) t
    GROUP BY t.customer_id
),

return_cancel AS(
    SELECT 
        ov.customer_id,
        (ov.orders_count - sov.succ_orders_count) AS return_cancel_orders_count,
        (ov.total_orders_value - sov.total_succ_orders_value) AS return_cancel_orders_values ,
        (ov.total_items_per_customer - sov.total_succ_items_per_customer) AS return_cancel_orders_items
    FROM order_values ov
    JOIN succ_order_values sov
    USING(customer_id)
),

successful_orders_for_intervals_90d AS (
    SELECT
        ol.order_id,
        ol.customer_id,
        ol.order_date
    FROM order_level ol
    JOIN item_level il USING(order_id)
    WHERE 
        (
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il2
                    WHERE il2.order_id = ol.order_id
                      AND il2.returned = 0
                )
            )
        )
        AND ol.order_date >= DATE_SUB(@cut_date, INTERVAL 90 DAY)
),

intervals_90d AS (
    SELECT
        customer_id,
        DATEDIFF(
            order_date,
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS interval_days
    FROM successful_orders_for_intervals_90d
),

order_frequency_90d AS (
    SELECT
        customer_id,
        AVG(interval_days) AS avg_interval_90d
    FROM intervals_90d
    GROUP BY customer_id
),

order_values_90d AS (
    SELECT 
    customer_id,
    COUNT(*) AS orders_count_90d,
    SUM(order_total) AS total_orders_value_90d,
    SUM(items_bought) AS total_items_per_customer_90d
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            SUM(il.price_at_purchase * il.quantity) AS order_total,
            SUM(il.quantity) AS items_bought
        FROM order_level ol
        JOIN item_level il USING(order_id)
        WHERE ol.order_date >= DATE_SUB(@cut_date, INTERVAL 90 DAY)
        GROUP BY ol.order_id, ol.customer_id
    ) t
    GROUP BY t.customer_id
),
  
succ_order_values_90d AS (
    SELECT
        t.customer_id,
        AVG(order_total) AS avg_order_value_90d,
        MIN(order_total) AS min_order_value_90d,
        SUM(order_total) AS total_succ_orders_value_90d,
        COUNT(*) AS succ_orders_count_90d,
        AVG(items_bought) AS avg_items_per_order_90d,
        SUM(items_bought) AS total_succ_items_per_customer_90d
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            SUM(CASE WHEN il.returned = 0 THEN il.price_at_purchase * il.quantity ELSE 0 END) AS order_total,
            SUM(CASE WHEN il.returned = 0 THEN il.quantity ELSE 0 END) AS items_bought
        FROM order_level ol
        JOIN item_level il USING(order_id)
        WHERE (
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il2
                    WHERE il2.order_id = ol.order_id
                      AND il2.returned = 0
                )
            )
        )
          AND ol.order_date >= DATE_SUB(@cut_date, INTERVAL 90 DAY) 
        GROUP BY ol.order_id, ol.customer_id
    ) t
    GROUP BY t.customer_id
),

return_cancel_90d AS(
    SELECT 
        ov90.customer_id,
        (ov90.orders_count_90d - sov90.succ_orders_count_90d) AS return_cancel_orders_count_90d,
        (ov90.total_orders_value_90d - sov90.total_succ_orders_value_90d) AS return_cancel_orders_values_90d,
        (ov90.total_items_per_customer_90d - sov90.total_succ_items_per_customer_90d) AS return_cancel_orders_items_90d
    FROM order_values_90d ov90
    JOIN succ_order_values_90d sov90
    USING(customer_id)
),


account_age AS (
    SELECT
        customer_id,
        DATEDIFF(@cut_date, registration_date) AS account_age_days
    FROM customers_filtered
),

last_successful_order AS (
    SELECT
        t.customer_id,
        t.order_id,
        DATEDIFF(@cut_date, t.order_date) AS last_successful_date
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            ol.order_date,
            ROW_NUMBER() OVER (
                PARTITION BY ol.customer_id
                ORDER BY ol.order_date DESC, ol.order_id DESC
            ) AS rn
        FROM order_level ol
        WHERE
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il2
                    WHERE il2.order_id = ol.order_id
                    AND il2.returned = 0
                )
            )
    ) t
    WHERE rn = 1
),

last_successful_stats AS (
    SELECT
        lso.customer_id,
        SUM(lso.last_successful_date) AS last_suc_order_interval ,
        SUM(CASE WHEN il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS last_succ_kept_order_total,
        SUM(CASE WHEN il.returned = 0 THEN il.quantity ELSE 0 END) AS last_succ_kept_order_items,
        SUM(il.quantity) AS last_succ_order_items,
        SUM(il.quantity * il.price_at_purchase) As last_succ_order_total
    FROM last_successful_order lso
    JOIN order_level ol
        ON ol.customer_id = lso.customer_id
        AND ol.order_id = lso.order_id
    JOIN item_level il 
    ON il.order_id = lso.order_id 
    GROUP BY lso.customer_id
),

full_return_orders AS (
    SELECT
        ol.order_id,
        ol.customer_id,
        ol.status_date,
        SUM(il.quantity * il.price_at_purchase) AS full_return_total
    FROM order_level ol
    JOIN item_level il USING(order_id)
    WHERE ol.status = 'Returned'
    GROUP BY ol.order_id, ol.customer_id, ol.status_date
    HAVING SUM(CASE WHEN il.returned = 0 THEN 1 ELSE 0 END) = 0
),

last_return_date AS (
    SELECT
        t.customer_id,
        t.order_id,
        t.status_date AS return_date
    FROM (
        SELECT
            customer_id,
            order_id,
            status_date,
            ROW_NUMBER() OVER (
                PARTITION BY customer_id
                ORDER BY status_date DESC,
                order_id DESC
            ) AS rn
        FROM full_return_orders
    ) t
    WHERE rn = 1
),

last_return_order AS (
    SELECT
        t.customer_id,
        t.order_id,
        DATEDIFF(@cut_date, t.return_date) AS days_from_last_return,
        t.full_return_total
    FROM (
        SELECT
            lrd.customer_id,
            lrd.order_id,
            lrd.return_date,
            fro.full_return_total
        FROM full_return_orders fro
        JOIN last_return_date lrd 
        ON fro.customer_id = lrd.customer_id
        AND fro.order_id = lrd.order_id
       
    ) t
),

last_return_stats AS (
    SELECT
        lro.customer_id,
        SUM(lro.days_from_last_return) AS days_from_last_return,
        SUM(CASE WHEN il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS last_return_total,
        SUM(CASE WHEN il.returned = 1 THEN il.quantity ELSE 0 END) AS last_returned_items
    FROM order_level ol
    JOIN last_return_order lro
        ON lro.customer_id = ol.customer_id
        AND lro.order_id = ol.order_id
    JOIN item_level il 
    ON il.order_id = lro.order_id 
    GROUP BY lro.customer_id
),

last_cancel_order AS (
    SELECT
        t.customer_id,
        t.order_id,
        DATEDIFF(@cut_date, t.status_date) AS days_from_last_cancel
    FROM (
        SELECT
            customer_id,
            order_id,
            status_date,
            ROW_NUMBER() OVER (
                PARTITION BY customer_id
                ORDER BY status_date DESC, order_id DESC
            ) AS rn
        FROM order_level
        WHERE status = 'Cancelled'
    ) t
    WHERE rn = 1
),

last_cancel_stats AS (
    SELECT
        lco.customer_id,
        SUM(lco.days_from_last_cancel) AS days_from_last_cancel,
        SUM(il.quantity) AS last_cancel_items,
        SUM(il.quantity * il.price_at_purchase) AS last_cancel_total
    FROM order_level ol
    JOIN last_cancel_order lco
        ON lco.customer_id = ol.customer_id
        AND lco.order_id = ol.order_id
    JOIN item_level il 
    ON il.order_id = lco.order_id 
    GROUP BY lco.customer_id
),

last3_orders AS (
    SELECT *
    FROM (
        SELECT
            customer_id,
            order_id,
            order_date,
            status,
            ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS rn
        FROM order_level
    ) t
    WHERE rn <= 3
),


last3_succ_orders AS (
    SELECT *
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            ol.order_date,
            ol.status,
            ROW_NUMBER() OVER (PARTITION BY ol.customer_id ORDER BY ol.order_date DESC, ol.order_id DESC
            ) AS rn
        FROM order_level ol
        WHERE
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il
                    WHERE il.order_id = ol.order_id
                    AND il.returned = 0
                )
            )
    ) t
    WHERE rn <= 3
),

last3_succ_orders_help_table AS (
    SELECT
        l3so.customer_id,
        l3so.order_id,
        SUM(CASE WHEN il.returned = 0 THEN il.price_at_purchase * il.quantity ELSE 0 END) AS last3_succ_kept_total,
        SUM(CASE WHEN il.returned = 0 THEN il.quantity ELSE 0 END) AS last3_succ_kept_items,
        SUM(il.quantity*il.price_at_purchase) AS total_value,
        SUM(il.quantity) AS total_items,
        DATEDIFF(
        l3so.order_date,
        LAG(l3so.order_date) OVER (PARTITION BY l3so.customer_id ORDER BY l3so.order_date, l3so.order_id)
        
        ) AS interval_days

    FROM last3_succ_orders l3so
    JOIN item_level il USING(order_id)
    GROUP BY l3so.customer_id, l3so.order_id
),

last3_succ_orders_stats AS (
    SELECT
        customer_id,
        AVG(interval_days) AS avg_last3_succ_interval,
        SUM(last3_succ_kept_items) AS last3_succ_orders_kept_items_total,
        SUM(last3_succ_kept_total) AS last3_succ_orders_kept_total,
        SUM(total_value) AS last3_succ_orders_total,
        SUM(total_items) AS last3_succ_orders_items
    FROM last3_succ_orders_help_table
    GROUP BY customer_id
),

last3_orders_help_table AS (
    SELECT
        l3o.customer_id,
        SUM(
            CASE
                WHEN (l3o.status = 'Returned' AND il.returned = 1)
                     OR l3o.status = 'Cancelled'
                THEN il.quantity * il.price_at_purchase
                ELSE 0
            END
        ) AS return_cancel_order_total,
        SUM(il.quantity * il.price_at_purchase) AS last_3orders_total,
        SUM(
            CASE
                WHEN (l3o.status = 'Returned' AND il.returned = 1)
                     OR l3o.status = 'Cancelled'
                THEN il.quantity
                ELSE 0
            END
        ) AS return_cancel_order_items,
        SUM(il.quantity) AS last_3orders_items
    FROM last3_orders l3o
    JOIN item_level il USING(order_id)
    GROUP BY l3o.customer_id
),

last3_orders_stats AS (
    SELECT
        customer_id,
        return_cancel_order_total  AS last3_return_cancel_order_total,
        (last_3orders_total - return_cancel_order_total) AS last3_kept_total ,
        return_cancel_order_items AS last3_cancels_returns_items,
        (last_3orders_items - return_cancel_order_items) AS last3_kept_items
    FROM last3_orders_help_table
),

category_counts AS (
    SELECT
        ol.customer_id,
        SUM(CASE WHEN p.category = 'Automotive' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS automotive_items,
        SUM(CASE WHEN p.category = 'Automotive' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS automotive_spent,
        SUM(CASE WHEN p.category = 'Beauty' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS beauty_items,
        SUM(CASE WHEN p.category = 'Beauty' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS beauty_spent,
        SUM(CASE WHEN p.category = 'Books' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS books_items,
        SUM(CASE WHEN p.category = 'Books' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS books_spent,
        SUM(CASE WHEN p.category = 'Electronics' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS electronics_items,
        SUM(CASE WHEN p.category = 'Electronics' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS electronics_spent,
        SUM(CASE WHEN p.category = 'Fashion' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS fashion_items,
        SUM(CASE WHEN p.category = 'Fashion' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS fashion_spent,
        SUM(CASE WHEN p.category = 'Food' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS food_items,
        SUM(CASE WHEN p.category = 'Food' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS food_spent,
        SUM(CASE WHEN p.category = 'Home' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS home_items,
        SUM(CASE WHEN p.category = 'Home' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS home_spent,
        SUM(CASE WHEN p.category = 'Pets' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS pets_items,
        SUM(CASE WHEN p.category = 'Pets' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS pets_spent,
        SUM(CASE WHEN p.category = 'Sports' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS sports_items,
        SUM(CASE WHEN p.category = 'Sports' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS sports_spent,
        SUM(CASE WHEN p.category = 'Toys' AND il.returned = 0 THEN il.quantity ELSE 0 END) AS toys_items,
        SUM(CASE WHEN p.category = 'Toys' AND il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS toys_spent
    FROM order_level ol
    JOIN item_level il USING(order_id)
    JOIN products p USING(product_id)
    WHERE ol.status IN ('Completed', 'Returned')
    GROUP BY ol.customer_id
),

category_returns_counts AS (
    SELECT
        ol.customer_id,
        SUM(CASE WHEN p.category = 'Automotive' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS automotive_items_returned,
        SUM(CASE WHEN p.category = 'Automotive' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS automotive_returned_total,
        SUM(CASE WHEN p.category = 'Beauty' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS beauty_items_returned,
        SUM(CASE WHEN p.category = 'Beauty' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS beauty_returned_total,
        SUM(CASE WHEN p.category = 'Books' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS books_items_returned,
        SUM(CASE WHEN p.category = 'Books' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS books_returned_total,
        SUM(CASE WHEN p.category = 'Electronics' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS electronics_items_returned,
        SUM(CASE WHEN p.category = 'Electronics' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS electronics_returned_total,
        SUM(CASE WHEN p.category = 'Fashion' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS fashion_items_returned,
        SUM(CASE WHEN p.category = 'Fashion' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS fashion_returned_total,
        SUM(CASE WHEN p.category = 'Food' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS food_items_returned,
        SUM(CASE WHEN p.category = 'Food' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS food_returned_total,
        SUM(CASE WHEN p.category = 'Home' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS home_items_returned,
        SUM(CASE WHEN p.category = 'Home' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS home_returned_total,
        SUM(CASE WHEN p.category = 'Pets' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS pets_items_returned,
        SUM(CASE WHEN p.category = 'Pets' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS pets_returned_total,
        SUM(CASE WHEN p.category = 'Sports' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS sports_items_returned,
        SUM(CASE WHEN p.category = 'Sports' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS sports_returned_total,
        SUM(CASE WHEN p.category = 'Toys' AND il.returned = 1 THEN il.quantity ELSE 0 END) AS toys_items_returned,
        SUM(CASE WHEN p.category = 'Toys' AND il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS toys_returned_total
    FROM order_level ol
    JOIN item_level il USING(order_id)
    JOIN products p USING(product_id)
    WHERE ol.status = 'Returned'
    GROUP BY ol.customer_id
),

discount_stats AS (
    SELECT
        ol.customer_id,
        SUM(CASE WHEN il.price_at_purchase < p.base_price THEN 1 ELSE 0 END) AS discounted_items_total
    FROM order_level ol
    JOIN item_level il USING(order_id)
    JOIN products p USING(product_id)
    WHERE ol.status IN ('Returned', 'Completed')
    GROUP BY ol.customer_id
),

last_session AS (
    SELECT
        customer_id,
        MAX(session_date) AS session_date
    FROM sessions_filtered
    WHERE session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 180 DAY)
                           AND @cut_date
    GROUP BY customer_id
),

last_session_stats AS (
    SELECT
        ls.customer_id,
        DATEDIFF(@cut_date, ls.session_date) AS days_from_last_session,
        sf.pages_viewed AS last_session_pages_viewed
    FROM last_session ls
    JOIN sessions_filtered sf
        ON sf.customer_id = ls.customer_id
       AND sf.session_date = ls.session_date
),

successful_orders_180 AS (
    SELECT
        customer_id,
        COUNT(*) AS successful_orders_180
    FROM order_level ol
    WHERE ol.order_date BETWEEN DATE_SUB(@cut_date, INTERVAL 180 DAY)
                            AND @cut_date
      AND (
            ol.status = 'Completed'
            OR (
                ol.status = 'Returned'
                AND EXISTS (
                    SELECT 1
                    FROM item_level il2
                    WHERE il2.order_id = ol.order_id
                      AND il2.returned = 0
                )
            )
          )
    GROUP BY customer_id
),

sessions_180_stats AS (
    SELECT
        sfl.customer_id,
        COUNT(*) AS total_180days_sessions,
        AVG(sfl.pages_viewed) AS avg_pages_viewed_180,
        MIN(sfl.pages_viewed) AS min_pages_viewed_180,
        SUM(CASE WHEN sfl.device = 'mobile' THEN 1 ELSE 0 END) AS mobile_sessions_count_180,
        SUM(CASE WHEN sfl.device = 'desktop' THEN 1 ELSE 0 END) AS desktop_sessions_count_180
    FROM sessions_filtered sfl
    JOIN last_session ls USING(customer_id)
    WHERE sfl.session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 180 DAY)
                               AND @cut_date
    GROUP BY sfl.customer_id
),

sessions_to_succ_orders_ratio_180 AS (
    SELECT
        s180.customer_id,
        so180.successful_orders_180 / NULLIF(s180.total_180days_sessions, 0) AS sessions_to_succ_orders_180days
    FROM successful_orders_180 so180
    JOIN sessions_180_stats s180 USING(customer_id)
),

recent_sessions_90 AS (
    SELECT
        customer_id,
        COUNT(*) AS sessions_90d,
        AVG(pages_viewed) AS avg_pages_90d
    FROM sessions_filtered
    WHERE session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 90 DAY)
                           AND @cut_date
    GROUP BY customer_id
),

session_intervals AS (
    SELECT
        customer_id,
        AVG(interval_days) AS avg_session_interval
    FROM (
        SELECT
            customer_id,
            DATEDIFF(
                session_date,
                LAG(session_date) OVER (PARTITION BY customer_id ORDER BY session_date)
            ) AS interval_days
        FROM sessions_filtered
    ) t
    WHERE interval_days IS NOT NULL
    GROUP BY customer_id
)


SELECT
    cfl.customer_id,

    COALESCE(aa.account_age_days, 1) AS account_age_days,
    cfl.birth_date,
    cfl.gender,
    cfl.city,
    cfl.country,

    COALESCE(1/NULLIF(ofq.avg_interval, 0), 0) AS shopping_frequency,
    COALESCE(ov.orders_count - sov.succ_orders_count, 0) AS unsuccessful_orders_count,

    COALESCE(sov.succ_orders_count, 0) AS succ_orders_count,
    COALESCE(sov.avg_order_value, 0) AS avg_order_value,
    COALESCE(sov.min_order_value, 0) AS min_order_value,
    COALESCE(sov.avg_items_per_order, 0) AS avg_items_per_order,
    COALESCE(sov.total_succ_items_per_customer, 0) AS total_succ_items_per_customer,

    COALESCE(rc.return_cancel_orders_count, 0) AS return_cancel_orders_count,
    COALESCE(rc.return_cancel_orders_values, 0) AS return_cancel_orders_values,
    COALESCE(rc.return_cancel_orders_items, 0) AS return_cancel_orders_items,

    COALESCE(1/NULLIF(of90.avg_interval_90d, 0), 0) AS shopping_frequency_90d,
    COALESCE(ov90.orders_count_90d - sov90.succ_orders_count_90d, 0) AS unsuccessful_orders_count_90d,

    COALESCE(sov90.succ_orders_count_90d, 0) AS succ_orders_count_90d,
    COALESCE(sov90.avg_order_value_90d, 0) AS avg_order_value_90d,
    COALESCE(sov90.min_order_value_90d, 0) AS min_order_value_90d,
    COALESCE(sov90.avg_items_per_order_90d, 0) AS avg_items_per_order_90d,
    COALESCE(sov90.total_succ_items_per_customer_90d, 0) AS total_succ_items_per_customer_90d,

    COALESCE(rc90.return_cancel_orders_count_90d, 0) AS return_cancel_orders_count_90d,
    COALESCE(rc90.return_cancel_orders_values_90d, 0) AS return_cancel_orders_values_90d,
    COALESCE(rc90.return_cancel_orders_items_90d, 0) AS return_cancel_orders_items_90d,

    COALESCE(lss.last_suc_order_interval, 0) AS last_suc_order_interval,
    COALESCE(lss.last_succ_kept_order_total, 0) AS last_succ_kept_order_total,
    COALESCE(lss.last_succ_kept_order_items, 0) AS last_succ_kept_order_items,
    COALESCE(lss.last_succ_order_items, 0) AS last_succ_order_items,
    COALESCE(lss.last_succ_order_total, 0) AS last_succ_order_total,

    COALESCE(lrs.days_from_last_return, 0) AS days_from_last_return,
    COALESCE(lrs.last_return_total, 0) AS last_return_total,
    COALESCE(lrs.last_returned_items, 0) AS last_returned_items,

    COALESCE(lcs.days_from_last_cancel, 0) AS days_from_last_cancel,
    COALESCE(lcs.last_cancel_items, 0) AS last_cancel_items,
    COALESCE(lcs.last_cancel_total, 0) AS last_cancel_total,

    COALESCE(l3sos.avg_last3_succ_interval, 0) AS avg_last3_succ_interval,
    COALESCE(l3sos.last3_succ_orders_kept_items_total, 0) AS last3_succ_orders_kept_items_total,
    COALESCE(l3sos.last3_succ_orders_kept_total, 0) AS last3_succ_orders_kept_total,
    COALESCE(l3sos.last3_succ_orders_total, 0) AS last3_succ_orders_total,
    COALESCE(l3sos.last3_succ_orders_items, 0) AS last3_succ_orders_items,

    COALESCE(l3os.last3_return_cancel_order_total, 0) AS last3_return_cancel_order_total,
    COALESCE(l3os.last3_kept_total, 0) AS last3_kept_total,
    COALESCE(l3os.last3_cancels_returns_items, 0) AS last3_cancels_returns_items,
    COALESCE(l3os.last3_kept_items, 0) AS last3_kept_items,

    COALESCE(cc.automotive_items, 0) AS automotive_items,
    COALESCE(cc.automotive_spent, 0) AS automotive_spent,
    COALESCE(cc.beauty_items, 0) AS beauty_items,
    COALESCE(cc.beauty_spent, 0) AS beauty_spent,
    COALESCE(cc.books_items, 0) AS books_items,
    COALESCE(cc.books_spent, 0) AS books_spent,
    COALESCE(cc.electronics_items, 0) AS electronics_items,
    COALESCE(cc.electronics_spent, 0) AS electronics_spent,
    COALESCE(cc.fashion_items, 0) AS fashion_items,
    COALESCE(cc.fashion_spent, 0) AS fashion_spent,
    COALESCE(cc.food_items, 0) AS food_items,
    COALESCE(cc.food_spent, 0) AS food_spent,
    COALESCE(cc.home_items, 0) AS home_items,
    COALESCE(cc.home_spent, 0) AS home_spent,
    COALESCE(cc.pets_items, 0) AS pets_items,
    COALESCE(cc.pets_spent, 0) AS pets_spent,
    COALESCE(cc.sports_items, 0) AS sports_items,
    COALESCE(cc.sports_spent, 0) AS sports_spent,
    COALESCE(cc.toys_items, 0) AS toys_items,
    COALESCE(cc.toys_spent, 0) AS toys_spent,

    COALESCE(crc.automotive_items_returned, 0) AS automotive_items_returned,
    COALESCE(crc.automotive_returned_total, 0) AS automotive_returned_total,
    COALESCE(crc.beauty_items_returned, 0) AS beauty_items_returned,
    COALESCE(crc.beauty_returned_total, 0) AS beauty_returned_total,
    COALESCE(crc.books_items_returned, 0) AS books_items_returned,
    COALESCE(crc.books_returned_total, 0) AS books_returned_total,
    COALESCE(crc.electronics_items_returned, 0) AS electronics_items_returned,
    COALESCE(crc.electronics_returned_total, 0) AS electronics_returned_total,
    COALESCE(crc.fashion_items_returned, 0) AS fashion_items_returned,
    COALESCE(crc.fashion_returned_total, 0) AS fashion_returned_total,
    COALESCE(crc.food_items_returned, 0) AS food_items_returned,
    COALESCE(crc.food_returned_total, 0) AS food_returned_total,
    COALESCE(crc.home_items_returned, 0) AS home_items_returned,
    COALESCE(crc.home_returned_total, 0) AS home_returned_total,
    COALESCE(crc.pets_items_returned, 0) AS pets_items_returned,
    COALESCE(crc.pets_returned_total, 0) AS pets_returned_total,
    COALESCE(crc.sports_items_returned, 0) AS sports_items_returned,
    COALESCE(crc.sports_returned_total, 0) AS sports_returned_total,
    COALESCE(crc.toys_items_returned, 0) AS toys_items_returned,
    COALESCE(crc.toys_returned_total, 0) AS toys_returned_total,

    COALESCE(ds.discounted_items_total, 0) AS discounted_items_total,

    COALESCE(ss180.total_180days_sessions, 0) AS total_180days_sessions,
    COALESCE(ss180.avg_pages_viewed_180, 0) AS avg_pages_viewed_180,
    COALESCE(ss180.min_pages_viewed_180, 0) AS min_pages_viewed_180,
    COALESCE(ss180.mobile_sessions_count_180, 0) AS mobile_sessions_count_180,
    COALESCE(ss180.desktop_sessions_count_180, 0) AS desktop_sessions_count_180,
    COALESCE(ss180_r.sessions_to_succ_orders_180days, 0) AS sessions_to_succ_orders_180days,

    COALESCE(ss90.sessions_90d, 0) AS sessions_90d,
    COALESCE(ss90.avg_pages_90d, 0) AS avg_pages_90d,

    COALESCE(lses.days_from_last_session, 0) AS days_from_last_session,
    COALESCE(lses.last_session_pages_viewed, 0) AS last_session_pages_viewed,

    COALESCE(si.avg_session_interval, 0) AS avg_session_interval


FROM customers_filtered cfl
LEFT JOIN order_frequency ofq USING(customer_id)
LEFT JOIN order_values ov USING(customer_id)
LEFT JOIN succ_order_values sov USING(customer_id)
LEFT JOIN return_cancel rc USING(customer_id)
LEFT JOIN order_values_90d ov90 USING(customer_id)
LEFT JOIN succ_order_values_90d sov90 USING(customer_id)
LEFT JOIN return_cancel_90d rc90 USING(customer_id)
LEFT JOIN order_frequency_90d of90 USING(customer_id)
LEFT JOIN account_age aa USING(customer_id)
LEFT JOIN last_successful_stats lss USING(customer_id)
LEFT JOIN last_return_stats lrs USING(customer_id)
LEFT JOIN last_cancel_stats lcs USING(customer_id)
LEFT JOIN last3_orders_stats l3os USING(customer_id)
LEFT JOIN last3_succ_orders_stats l3sos USING(customer_id)
LEFT JOIN category_counts cc USING(customer_id)
LEFT JOIN category_returns_counts crc USING(customer_id)
LEFT JOIN discount_stats ds USING(customer_id)
LEFT JOIN sessions_180_stats ss180 USING(customer_id)
LEFT JOIN recent_sessions_90 ss90 USING(customer_id)
LEFT JOIN last_session_stats lses USING(customer_id)
LEFT JOIN sessions_to_succ_orders_ratio_180 ss180_r USING(customer_id)
LEFT JOIN session_intervals si USING(customer_id);

"""

with engine.connect() as conn:
    conn.execute(text("SET @cut_date = '2026-01-01'"))
    df = pd.read_sql_query(text(query), conn)


df.to_csv("feature_matrix.csv", index=False)

print("ALL DONE! CSV saved as feature_matrix.csv")

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
