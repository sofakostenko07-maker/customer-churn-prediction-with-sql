import pandas as pd
from sqlalchemy import create_engine, text

USER = "..."
PASSWORD = "..."
HOST = "localhost"
DB = "churn_project"

engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DB}")

def load_csv(table_name, csv_path):
    print(f"Loading {csv_path} to table → {table_name} ...")

    df = pd.read_csv(csv_path)

    df.columns = [c.lower() for c in df.columns]

    try:
        df.to_sql(
            table_name,
            engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000
        )
        print(f"Successfully dumped to {table_name}")
    except Exception as e:
        print(f"Error at {table_name}: {e}")


def main():
    print("Uploading to MySQL...\n")

    load_csv("order_items", "data/raw/order_items.csv")
    load_csv("customers", "data/raw/customers.csv")
    load_csv("products", "data/raw/products.csv")
    load_csv("orders", "data/raw/orders.csv")
    load_csv("order_items", "data/raw/order_items.csv")
    load_csv("sessions", "data/raw/sessions.csv")

    print("\nALL DONE")

if __name__ == "__main__":
    main()
