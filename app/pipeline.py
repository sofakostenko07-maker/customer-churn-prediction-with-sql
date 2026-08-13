import sqlite3
import pandas as pd
import numpy as np

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


FEATURES = [
    "customer_id",
    "account_age_days",
    "birth_date",
    "shopping_frequency",
    "unsuccessful_orders_count",
    "succ_orders_count",
    "avg_order_value",
    "min_order_value",
    "avg_items_per_order",
    "total_succ_items_per_customer",
    "return_cancel_orders_values",
    "return_cancel_orders_items",
    "shopping_frequency_90d",
    "unsuccessful_orders_count_90d",
    "succ_orders_count_90d",
    "avg_order_value_90d",
    "min_order_value_90d",
    "avg_items_per_order_90d",
    "total_succ_items_per_customer_90d",
    "return_cancel_orders_values_90d",
    "return_cancel_orders_items_90d",
    "last_suc_order_interval",
    "last_succ_kept_order_total",
    "last_succ_kept_order_items",
    "last_succ_order_items",
    "last_succ_order_total",
    "days_from_last_return",
    "last_return_total",
    "last_returned_items",
    "days_from_last_cancel",
    "last_cancel_items",
    "last_cancel_total",
    "avg_last3_succ_interval",
    "last3_succ_orders_kept_items_total",
    "last3_succ_orders_kept_total",
    "last3_succ_orders_total",
    "last3_succ_orders_items",
    "last3_return_cancel_order_total",
    "last3_kept_total",
    "last3_cancels_returns_items",
    "last3_kept_items",
    "automotive_items",
    "automotive_spent",
    "beauty_items",
    "beauty_spent",
    "books_items",
    "books_spent",
    "electronics_items",
    "electronics_spent",
    "fashion_items",
    "fashion_spent",
    "food_items",
    "food_spent",
    "home_items",
    "home_spent",
    "pets_items",
    "pets_spent",
    "sports_items",
    "sports_spent",
    "toys_items",
    "toys_spent",
    "automotive_items_returned",
    "automotive_returned_total",
    "beauty_items_returned",
    "beauty_returned_total",
    "books_items_returned",
    "books_returned_total",
    "electronics_items_returned",
    "electronics_returned_total",
    "fashion_items_returned",
    "fashion_returned_total",
    "food_items_returned",
    "food_returned_total",
    "home_items_returned",
    "home_returned_total",
    "pets_items_returned",
    "pets_returned_total",
    "sports_items_returned",
    "sports_returned_total",
    "toys_items_returned",
    "toys_returned_total",
    "discounted_items_total",
    "total_180days_sessions",
    "avg_pages_viewed_180",
    "min_pages_viewed_180",
    "mobile_sessions_count_180",
    "desktop_sessions_count_180",
    "sessions_to_succ_orders_180days",
    "sessions_90d",
    "avg_pages_90d",
    "days_from_last_session",
    "last_session_pages_viewed",
    "avg_session_interval"
]

drop_A = [
        "gender",
        "automotive_items_returned",
        "beauty_items_returned",
        "books_items_returned",
        "electronics_items_returned",
        "fashion_items_returned",
        "food_items_returned",
        "home_items_returned",
        "pets_items_returned",
        "sports_items_returned",
        "toys_items_returned"
]


drop_B = [
    "beauty_items",
    "automotive_spent",
    "last3_kept_total",
    "last3_cancels_returns_items",
    "last3_succ_orders_kept_total",
    "last3_return_cancel_order_total",
    "last_cancel_total",
    "last_cancel_items",
    "last_succ_order_items",
    "last_succ_kept_order_total",
    "last_succ_order_total",
    "days_from_last_return",
    "last_return_total",
    "last_returned_items",
    # "succ_orders_count_90d",  # KEEP
    "avg_items_per_order_90d",
    "min_order_value_90d",
    "total_succ_items_per_customer_90d",
    # "avg_order_value_90d",    # KEEP
    "return_cancel_orders_items",
    "gender",
    "account_age_days",
    "unsuccessful_orders_count",
    "food_spent",
    "pets_items",
    "home_spent",
    "home_items",
    "food_items",
    "fashion_items",
    "books_spent",
    "sports_items_returned",
    "pets_returned_total",
    "pets_items_returned",
    "home_returned_total",
    "home_items_returned",
    "food_returned_total",
    "food_items_returned",
    "fashion_returned_total",
    "fashion_items_returned",
    "electronics_returned_total",
    "electronics_items_returned",
    "books_returned_total",
    "beauty_returned_total",
    "beauty_items_returned",
    "toys_spent",
    "automotive_items_returned",
    "electronics_items",
    "electronics_spent",
    "toys_items",
    "sports_spent",
    "toys_returned_total",
    "sports_returned_total",
    "avg_pages_viewed_180",
    "last_session_pages_to_avg90",
    "last3_kept_value_ratio",
    "last3_kept_items_ratio",
    "last_kept_items_ratio",
    "last3_succ_kept_value_to_avg_ratio",
    "avg_order_value_recent_ratio",
    "last_succ_kept_value_to_avg_ratio",
    "sessions_per_success_order_90d",
    "min_order_value_delta"
]


def offer_score(p_churn_clip, ltv_norm, churn_coef=0.6, ltv_coef=0.4):
    offer_score = (churn_coef*p_churn_clip) + (ltv_coef*ltv_norm) + 1
    return offer_score

def norm_ltv(ltv, ltv_min, ltv_max):
  norm_ltv = (ltv - ltv_min) / (ltv_max - ltv_min)
  return norm_ltv

def p_churn_clip(p_churn, p_churn_cap):
    p_norm = p_churn / p_churn_cap
    return np.clip(p_norm, 0, 1)
def select_features(df, feature_list=FEATURES):
    missing = [f for f in feature_list if f not in df.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    return df[feature_list].copy()


def basic_cleaning(df, birth_mode):
    df = df.copy()
    if 'customer_id' in df.columns:
      df = df.drop(columns=['customer_id'])
    df['birth_date'] = df['birth_date'].fillna(birth_mode)
    df['birth_date'] = pd.to_datetime(df['birth_date'])
    reference_date = pd.to_datetime('2026-01-01')
    df['client_age'] = ((reference_date - df['birth_date']).dt.days // 365).astype(int)
    df = df.drop(columns=['birth_date'])
    return df

def feature_engineering(df):
    df = df.copy()

    def safe_div(n, d):
        return (n / d).replace([np.inf, -np.inf], 0).fillna(0)

    df["last_session_pages_to_avg90"] = safe_div(df["last_session_pages_viewed"], df["avg_pages_90d"])
    df["sessions_90d_to_180"] = safe_div(df["sessions_90d"], df["total_180days_sessions"])
    df["avg_pages_90d_to_180"] = safe_div(df["avg_pages_90d"], df["avg_pages_viewed_180"])
    df["mobile_share"] = safe_div(df["mobile_sessions_count_180"], df["desktop_sessions_count_180"] + df["mobile_sessions_count_180"])
    df["last_kept_items_ratio"] = safe_div(df["last_succ_kept_order_items"], df["last_succ_order_items"])
    df["last_kept_value_ratio"] = safe_div(df["last_succ_kept_order_total"], df["last_succ_order_total"])
    df["last3_kept_items_ratio"] = safe_div(df["last3_kept_items"], df["last3_kept_items"] + df["last3_cancels_returns_items"])
    df["last3_kept_value_ratio"] = safe_div(df["last3_kept_total"], df["last3_kept_total"] + df["last3_return_cancel_order_total"])
    df["last3_succ_kept_value_to_avg_ratio"] = safe_div(df["last3_succ_orders_kept_total"], 3 * df["avg_order_value"])
    df["last_succ_kept_value_to_avg_ratio"] = safe_div(df["last_succ_kept_order_total"], df["avg_order_value"])
    df["avg_items_per_order_recent_ratio"] = safe_div(df["avg_items_per_order_90d"], df["avg_items_per_order"])
    df["avg_order_value_recent_ratio"] = safe_div(df["avg_order_value_90d"], df["avg_order_value"])
    df["succ_items_recent_ratio"] = safe_div(df["total_succ_items_per_customer_90d"], df["total_succ_items_per_customer"])
    df["sessions_per_success_order_90d"] = safe_div(df["sessions_90d"], df["succ_orders_count_90d"])
    df["min_order_value_delta"] = df["min_order_value_90d"] - df["min_order_value"]
    df["succ_orders_per_account_age"] = safe_div(df["succ_orders_count"], df["account_age_days"])

    return df
def prepare_A_inference(df, drop_feat=drop_A):

    df_A = df.drop(columns=drop_feat, errors="ignore")

    return df_A


def prepare_B_inference(df, drop_feat=drop_B):

    df_B = df.drop(columns=drop_feat, errors="ignore")

    return df_B

def predict_A(df, model_A):
    df_A = prepare_A_inference(df)
    p_not_active = model_A.predict_proba(df_A)[:, 1]
    return p_not_active

def predict_B(df, model_B):
    df_B = prepare_B_inference(df)
    X = df_B.drop(columns =["succ_orders_count_90d", "avg_order_value_90d"])
    p_churn = model_B.predict_proba(X)[:, 1]
    return p_churn

def prediction_pipeline(df, model_A, model_B, norm_params, churn_coef=0.6, ltv_coef=0.4, FEATURES=FEATURES):

    ltv_min = norm_params["ltv_min"]
    ltv_q25 = norm_params["ltv_q25"]
    ltv_q99 = norm_params["ltv_q99"]
    p_churn_cap = norm_params["p_churn_cap"]
    birth_mode = norm_params["birth_mode"]


    df_sel = select_features(df, FEATURES)
    ids = df['customer_id']
    df_clean = basic_cleaning(df_sel, birth_mode)
    df_fin = feature_engineering(df_clean)

    df_fin["ltv_score"] = (
        (df_fin["succ_orders_count"] * df_fin["avg_order_value"]) +
        (df_fin["succ_orders_count_90d"] * df_fin["avg_order_value_90d"])
    )

    df_fin["ltv_norm"] = df_fin["ltv_score"].apply(
        lambda x: norm_ltv(x, ltv_min, ltv_q99)
    )

    service_cols = ["ltv_norm", "ltv_score"]

    out = pd.DataFrame(ids)
    out["segment"] = "ACTIVE"
    out["offer_score"] = 0.0
    out["churn_prob"] = 0.0


    p_A_all = predict_A(df_fin.drop(columns=service_cols), model_A)

    out["active_prob"] = 1-p_A_all

    df_fin["p_A"] = p_A_all


    mask_low_risk = (df_fin["p_A"] >= 0.35) & (df_fin["p_A"] < 0.55) & (df_fin["ltv_score"] < ltv_q25)
    mask_non_active = ((df_fin["p_A"] >= 0.35) & ~mask_low_risk)|(df_fin["p_A"] >= 0.6)


    mask_B_input = mask_non_active | mask_low_risk
    df_B_input = df_fin.loc[mask_B_input]


    p_B = predict_B(df_B_input.drop(columns=service_cols + ['p_A']), model_B)
    p_B_clip = p_churn_clip(p_B, p_churn_cap)

    offer_score_vals = [
        offer_score(pb, ltv, churn_coef, ltv_coef)
        for pb, ltv in zip(p_B_clip, df_B_input["ltv_norm"])
        ]

    out.loc[mask_low_risk.values, "segment"] = "LOW-RISK AND LOW-VALUE"
    out.loc[mask_non_active.values, "segment"] = "NON-ACTIVE"
    out.loc[mask_B_input.values, "offer_score"] = offer_score_vals
    out.loc[mask_B_input.values, "churn_prob"] = p_B


    return out

def load_sql_query(filename="feature_query.sql"):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

FEATURE_QUERY = load_sql_query()


def build_feature_matrix(customers_df, orders_df, order_items_df, sessions_df, products_df):

    conn = sqlite3.connect(":memory:")

    customers_df.to_sql("customers", conn, index=False, if_exists="replace")
    orders_df.to_sql("orders", conn, index=False, if_exists="replace")
    order_items_df.to_sql("order_items", conn, index=False, if_exists="replace")
    sessions_df.to_sql("sessions", conn, index=False, if_exists="replace")
    products_df.to_sql("products", conn, index=False, if_exists="replace")

    feature_matrix = pd.read_sql_query(FEATURE_QUERY, conn)

    conn.close()
    return feature_matrix




