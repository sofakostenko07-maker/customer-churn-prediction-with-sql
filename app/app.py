import streamlit as st
import pandas as pd
import joblib

from pipeline import (
    build_feature_matrix,
    prediction_pipeline
)

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_A_PATH = os.path.join(BASE_DIR, "model_A.joblib")
MODEL_B_PATH = os.path.join(BASE_DIR, "model_B.joblib")
NORM_PARAMS_PATH = os.path.join(BASE_DIR, "normalization_params.joblib")
PRODUCTS_PATH = os.path.join(BASE_DIR, "products.csv")


st.set_page_config(page_title="Churn Prediction", layout="wide")
st.title("Customer Churn Prediction")


@st.cache_resource
def load_models():
    model_A = joblib.load(MODEL_A_PATH)
    model_B = joblib.load(MODEL_B_PATH)
    norm_params = joblib.load(NORM_PARAMS_PATH)

    return model_A, model_B, norm_params


@st.cache_data
def load_products():
    return pd.read_csv(PRODUCTS_PATH)



model_A, model_B, norm_params = load_models()
products_df = load_products()

VALID_STATUSES = ["Completed", "Returned", "Cancelled"]

st.subheader("1. Provide customer data")

mode = st.radio(
    "How do you want to provide the data?",
    ["Upload CSV files", "Enter manually"],
)

REQUIRED_COLUMNS = {
    "customers": ["customer_id", "registration_date"],
    "orders": ["order_id", "customer_id", "order_date", "status", "status_date"],
    "order_items": ["order_item_id", "order_id", "product_id", "quantity", "price_at_purchase", "returned"],
    "sessions": ["session_id", "customer_id", "session_date", "device", "pages_viewed"],
}


def validate_columns(df, name):
    missing = [c for c in REQUIRED_COLUMNS[name] if c not in df.columns]
    if missing:
        st.error(f"'{name}' file is missing required columns: {missing}")
        return False
    return True


def normalize_and_validate_status(df):
    df["status"] = df["status"].astype(str).str.strip().str.capitalize()
    bad_statuses = set(df["status"]) - set(VALID_STATUSES)
    if bad_statuses:
        st.error(
            f"'orders' file has unrecognized status values: {sorted(bad_statuses)}. "
            f"Allowed values: {', '.join(VALID_STATUSES)}."
        )
        return False
    return True


def validate_dates(df, date_columns, name, optional_columns=None):
    optional_columns = optional_columns or []
    today = pd.Timestamp.now().normalize()
    ok = True
    for col in date_columns:
        if col not in df.columns:
            continue

        raw = df[col].astype(str).str.strip()
        is_empty = raw.eq("") | raw.eq("nan") | raw.eq("None")
        parsed = pd.to_datetime(df[col], errors="coerce")

        if col in optional_columns:
            unparseable = (~is_empty) & parsed.isna()
        else:
            unparseable = parsed.isna()

        if unparseable.any():
            st.error(
                f"'{name}.{col}' has {unparseable.sum()} value(s) that aren't valid dates "
                f"(expected format: YYYY-MM-DD, e.g. 1990-05-20) — please fix before running."
            )
            ok = False
            continue

        future = parsed.notna() & (parsed > today)
        if future.any():
            st.error(f"'{name}.{col}' contains {future.sum()} date(s) in the future — please fix before running.")
            ok = False

    return ok


NUMERIC_COLUMNS = {
    "customers": ["customer_id"],
    "orders": ["order_id", "customer_id"],
    "order_items": ["order_item_id", "order_id", "product_id", "quantity", "price_at_purchase", "returned"],
    "sessions": ["session_id", "customer_id", "pages_viewed"],
}


def coerce_numeric_columns(df, name):
    for col in NUMERIC_COLUMNS.get(name, []):
        if col not in df.columns:
            continue
        original = df[col]
        coerced = pd.to_numeric(original, errors="coerce")
        was_present = original.notna() & (original.astype(str).str.strip() != "")
        failed = was_present & coerced.isna()
        if failed.any():
            st.warning(f"'{name}.{col}' had {failed.sum()} non-numeric value(s) — replaced with 0.")
        df[col] = coerced.fillna(0)
    return df


customers_df = orders_df = order_items_df = sessions_df = None

if mode == "Upload CSV files":
    st.write("Upload four CSV files, one per table:")
    st.write("CSV files must contain the following columns:")
    st.markdown("""
    - **customers.csv**: `customer_id`, `registration_date` (optionally `birth_date`)
    - **orders.csv**: `order_id`, `customer_id`, `order_date`, `status`, `status_date`
    - **order_items.csv**: `order_item_id`, `order_id`, `product_id`, `quantity`, `price_at_purchase`, `returned`
    - **sessions.csv**: `session_id`, `customer_id`, `session_date`, `device`, `pages_viewed`
        """)
    st.write("Other unspecified columns can be present in CSV and will be deleted automatically")
    st.caption("Dates: please use YYYY-MM-DD (e.g. 1990-05-20) to avoid day/month ambiguity")
    st.caption("Customer birth_date is optional — missing values are replaced with the median customer age.")
    st.caption("Product IDs range between 1 and 20000 and are fixed, as offered by the shop's product catalog.")
    st.caption(f"orders.csv 'status' column: allowed values are {', '.join(VALID_STATUSES)} (any casing/spacing is auto-corrected).")

    customers_file = st.file_uploader("customers.csv", type="csv", key="customers_csv")
    orders_file = st.file_uploader("orders.csv", type="csv", key="orders_csv")
    order_items_file = st.file_uploader("order_items.csv", type="csv", key="order_items_csv")
    sessions_file = st.file_uploader("sessions.csv", type="csv", key="sessions_csv")

    if customers_file and orders_file and order_items_file and sessions_file:
        customers_df = pd.read_csv(customers_file)
        orders_df = pd.read_csv(orders_file)
        order_items_df = pd.read_csv(order_items_file)
        sessions_df = pd.read_csv(sessions_file)

        checks = [
            validate_columns(customers_df, "customers"),
            validate_columns(orders_df, "orders"),
            validate_columns(order_items_df, "order_items"),
            validate_columns(sessions_df, "sessions"),
        ]

        if all(checks):
            checks.append(normalize_and_validate_status(orders_df))
            checks.append(validate_dates(customers_df, ["registration_date", "birth_date"], "customers", optional_columns=["birth_date"]))
            checks.append(validate_dates(orders_df, ["order_date", "status_date"], "orders"))
            checks.append(validate_dates(sessions_df, ["session_date"], "sessions"))

        if not all(checks):
            customers_df = None
        else:
            customers_df = coerce_numeric_columns(customers_df, "customers")
            orders_df = coerce_numeric_columns(orders_df, "orders")
            order_items_df = coerce_numeric_columns(order_items_df, "order_items")
            sessions_df = coerce_numeric_columns(sessions_df, "sessions")

if mode == "Enter manually":
    st.write("Fill in the tables below (add rows as needed):")
    st.caption("Dates: please use YYYY-MM-DD (e.g. 1990-05-20).")
    st.caption("Customer birth_date is optional — missing values are replaced with the median customer age.")
    st.caption("Product IDs range between 1 and 20000 and are fixed, as offered by the shop's product catalog.")

    example_customer = pd.DataFrame([{
        "customer_id": 1,
        "registration_date": "2024-01-15",
        "birth_date": "1990-05-20"
    }])

    st.markdown("**Example customer:**")
    st.dataframe(example_customer)

    st.markdown("**Customers**")
    customers_df = st.data_editor(
        pd.DataFrame(columns=["customer_id", "registration_date", "birth_date"]),
        num_rows="dynamic",
        key="customers_editor",
    )

    st.markdown("**Orders**")
    orders_df = st.data_editor(
        pd.DataFrame(columns=["order_id", "customer_id", "order_date", "status", "status_date"]),
        num_rows="dynamic",
        key="orders_editor",
        column_config={
            "status": st.column_config.SelectboxColumn(
                "status", options=VALID_STATUSES, required=True
            ),
        },
    )

    st.markdown("**Order items**")
    order_items_df = st.data_editor(
        pd.DataFrame(columns=["order_item_id", "order_id", "product_id", "quantity", "price_at_purchase", "returned"]),
        num_rows="dynamic",
        key="order_items_editor",
    )

    st.markdown("**Sessions**")
    sessions_df = st.data_editor(
        pd.DataFrame(columns=["session_id", "customer_id", "session_date", "device", "pages_viewed"]),
        num_rows="dynamic",
        key="sessions_editor",
    )

    if customers_df is not None and not customers_df.empty:
        if not validate_dates(customers_df, ["registration_date", "birth_date"], "customers", optional_columns=["birth_date"]):
            customers_df = None

    if orders_df is not None and not orders_df.empty:
        if not validate_dates(orders_df, ["order_date", "status_date"], "orders"):
            orders_df = None

    if sessions_df is not None and not sessions_df.empty:
        if not validate_dates(sessions_df, ["session_date"], "sessions"):
            sessions_df = None

    if customers_df is not None and not customers_df.empty:
        customers_df = coerce_numeric_columns(customers_df, "customers")
    if orders_df is not None and not orders_df.empty:
        orders_df = coerce_numeric_columns(orders_df, "orders")
    if order_items_df is not None and not order_items_df.empty:
        order_items_df = coerce_numeric_columns(order_items_df, "order_items")
    if sessions_df is not None and not sessions_df.empty:
        sessions_df = coerce_numeric_columns(sessions_df, "sessions")

st.subheader("2. Offer score weights")
st.caption("Choose how much churn risk vs. customer value should drive the offer score. The two values must add up to 1.")

col1, col2 = st.columns(2)

with col1:
    churn_coef = st.number_input(
        "Churn risk weight",
        min_value=0.0, max_value=1.0, value=0.6, step=0.05,
        key="churn_coef_input",
    )

with col2:
    ltv_coef = st.number_input(
        "LTV weight",
        min_value=0.0, max_value=1.0, value=0.4, step=0.05,
        key="ltv_coef_input",
    )

weights_valid = abs((churn_coef + ltv_coef) - 1.0) < 1e-6

if not weights_valid:
    st.error(f"Churn weight + LTV weight must equal 1.0 (currently {churn_coef + ltv_coef:.2f}).")

st.subheader("3. Run prediction")

data_ready = (
    customers_df is not None and not customers_df.empty and
    orders_df is not None and not orders_df.empty and
    order_items_df is not None and not order_items_df.empty and
    sessions_df is not None and not sessions_df.empty
)

if st.button("Run prediction", type="primary", disabled=not (data_ready and weights_valid)):
    with st.spinner("Building features from raw data..."):
        feature_matrix = build_feature_matrix(
            customers_df, orders_df, order_items_df, sessions_df, products_df
        )

    with st.spinner("Scoring customers..."):
        result = prediction_pipeline(
            feature_matrix, model_A, model_B, norm_params, churn_coef, ltv_coef
        )

    st.subheader("4. Results")
    st.dataframe(result)

    st.download_button(
        "Download predictions as CSV",
        result.to_csv(index=False).encode("utf-8"),
        file_name="predictions.csv",
        mime="text/csv",
    )

if not data_ready:
    st.info("Provide data for all four tables above (upload files or fill the tables) before running.")
elif not weights_valid:
    st.info("Fix the offer score weights above so they add up to 1.0 before running.")