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
    JOIN customers_filtered
    USING(customer_id)
),

items_filtered AS (
    SELECT
        oi.*
    FROM order_items oi
    JOIN orders_filtered USING(order_id)
),

sessions_filtered AS (
    SELECT s.*
    FROM sessions s
    JOIN customers_filtered
    USING(customer_id)
),

successful_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.status
    FROM orders_filtered o
    WHERE 
        o.status = 'Completed'
        OR (
            o.status = 'Returned'
            AND EXISTS (
                SELECT 1
                FROM items_filtered it
                WHERE it.order_id = o.order_id
                  AND it.returned = 0
            )
        )
),

successful_orders_30 AS (
    SELECT
        customer_id,
        COUNT(*) AS successful_orders_30
    FROM successful_orders
    WHERE order_date BETWEEN DATE_SUB(@last_date, INTERVAL 30 DAY) AND @last_date
    GROUP BY customer_id
),

successful_orders_60 AS (
    SELECT
        customer_id,
        COUNT(*) AS successful_orders_60
    FROM successful_orders
    WHERE order_date BETWEEN DATE_SUB(@last_date, INTERVAL 60 DAY) AND @last_date
    GROUP BY customer_id
),

successful_orders_120 AS (
    SELECT
        customer_id,
        COUNT(*) AS successful_orders_120
    FROM successful_orders
    WHERE order_date BETWEEN DATE_SUB(@last_date, INTERVAL 120 DAY) AND @last_date
    GROUP BY customer_id
),

last_successful_order AS (
    SELECT
        customer_id,
        order_id,
        order_date AS last_suc_date
    FROM (
        SELECT
            customer_id,
            order_id,
            order_date,
            ROW_NUMBER() OVER (
                PARTITION BY customer_id
                ORDER BY order_date DESC
            ) AS rn
        FROM successful_orders
    ) x
    WHERE rn = 1
),

last_successful_order_total AS (
    SELECT
        lso.customer_id,
        SUM(CASE WHEN it.returned = 0 THEN it.price_at_purchase * it.quantity ELSE 0 END)
            AS last_suc_order_total
    FROM last_successful_order lso
    JOIN items_filtered it USING(order_id)
    GROUP BY lso.customer_id
),

successful_orders_excl_last AS (
    SELECT
        so.customer_id,
        so.order_id,
        so.order_date
    FROM successful_orders so
    LEFT JOIN last_successful_order lso
        ON so.customer_id = lso.customer_id
       AND so.order_date = lso.last_suc_date
    WHERE lso.last_suc_date IS NULL
       OR so.order_date <> lso.last_suc_date
),

avg_order_value_excl_last AS (
    SELECT
        t.customer_id,
        AVG(t.order_total) AS avg_order_value
    FROM (
        SELECT
            soel.customer_id,
            SUM(CASE WHEN it.returned = 0 THEN it.price_at_purchase * it.quantity ELSE 0 END)
                AS order_total
        FROM successful_orders_excl_last soel
        JOIN items_filtered it USING(order_id)
        GROUP BY soel.order_id, soel.customer_id
    ) t
    GROUP BY t.customer_id
),

order_intervals AS (
    SELECT
        customer_id,
        DATEDIFF(
            order_date,
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS interval_days
    FROM successful_orders
),

clean_intervals AS (
    SELECT customer_id, interval_days
    FROM order_intervals
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

median_interval AS (
    SELECT
        customer_id,
        interval_days AS median_interval
    FROM ranked_intervals
    WHERE rn = FLOOR((cnt + 1) / 2)
),

pages_last_60 AS (
    SELECT
        customer_id,
        SUM(pages_viewed) AS pages_last_60
    FROM sessions_filtered
    WHERE session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 60 DAY) AND @cut_date
    GROUP BY customer_id
),

sessions_120 AS (
    SELECT
        customer_id,
        session_date,
        LAG(session_date) OVER (PARTITION BY customer_id ORDER BY session_date)
            AS prev_session_date
    FROM sessions_filtered
    WHERE session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 120 DAY) AND @cut_date
),

session_intervals_120 AS (
    SELECT
        customer_id,
        DATEDIFF(session_date, prev_session_date) AS interval_days
    FROM sessions_120
    WHERE prev_session_date IS NOT NULL
),

avg_session_interval_120 AS (
    SELECT
        customer_id,
        AVG(interval_days) AS avg_session_interval_120
    FROM session_intervals_120
    GROUP BY customer_id
),

last_session AS (
    SELECT
        customer_id,
        MAX(session_date) AS last_session_date
    FROM sessions_filtered
    GROUP BY customer_id
),

days_since_last_session AS (
    SELECT
        customer_id,
        DATEDIFF(@cut_date, last_session_date) AS days_since_last_session
    FROM last_session
),

days_since_last_successful AS (
    SELECT
        customer_id,
        DATEDIFF(@cut_date, last_suc_date) AS days_since_last_successful_order
    FROM last_successful_order
),

target AS (
    SELECT
        c.customer_id,

        CASE
            WHEN COALESCE(so120.successful_orders_120, 0) = 0
             AND COALESCE(p60.pages_last_60, 0) < 3
             AND mi.median_interval < 120
             AND lso.last_suc_order_total < 3 * aov.avg_order_value
             AND asi.avg_session_interval_120 < 60
            THEN 'CHURNED'

            WHEN COALESCE(so30.successful_orders_30, 0) > 0
            THEN 'ACTIVE'

            WHEN COALESCE(so60.successful_orders_60, 0) > 0
             AND COALESCE(so30.successful_orders_30, 0) = 0
             AND lso.last_suc_order_total >= 5 * aov.avg_order_value
            THEN 'ACTIVE'

            WHEN COALESCE(so60.successful_orders_60, 0) > 0
             AND COALESCE(so30.successful_orders_30, 0) = 0
             AND COALESCE(p60.pages_last_60, 0) >= 3
            THEN 'ACTIVE'

            WHEN dsl.days_since_last_successful_order <= mi.median_interval
             AND dss.days_since_last_session <= asi.avg_session_interval_120
            THEN 'ACTIVE'

            ELSE 'AT-RISK'
        END AS target

    FROM customers_filtered c
    LEFT JOIN successful_orders_30 so30 USING(customer_id)
    LEFT JOIN successful_orders_60 so60 USING(customer_id)
    LEFT JOIN successful_orders_120 so120 USING(customer_id)
    LEFT JOIN pages_last_60 p60 USING(customer_id)
    LEFT JOIN median_interval mi USING(customer_id)
    LEFT JOIN last_successful_order_total lso USING(customer_id)
    LEFT JOIN avg_order_value_excl_last aov USING(customer_id)
    LEFT JOIN avg_session_interval_120 asi USING(customer_id)
    LEFT JOIN days_since_last_successful dsl USING(customer_id)
    LEFT JOIN days_since_last_session dss USING(customer_id)
)

SELECT * FROM target;

"""

with engine.connect() as conn:
    conn.execute(text("SET @cut_date = '2026-01-01'"))
    conn.execute(text("SET @last_date = '2026-07-01'"))
    df = pd.read_sql_query(text(query), conn)

df.to_csv("target.csv", index=False)
print("DONE! Saved as target.csv")
