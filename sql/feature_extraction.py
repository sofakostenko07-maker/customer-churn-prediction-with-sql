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
            ELSE status
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
            ELSE oi.returned
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

clean_intervals AS (
    SELECT customer_id, interval_days
    FROM intervals
    WHERE interval_days IS NOT NULL
),

ranked_intervals AS (
    SELECT
        customer_id,
        interval_days,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY interval_days) AS rn,
        COUNT(*) OVER (PARTITION BY customer_id) AS cnt
    FROM clean_intervals
),

order_frequency AS (
    SELECT
        customer_id,
        interval_days AS median_interval
    FROM ranked_intervals
    WHERE rn = FLOOR((cnt + 1) / 2)
),

order_values AS (
    SELECT
        t.customer_id,
        AVG(order_total) AS avg_order_value,
        MIN(order_total) AS min_order_value,
        SUM(order_total) AS total_orders_value,
        COUNT(*) AS orders_count,
        AVG(items_bought) AS avg_items_per_order,
        SUM(items_bought) AS total_items_per_customer
    FROM (
        SELECT
            ol.customer_id,
            ol.order_id,
            SUM(CASE WHEN il.returned = 0 THEN il.price_at_purchase * il.quantity ELSE 0 END) AS order_total,
            SUM(CASE WHEN il.returned = 0 THEN il.quantity ELSE 0 END) AS items_bought
        FROM order_level ol
        JOIN item_level il USING(order_id)
        WHERE ol.status IN ('Completed', 'Returned')
        GROUP BY ol.order_id, ol.customer_id
    ) t
    GROUP BY t.customer_id
),

return_cancel AS (
    SELECT
        ol.customer_id,
        SUM(CASE WHEN il.returned = 1 AND ol.status = 'Returned' THEN il.quantity ELSE 0 END) AS returned_items,
        SUM(CASE WHEN il.returned = 1 AND ol.status = 'Returned' THEN il.quantity * il.price_at_purchase ELSE 0 END) AS returned_items_total,
        SUM(CASE WHEN ol.status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
        SUM(CASE WHEN ol.status = 'Cancelled' THEN il.quantity ELSE 0 END) AS cancelled_items_total
    FROM order_level ol
    JOIN item_level il USING(order_id)
    GROUP BY ol.customer_id
),

return_cancel_ratio AS (
    SELECT
        ov.customer_id,
        (rc.returned_items_total + rc.cancelled_items_total) / NULLIF(ov.total_orders_value, 0)
        AS return_cancel_ratio_lifetime
    FROM order_values ov
    JOIN return_cancel rc USING(customer_id)
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
        SUM(CASE WHEN il.returned = 0 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS last_suc_order_total,
        SUM(CASE WHEN il.returned = 0 THEN il.quantity ELSE 0 END) AS last_suc_order_items,
        SUM(CASE WHEN il.returned = 1 THEN il.quantity ELSE 0 END) AS returned_items_in_last_order,
        SUM(CASE WHEN il.returned = 1 THEN il.quantity * il.price_at_purchase ELSE 0 END) AS returned_items_total_in_last_order
    FROM last_successful_order lso
    JOIN order_level ol
        ON ol.customer_id = lso.customer_id
        AND ol.order_id = lso.order_id
    JOIN item_level il 
    ON il.order_id = lso.order_id 
    GROUP BY lso.customer_id
),

last_successful_ratios AS (
    SELECT
        customer_id,
        returned_items_in_last_order / NULLIF(returned_items_in_last_order + last_suc_order_items, 0) AS items_return_ratio,
        returned_items_total_in_last_order / NULLIF(returned_items_total_in_last_order + last_suc_order_total, 0) AS total_return_ratio
    FROM last_successful_stats
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
        l3so.order_date,
        SUM(CASE WHEN il.returned = 0 THEN il.price_at_purchase * il.quantity ELSE 0 END) AS last_succ_totals,
        SUM(CASE WHEN il.returned = 1 THEN il.quantity ELSE 0 END) AS last_succ_items_returned,
        SUM(il.quantity) AS total_items,
        DATEDIFF(
            l3so.order_date,
            LAG(l3so.order_date) OVER (PARTITION BY l3so.customer_id ORDER BY l3so.order_date DESC, l3so.order_id DESC)
        ) AS interval_days
    FROM last3_succ_orders l3so
    JOIN item_level il USING(order_id)
    GROUP BY l3so.customer_id, l3so.order_id, l3so.order_date
),

last3_succ_orders_stats AS (
    SELECT
        customer_id,
        AVG(interval_days) AS avg_last3_succ_interval,
        AVG(last_succ_totals) AS last3_succ_orders_total,
        AVG(last_succ_items_returned / NULLIF(total_items, 0)) AS last3_succ_returns_ratio
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
        SUM(il.quantity * il.price_at_purchase) AS last_3orders_total
    FROM last3_orders l3o
    JOIN item_level il USING(order_id)
    GROUP BY l3o.customer_id
),

last3_orders_stats AS (
    SELECT
        customer_id,
        return_cancel_order_total / NULLIF(last_3orders_total, 0) AS return_cancel_ratio_total_last3
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
    aa.account_age_days,
    cfl.birth_date,
    cfl.gender,
    cfl.city,
    cfl.country,

    1/NULLIF(ofq.median_interval) AS shopping_frequency,

    ov.avg_order_value,
    ov.min_order_value,
    ov.orders_count,
    ov.avg_items_per_order,
    ov.total_items_per_customer,

    rc.returned_items,
    rc.returned_items_total,
    rc.cancelled_orders,
    rc.cancelled_items_total,
    rcr.return_cancel_ratio_lifetime,

    lss.last_suc_order_interval,
    lss.last_suc_order_total,
    lss.last_suc_order_items,
    lsr.items_return_ratio,
    lsr.total_return_ratio,

    lrs.days_from_last_return,
    lrs.last_return_total,
    lrs.last_returned_items,

    lcs.days_from_last_cancel,
    lcs.last_cancel_items,
    lcs.last_cancel_total,

    l3os.return_cancel_ratio_total_last3,

    l3sos.avg_last3_succ_interval,
    l3sos.last3_succ_orders_total,
    l3sos.last3_succ_returns_ratio,

    cc.automotive_items,
    cc.automotive_spent,
    cc.beauty_items,
    cc.beauty_spent,
    cc.books_items,
    cc.books_spent,
    cc.electronics_items,
    cc.electronics_spent,
    cc.fashion_items,
    cc.fashion_spent,
    cc.food_items,
    cc.food_spent,
    cc.home_items,
    cc.home_spent,
    cc.pets_items,
    cc.pets_spent,
    cc.sports_items,
    cc.sports_spent,
    cc.toys_items,
    cc.toys_spent,

    crc.automotive_items_returned,
    crc.automotive_returned_total,
    crc.beauty_items_returned,
    crc.beauty_returned_total,
    crc.books_items_returned,
    crc.books_returned_total,
    crc.electronics_items_returned,
    crc.electronics_returned_total,
    crc.fashion_items_returned,
    crc.fashion_returned_total,
    crc.food_items_returned,
    crc.food_returned_total,
    crc.home_items_returned,
    crc.home_returned_total,
    crc.pets_items_returned,
    crc.pets_returned_total,
    crc.sports_items_returned,
    crc.sports_returned_total,
    crc.toys_items_returned,
    crc.toys_returned_total,

    ds.discounted_items_total,

    ss180.total_180days_sessions,
    ss180.avg_pages_viewed_180,
    ss180.min_pages_viewed_180,
    ss180.mobile_sessions_count_180,
    ss180.desktop_sessions_count_180,
    ss180_r.sessions_to_succ_orders_180days,

    ss90.sessions_90d,
    ss90.avg_pages_90d,

    lses.days_from_last_session,
    lses.last_session_pages_viewed,

    si.avg_session_interval

FROM customers_filtered cfl
LEFT JOIN order_frequency ofq USING(customer_id)
LEFT JOIN order_values ov USING(customer_id)
LEFT JOIN return_cancel rc USING(customer_id)
LEFT JOIN return_cancel_ratio rcr USING(customer_id)
LEFT JOIN account_age aa USING(customer_id)
LEFT JOIN last_successful_stats lss USING(customer_id)
LEFT JOIN last_successful_ratios lsr USING(customer_id)
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

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
