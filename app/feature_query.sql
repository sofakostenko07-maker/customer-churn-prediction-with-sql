WITH

customers_filtered AS (
    SELECT * FROM customers
),

orders_filtered AS (
    SELECT * FROM orders
),

sessions_filtered AS (
    SELECT * FROM sessions
),

order_item_level AS (
    SELECT
        oi.order_item_id,
        oi.product_id,
        oi.quantity,
        oi.price_at_purchase,
        oi.order_id,
        ofl.customer_id,
        ofl.order_date,
        ofl.status,
        ofl.status_date,
        COALESCE(oi.returned, 0) AS returned
    FROM orders_filtered ofl
    JOIN order_items oi USING(order_id)
),

successful_orders_for_intervals AS (
    SELECT DISTINCT
        oil.order_id,
        oil.customer_id,
        oil.order_date
    FROM order_item_level oil
    WHERE
        (
            oil.status = 'Completed'
            OR (
                oil.status = 'Returned'
                AND EXISTS (
                    SELECT 1 FROM order_item_level oil2
                    WHERE oil2.order_id = oil.order_id AND oil2.returned = 0
                )
            )
        )
        AND oil.order_date < date('now', '-90 days')
),

intervals AS (
    SELECT
        customer_id,
        CAST(julianday(order_date) - julianday(
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS INTEGER) AS interval_days
    FROM successful_orders_for_intervals
),

order_frequency AS (
    SELECT customer_id, AVG(interval_days) AS avg_interval
    FROM intervals GROUP BY customer_id
),

order_values AS (
    SELECT
        customer_id,
        COUNT(*) AS orders_count,
        SUM(order_total) AS total_orders_value,
        SUM(items_bought) AS total_items_per_customer
    FROM (
        SELECT
            oil.customer_id, oil.order_id,
            SUM(oil.price_at_purchase * oil.quantity) AS order_total,
            SUM(oil.quantity) AS items_bought
        FROM order_item_level oil
        WHERE oil.order_date < date('now', '-90 days')
        GROUP BY oil.order_id, oil.customer_id
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
            oil.customer_id, oil.order_id,
            SUM(CASE WHEN oil.returned = 0 THEN oil.price_at_purchase * oil.quantity ELSE 0 END) AS order_total,
            SUM(CASE WHEN oil.returned = 0 THEN oil.quantity ELSE 0 END) AS items_bought
        FROM order_item_level oil
        WHERE oil.status IN ('Completed', 'Returned')
          AND oil.order_date < date('now', '-90 days')
        GROUP BY oil.order_id, oil.customer_id
        HAVING
            SUM(CASE WHEN oil.returned = 0 THEN 1 ELSE 0 END) > 0
    ) t
    GROUP BY t.customer_id
),

successful_orders_for_intervals_90d AS (
    SELECT DISTINCT
        oil.order_id,
        oil.customer_id,
        oil.order_date
    FROM order_item_level oil
    WHERE
        (
            oil.status = 'Completed'
            OR (
                oil.status = 'Returned'
                AND EXISTS (
                    SELECT 1 FROM order_item_level oil2
                    WHERE oil2.order_id = oil.order_id AND oil2.returned = 0
                )
            )
        )
        AND oil.order_date >= date('now', '-90 days')
),

intervals_90d AS (
    SELECT customer_id,
        CAST(julianday(order_date) - julianday(
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS INTEGER) AS interval_days
    FROM successful_orders_for_intervals_90d
),

order_frequency_90d AS (
    SELECT customer_id, AVG(interval_days) AS avg_interval_90d
    FROM intervals_90d GROUP BY customer_id
),

order_values_90d AS (
    SELECT customer_id,
        COUNT(*) AS orders_count_90d,
        SUM(order_total) AS total_orders_value_90d,
        SUM(items_bought) AS total_items_per_customer_90d
    FROM (
        SELECT oil.customer_id, oil.order_id,
            SUM(oil.price_at_purchase * oil.quantity) AS order_total,
            SUM(oil.quantity) AS items_bought
        FROM order_item_level oil
        WHERE oil.order_date >= date('now', '-90 days')
        GROUP BY oil.order_id, oil.customer_id
    ) t GROUP BY t.customer_id
),

succ_order_values_90d AS (
    SELECT t.customer_id,
        AVG(order_total) AS avg_order_value_90d,
        MIN(order_total) AS min_order_value_90d,
        SUM(order_total) AS total_succ_orders_value_90d,
        COUNT(*) AS succ_orders_count_90d,
        AVG(items_bought) AS avg_items_per_order_90d,
        SUM(items_bought) AS total_succ_items_per_customer_90d
    FROM (
        SELECT oil.customer_id, oil.order_id,
            SUM(CASE WHEN oil.returned = 0 THEN oil.price_at_purchase * oil.quantity ELSE 0 END) AS order_total,
            SUM(CASE WHEN oil.returned = 0 THEN oil.quantity ELSE 0 END) AS items_bought
        FROM order_item_level oil
        WHERE oil.status IN ('Completed', 'Returned')
          AND oil.order_date >= date('now', '-90 days')
        GROUP BY oil.order_id, oil.customer_id
        HAVING
            SUM(CASE WHEN oil.returned = 0 THEN 1 ELSE 0 END) > 0
    ) t GROUP BY t.customer_id
),

account_age AS (
    SELECT customer_id,
        CAST(julianday('now') - julianday(registration_date) AS INTEGER) AS account_age_days
    FROM customers_filtered
),

last_successful_order AS (
    SELECT
        ranked.customer_id,
        ranked.order_id,
        CAST(julianday('now') - julianday(ranked.order_date) AS INTEGER) AS last_successful_date
    FROM (
        SELECT
            t.customer_id, t.order_id, t.order_date,
            ROW_NUMBER() OVER (
                PARTITION BY t.customer_id
                ORDER BY t.order_date DESC, t.order_id DESC
            ) AS rn
        FROM (
            SELECT DISTINCT
                oil.customer_id, oil.order_id, oil.order_date
            FROM order_item_level oil
            WHERE
                oil.status = 'Completed'
                OR (
                    oil.status = 'Returned'
                    AND EXISTS (
                        SELECT 1 FROM order_item_level oil2
                        WHERE oil2.order_id = oil.order_id AND oil2.returned = 0
                    )
                )
        ) t
    ) ranked
    WHERE ranked.rn = 1
),

last_successful_stats AS (
    SELECT
        lso.customer_id,
        SUM(lso.last_successful_date) AS last_suc_order_interval,
        SUM(CASE WHEN oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS last_succ_kept_order_total,
        SUM(CASE WHEN oil.returned = 0 THEN oil.quantity ELSE 0 END) AS last_succ_kept_order_items,
        SUM(oil.quantity) AS last_succ_order_items,
        SUM(oil.quantity * oil.price_at_purchase) AS last_succ_order_total
    FROM last_successful_order lso
    JOIN order_item_level oil
        ON oil.customer_id = lso.customer_id AND oil.order_id = lso.order_id
    GROUP BY lso.customer_id
),

full_return_orders AS (
    SELECT
        oil.order_id, oil.customer_id, oil.status_date,
        SUM(oil.quantity * oil.price_at_purchase) AS full_return_total
    FROM order_item_level oil
    WHERE oil.status = 'Returned'
    GROUP BY oil.order_id, oil.customer_id, oil.status_date
    HAVING SUM(CASE WHEN oil.returned = 0 THEN 1 ELSE 0 END) = 0
),

last_return_date AS (
    SELECT t.customer_id, t.order_id, t.status_date AS return_date
    FROM (
        SELECT customer_id, order_id, status_date,
            ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY status_date DESC, order_id DESC) AS rn
        FROM full_return_orders
    ) t WHERE rn = 1
),

last_return_order AS (
    SELECT
        t.customer_id, t.order_id,
        CAST(julianday('now') - julianday(t.return_date) AS INTEGER) AS days_from_last_return,
        t.full_return_total
    FROM (
        SELECT lrd.customer_id, lrd.order_id, lrd.return_date, fro.full_return_total
        FROM full_return_orders fro
        JOIN last_return_date lrd
            ON fro.customer_id = lrd.customer_id AND fro.order_id = lrd.order_id
    ) t
),

last_return_stats AS (
    SELECT
        lro.customer_id,
        SUM(lro.days_from_last_return) AS days_from_last_return,
        SUM(CASE WHEN oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS last_return_total,
        SUM(CASE WHEN oil.returned = 1 THEN oil.quantity ELSE 0 END) AS last_returned_items
    FROM order_item_level oil
    JOIN last_return_order lro
        ON lro.customer_id = oil.customer_id AND lro.order_id = oil.order_id
    GROUP BY lro.customer_id
),

last_cancel_order AS (
    SELECT
        ranked.customer_id,
        ranked.order_id,
        CAST(julianday('now') - julianday(ranked.status_date) AS INTEGER) AS days_from_last_cancel
    FROM (
        SELECT
            t.customer_id, t.order_id, t.status_date,
            ROW_NUMBER() OVER (
                PARTITION BY t.customer_id
                ORDER BY t.status_date DESC, t.order_id DESC
            ) AS rn
        FROM (
            SELECT DISTINCT
                oil.customer_id, oil.order_id, oil.status_date
            FROM order_item_level oil
            WHERE oil.status = 'Cancelled'
        ) t
    ) ranked
    WHERE ranked.rn = 1
),

last_cancel_stats AS (
    SELECT
        lco.customer_id,
        SUM(lco.days_from_last_cancel) AS days_from_last_cancel,
        SUM(oil.quantity) AS last_cancel_items,
        SUM(oil.quantity * oil.price_at_purchase) AS last_cancel_total
    FROM order_item_level oil
    JOIN last_cancel_order lco
        ON lco.customer_id = oil.customer_id AND lco.order_id = oil.order_id
    GROUP BY lco.customer_id
),

last3_order_ids AS (
    SELECT ranked.customer_id, ranked.order_id
    FROM (
        SELECT
            t.customer_id, t.order_id, t.order_date,
            ROW_NUMBER() OVER (
                PARTITION BY customer_id
                ORDER BY order_date DESC, order_id DESC
            ) AS rn
        FROM (
            SELECT DISTINCT customer_id, order_id, order_date
            FROM order_item_level
        ) t
    ) ranked
    WHERE ranked.rn <= 3
),

last3_succ_orders AS (
    SELECT ranked.customer_id, ranked.order_id, ranked.order_date
    FROM (
        SELECT
            t.customer_id, t.order_id, t.order_date,
            ROW_NUMBER() OVER (
                PARTITION BY t.customer_id
                ORDER BY t.order_date DESC, t.order_id DESC
            ) AS rn
        FROM (
            SELECT DISTINCT
                oil.customer_id, oil.order_id, oil.order_date
            FROM order_item_level oil
            WHERE
                oil.status = 'Completed'
                OR (
                    oil.status = 'Returned'
                    AND EXISTS (
                        SELECT 1 FROM order_item_level oil2
                        WHERE oil2.order_id = oil.order_id AND oil2.returned = 0
                    )
                )
        ) t
    ) ranked
    WHERE ranked.rn <= 3
),

last3_succ_orders_help_table AS (
    SELECT
        l3so.customer_id, l3so.order_id,
        SUM(CASE WHEN oil.returned = 0 THEN oil.price_at_purchase * oil.quantity ELSE 0 END) AS last3_succ_kept_total,
        SUM(CASE WHEN oil.returned = 0 THEN oil.quantity ELSE 0 END) AS last3_succ_kept_items,
        SUM(oil.quantity * oil.price_at_purchase) AS total_value,
        SUM(oil.quantity) AS total_items,
        CAST(julianday(l3so.order_date) - julianday(
            LAG(l3so.order_date) OVER (PARTITION BY l3so.customer_id ORDER BY l3so.order_date, l3so.order_id)
        ) AS INTEGER) AS interval_days
    FROM last3_succ_orders l3so
    JOIN order_item_level oil USING(order_id)
    GROUP BY l3so.customer_id, l3so.order_id, l3so.order_date
),

last3_succ_orders_stats AS (
    SELECT customer_id,
        AVG(interval_days) AS avg_last3_succ_interval,
        SUM(last3_succ_kept_items) AS last3_succ_orders_kept_items_total,
        SUM(last3_succ_kept_total) AS last3_succ_orders_kept_total,
        SUM(total_value) AS last3_succ_orders_total,
        SUM(total_items) AS last3_succ_orders_items
    FROM last3_succ_orders_help_table GROUP BY customer_id
),

last3_orders_help_table AS (
    SELECT
        l3.customer_id,
        SUM(
            CASE
                WHEN (oil.status = 'Returned' AND oil.returned = 1) OR oil.status = 'Cancelled'
                THEN oil.quantity * oil.price_at_purchase
                ELSE 0
            END
        ) AS return_cancel_order_total,
        SUM(oil.quantity * oil.price_at_purchase) AS last_3orders_total,
        SUM(
            CASE
                WHEN (oil.status = 'Returned' AND oil.returned = 1) OR oil.status = 'Cancelled'
                THEN oil.quantity
                ELSE 0
            END
        ) AS return_cancel_order_items,
        SUM(oil.quantity) AS last_3orders_items
    FROM last3_order_ids l3
    JOIN order_item_level oil
        ON l3.customer_id = oil.customer_id AND l3.order_id = oil.order_id
    GROUP BY l3.customer_id
),

last3_orders_stats AS (
    SELECT customer_id,
        return_cancel_order_total AS last3_return_cancel_order_total,
        (last_3orders_total - return_cancel_order_total) AS last3_kept_total,
        return_cancel_order_items AS last3_cancels_returns_items,
        (last_3orders_items - return_cancel_order_items) AS last3_kept_items
    FROM last3_orders_help_table
),

category_counts AS (
    SELECT
        oil.customer_id,
        SUM(CASE WHEN p.category = 'Automotive' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS automotive_items,
        SUM(CASE WHEN p.category = 'Automotive' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS automotive_spent,
        SUM(CASE WHEN p.category = 'Beauty' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS beauty_items,
        SUM(CASE WHEN p.category = 'Beauty' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS beauty_spent,
        SUM(CASE WHEN p.category = 'Books' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS books_items,
        SUM(CASE WHEN p.category = 'Books' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS books_spent,
        SUM(CASE WHEN p.category = 'Electronics' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS electronics_items,
        SUM(CASE WHEN p.category = 'Electronics' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS electronics_spent,
        SUM(CASE WHEN p.category = 'Fashion' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS fashion_items,
        SUM(CASE WHEN p.category = 'Fashion' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS fashion_spent,
        SUM(CASE WHEN p.category = 'Food' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS food_items,
        SUM(CASE WHEN p.category = 'Food' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS food_spent,
        SUM(CASE WHEN p.category = 'Home' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS home_items,
        SUM(CASE WHEN p.category = 'Home' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS home_spent,
        SUM(CASE WHEN p.category = 'Pets' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS pets_items,
        SUM(CASE WHEN p.category = 'Pets' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS pets_spent,
        SUM(CASE WHEN p.category = 'Sports' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS sports_items,
        SUM(CASE WHEN p.category = 'Sports' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS sports_spent,
        SUM(CASE WHEN p.category = 'Toys' AND oil.returned = 0 THEN oil.quantity ELSE 0 END) AS toys_items,
        SUM(CASE WHEN p.category = 'Toys' AND oil.returned = 0 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS toys_spent
    FROM order_item_level oil
    JOIN products p USING(product_id)
    WHERE oil.status IN ('Completed', 'Returned')
    GROUP BY oil.customer_id
),

category_returns_counts AS (
    SELECT
        oil.customer_id,
        SUM(CASE WHEN p.category = 'Automotive' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS automotive_items_returned,
        SUM(CASE WHEN p.category = 'Automotive' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS automotive_returned_total,
        SUM(CASE WHEN p.category = 'Beauty' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS beauty_items_returned,
        SUM(CASE WHEN p.category = 'Beauty' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS beauty_returned_total,
        SUM(CASE WHEN p.category = 'Books' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS books_items_returned,
        SUM(CASE WHEN p.category = 'Books' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS books_returned_total,
        SUM(CASE WHEN p.category = 'Electronics' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS electronics_items_returned,
        SUM(CASE WHEN p.category = 'Electronics' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS electronics_returned_total,
        SUM(CASE WHEN p.category = 'Fashion' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS fashion_items_returned,
        SUM(CASE WHEN p.category = 'Fashion' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS fashion_returned_total,
        SUM(CASE WHEN p.category = 'Food' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS food_items_returned,
        SUM(CASE WHEN p.category = 'Food' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS food_returned_total,
        SUM(CASE WHEN p.category = 'Home' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS home_items_returned,
        SUM(CASE WHEN p.category = 'Home' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS home_returned_total,
        SUM(CASE WHEN p.category = 'Pets' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS pets_items_returned,
        SUM(CASE WHEN p.category = 'Pets' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS pets_returned_total,
        SUM(CASE WHEN p.category = 'Sports' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS sports_items_returned,
        SUM(CASE WHEN p.category = 'Sports' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS sports_returned_total,
        SUM(CASE WHEN p.category = 'Toys' AND oil.returned = 1 THEN oil.quantity ELSE 0 END) AS toys_items_returned,
        SUM(CASE WHEN p.category = 'Toys' AND oil.returned = 1 THEN oil.quantity * oil.price_at_purchase ELSE 0 END) AS toys_returned_total
    FROM order_item_level oil
    JOIN products p USING(product_id)
    WHERE oil.status = 'Returned'
    GROUP BY oil.customer_id
),

discount_stats AS (
    SELECT
        oil.customer_id,
        SUM(CASE WHEN oil.price_at_purchase < p.base_price THEN oil.quantity ELSE 0 END) AS discounted_items_total
    FROM order_item_level oil
    JOIN products p USING(product_id)
    WHERE oil.status IN ('Returned', 'Completed')
    GROUP BY oil.customer_id
),

last_session AS (
    SELECT
        customer_id, session_date, pages_viewed,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY session_date DESC
        ) AS rn
    FROM sessions_filtered
    WHERE session_date >= date('now', '-180 days')
      AND session_date < date('now')
),

last_session_stats AS (
    SELECT
        customer_id,
        CAST(julianday('now') - julianday(session_date) AS INTEGER) AS days_from_last_session,
        pages_viewed AS last_session_pages_viewed
    FROM last_session
    WHERE rn = 1
),

successful_orders_180 AS (
    SELECT
        customer_id,
        COUNT(DISTINCT oil.order_id) AS successful_orders_180
    FROM order_item_level oil
    WHERE oil.order_date >= date('now', '-180 days')
      AND oil.order_date < date('now')
      AND (
            oil.status = 'Completed'
            OR (
                oil.status = 'Returned'
                AND EXISTS (
                    SELECT 1 FROM order_item_level oil2
                    WHERE oil2.order_id = oil.order_id AND oil2.returned = 0
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
    WHERE sfl.session_date >= date('now', '-180 days')
      AND sfl.session_date < date('now')
    GROUP BY sfl.customer_id
),

sessions_to_succ_orders_ratio_180 AS (
    SELECT
        s180.customer_id,
        CAST(so180.successful_orders_180 AS REAL) / NULLIF(s180.total_180days_sessions, 0) AS sessions_to_succ_orders_180days
    FROM successful_orders_180 so180
    JOIN sessions_180_stats s180 USING(customer_id)
),

recent_sessions_90 AS (
    SELECT customer_id, COUNT(*) AS sessions_90d, AVG(pages_viewed) AS avg_pages_90d
    FROM sessions_filtered
    WHERE session_date >= date('now', '-90 days')
      AND session_date < date('now')
    GROUP BY customer_id
),

session_intervals AS (
    SELECT customer_id, AVG(interval_days) AS avg_session_interval
    FROM (
        SELECT customer_id,
            CAST(julianday(session_date) - julianday(
                LAG(session_date) OVER (PARTITION BY customer_id ORDER BY session_date)
            ) AS INTEGER) AS interval_days
        FROM sessions_filtered
    ) t
    WHERE interval_days IS NOT NULL
    GROUP BY customer_id
)

SELECT
    cfl.customer_id,
    COALESCE(aa.account_age_days, 1) AS account_age_days,
    cfl.birth_date,
    COALESCE(1.0 / NULLIF(ofq.avg_interval, 0), 0) AS shopping_frequency,
    (COALESCE(ov.orders_count, 0) - COALESCE(sov.succ_orders_count, 0)) AS unsuccessful_orders_count,
    COALESCE(sov.succ_orders_count, 0) AS succ_orders_count,
    COALESCE(sov.avg_order_value, 0) AS avg_order_value,
    COALESCE(sov.min_order_value, 0) AS min_order_value,
    COALESCE(sov.avg_items_per_order, 0) AS avg_items_per_order,
    COALESCE(sov.total_succ_items_per_customer, 0) AS total_succ_items_per_customer,
    (COALESCE(ov.total_orders_value, 0) - COALESCE(sov.total_succ_orders_value, 0)) AS return_cancel_orders_values,
    (COALESCE(ov.total_items_per_customer, 0) - COALESCE(sov.total_succ_items_per_customer, 0)) AS return_cancel_orders_items,
    COALESCE(1.0 / NULLIF(of90.avg_interval_90d, 0), 0) AS shopping_frequency_90d,
    (COALESCE(ov90.orders_count_90d, 0) - COALESCE(sov90.succ_orders_count_90d, 0)) AS unsuccessful_orders_count_90d,
    COALESCE(sov90.succ_orders_count_90d, 0) AS succ_orders_count_90d,
    COALESCE(sov90.avg_order_value_90d, 0) AS avg_order_value_90d,
    COALESCE(sov90.min_order_value_90d, 0) AS min_order_value_90d,
    COALESCE(sov90.avg_items_per_order_90d, 0) AS avg_items_per_order_90d,
    COALESCE(sov90.total_succ_items_per_customer_90d, 0) AS total_succ_items_per_customer_90d,
    (COALESCE(ov90.total_orders_value_90d, 0) - COALESCE(sov90.total_succ_orders_value_90d, 0)) AS return_cancel_orders_values_90d,
    (COALESCE(ov90.total_items_per_customer_90d, 0) - COALESCE(sov90.total_succ_items_per_customer_90d, 0)) AS return_cancel_orders_items_90d,
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
LEFT JOIN order_values_90d ov90 USING(customer_id)
LEFT JOIN succ_order_values_90d sov90 USING(customer_id)
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