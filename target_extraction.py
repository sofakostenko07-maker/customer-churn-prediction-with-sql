import pandas as pd
from sqlalchemy import create_engine, text

USER = "...."
PASSWORD = "...."
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

sessions_filtered AS (
    SELECT 
        s.*
    FROM sessions s
    JOIN customers_filtered cf USING(customer_id)
),

orders_filtered AS (
    SELECT 
        o.*
    FROM orders o
    JOIN customers_filtered cf USING(customer_id)
),

items_filtered AS (
    SELECT 
        oi.*
    FROM order_items oi 
    JOIN orders_filtered ofl USING(order_id)
),

sessions_120 AS (
    SELECT 
        customer_id,
        session_date,
        pages_viewed,
        LAG(session_date) OVER (
            PARTITION BY customer_id ORDER BY session_date
        ) AS prev_session_date
    FROM sessions_filtered
    WHERE session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 120 DAY)
                           AND @cut_date
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

pages_last_60 AS (
    SELECT 
        customer_id,
        SUM(pages_viewed) AS pages_last_60
    FROM sessions_filtered
    WHERE session_date BETWEEN DATE_SUB(@cut_date, INTERVAL 60 DAY)
                           AND @cut_date
    GROUP BY customer_id
),

successful_orders_30 AS (
    SELECT 
        ofl.customer_id,
        COUNT(*) AS successful_orders_30
    FROM orders_filtered ofl
    WHERE ofl.order_date BETWEEN DATE_SUB(@cut_date, INTERVAL 30 DAY)
                             AND @cut_date
      AND ofl.status IN ('Cancelled','Returned')
      AND EXISTS (
            SELECT 1 FROM items_filtered it
            WHERE it.order_id = ofl.order_id
              AND it.returned = 0
      )
    GROUP BY ofl.customer_id
),

successful_orders_60 AS (
    SELECT 
        ofl.customer_id,
        COUNT(*) AS successful_orders_60
    FROM orders_filtered ofl
    WHERE ofl.order_date BETWEEN DATE_SUB(@cut_date, INTERVAL 60 DAY)
                             AND @cut_date
      AND ofl.status IN ('Cancelled','Returned')
      AND EXISTS (
            SELECT 1 FROM items_filtered it
            WHERE it.order_id = ofl.order_id
              AND it.returned = 0
      )
    GROUP BY ofl.customer_id
),

successful_orders_120 AS (
    SELECT 
        ofl.customer_id,
        COUNT(*) AS successful_orders_120
    FROM orders_filtered ofl
    WHERE ofl.order_date BETWEEN DATE_SUB(@cut_date, INTERVAL 120 DAY)
                             AND @cut_date
      AND ofl.status IN ('Cancelled','Returned')
      AND EXISTS (
            SELECT 1 FROM items_filtered it
            WHERE it.order_id = ofl.order_id
              AND it.returned = 0
      )
    GROUP BY ofl.customer_id
),

last_successful_order_info AS (
    SELECT 
        ofl.customer_id,
        MAX(ofl.order_date) AS last_suc_date
    FROM orders_filtered ofl
    WHERE ofl.status IN ('Cancelled','Returned')
      AND EXISTS (
        SELECT 1 FROM items_filtered it
        WHERE it.order_id = ofl.order_id
          AND it.returned = 0
    )
    GROUP BY ofl.customer_id
),

days_since_last_successful AS (
    SELECT 
        customer_id,
        DATEDIFF(@cut_date, last_suc_date) AS days_since_last_successful_order
    FROM last_successful_order_info
),

last_session_info AS (
    SELECT 
        customer_id,
        MAX(session_date) AS last_session_date
    FROM sessions_filtered
    WHERE session_date < @cut_date
    GROUP BY customer_id
),

days_since_last_session AS (
    SELECT 
        customer_id,
        DATEDIFF(@cut_date, last_session_date) AS days_since_last_session
    FROM last_session_info
),

target AS (
    SELECT 
        c.customer_id,
        CASE
            WHEN so120.successful_orders_120 = 0
             AND p60.pages_last_60 < 3
             AND c.median_interval < 120
             AND c.last_suc_order_total < 3 * c.avg_order_value
             AND asi.avg_session_interval_120 < 60
            THEN 'CHURNED'
            WHEN so30.successful_orders_30 > 0
            THEN 'ACTIVE'
            WHEN so60.successful_orders_60 > 0
             AND so30.successful_orders_30 = 0
             AND c.last_suc_order_total >= 5 * c.avg_order_value
            THEN 'ACTIVE'
            WHEN so60.successful_orders_60 > 0
             AND so30.successful_orders_30 = 0
             AND p60.pages_last_60 >= 3
            THEN 'ACTIVE'
            WHEN dsl.days_since_last_successful_order <= c.median_interval
             AND dss.days_since_last_session <= asi.avg_session_interval_120
            THEN 'ACTIVE'
            ELSE 'AT-RISK'
        END AS target
    FROM customers_filtered c
    LEFT JOIN successful_orders_30 so30 USING(customer_id)
    LEFT JOIN successful_orders_60 so60 USING(customer_id)
    LEFT JOIN successful_orders_120 so120 USING(customer_id)
    LEFT JOIN pages_last_60 p60 USING(customer_id)
    LEFT JOIN avg_session_interval_120 asi USING(customer_id)
    LEFT JOIN days_since_last_successful dsl USING(customer_id)
    LEFT JOIN days_since_last_session dss USING(customer_id)
)

SELECT * FROM target;
"""

with engine.connect() as conn:
    conn.execute(text("SET @cut_date = '2026-01-01'"))
    df = pd.read_sql_query(text(query), conn)

df.to_csv("target.csv", index=False)
print("DONE! Saved as target.csv")
