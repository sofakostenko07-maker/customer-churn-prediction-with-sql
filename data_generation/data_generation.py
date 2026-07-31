import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
from config import *

fake = Faker()
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def generate_products():
    rows = []
    categories = list(CATEGORIES.keys())

    for product_id in range(1, N_PRODUCTS + 1):
        category = random.choice(categories)
        low, high = CATEGORIES[category]

        rows.append({
            "product_id": product_id,
            "category": category,
            "brand": random.choice(BRANDS),
            "base_price": round(random.uniform(low, high), 2)
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "products.csv", index=False)
    return df

def generate_customers():
    rows = []
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.strptime(END_DATE, "%Y-%m-%d")

    for customer_id in range(1, N_CUSTOMERS + 1):
        registration = random_date(start, end)
        age = random.randint(18, 75)
        birth = registration - timedelta(days=365 * age)

        rows.append({
            "customer_id": customer_id,
            "registration_date": registration.date(),
            "birth_date": birth.date(),
            "gender": random.choice(["Male", "Female"]),
            "city": random.choice(CITIES),
            "country": "Poland"
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "customers.csv", index=False)
    return df

def generate_orders(customers):
    rows = []
    order_id = 1
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d")

    for _, customer in customers.iterrows():
        cid = customer["customer_id"]
        registration = datetime.strptime(str(customer["registration_date"]), "%Y-%m-%d")


        base_orders_per_year = random.choice([2, 4, 6, 12])
        avg_interval = int(365 / base_orders_per_year)

        current = registration
        while current < end_date:
            interval = max(5, int(np.random.normal(avg_interval, avg_interval * 0.4)))
            current += timedelta(days=interval)
            if current > end_date:
                break

            status_choice = random.choices(
                ["Completed", "Cancelled", "Returned"],
                [0.8, 0.1, 0.1]
            )[0]

            if status_choice == "Completed":
                status_date = current
            elif status_choice == "Cancelled":
                status_date = current
            else:
                status_date = current + timedelta(days=random.randint(3, 30))

            rows.append({
                "order_id": order_id,
                "customer_id": cid,
                "order_date": current.date(),
                "status": status_choice,
                "status_date": status_date.date()
            })

            order_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "orders.csv", index=False)
    return df

def generate_order_items(orders, products):
    rows = []
    item_id = 1

    product_ids = products["product_id"].tolist()

    for _, order in orders.iterrows():
        oid = order["order_id"]
        n_items = random.randint(1, 5)

        for _ in range(n_items):
            pid = random.choice(product_ids)
            prod = products.loc[products["product_id"] == pid].iloc[0]
            quantity = random.randint(1, 3)

            price = prod["base_price"] * random.uniform(0.8, 1.2)

            returned = 0
            if order["status"] == "Returned":
                returned = int(random.random() < 0.5)

            rows.append({
                "order_item_id": item_id,
                "order_id": oid,
                "product_id": pid,
                "quantity": quantity,
                "price_at_purchase": round(price, 2),
                "returned": returned
            })

            item_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "order_items.csv", index=False)
    return df

def generate_sessions(customers):
    rows = []
    session_id = 1
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d")

    for _, customer in customers.iterrows():
        cid = customer["customer_id"]
        registration = datetime.strptime(str(customer["registration_date"]), "%Y-%m-%d")

        base_sessions_per_month = random.choice([1, 2, 4, 8])
        current = registration

        while current < end_date:
            days_step = max(1, int(np.random.exponential(30 / base_sessions_per_month)))
            current += timedelta(days=days_step)
            if current > end_date:
                break

            rows.append({
                "session_id": session_id,
                "customer_id": cid,
                "session_date": current.date(),
                "device": random.choice(["mobile", "desktop"]),
                "pages_viewed": random.randint(1, 30)
            })

            session_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "sessions.csv", index=False)
    return df
