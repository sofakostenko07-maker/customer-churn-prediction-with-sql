from data_generation import (
    generate_products,
    generate_customers,
    generate_orders,
    generate_order_items,
    generate_sessions,
)


def main():
    print("Generating products...")
    products = generate_products()

    print("Generating customers...")
    customers = generate_customers()

    print("Generating orders...")
    orders = generate_orders(customers)

    print("Generating order items...")
    order_items = generate_order_items(orders, products)

    print("Generating sessions...")
    sessions = generate_sessions(customers)




    print("Done.")
    print("Saved CSVs in data/:")
    print("- products.csv")
    print("- customers.csv")
    print("- orders.csv")
    print("- order_items.csv")
    print("- sessions.csv")


if __name__ == "__main__":
    main()
