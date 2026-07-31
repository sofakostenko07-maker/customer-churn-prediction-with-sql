from pathlib import Path

RANDOM_SEED = 42

START_DATE = "2021-01-01"
END_DATE = "2026-07-01"

N_CUSTOMERS = 100_000
N_PRODUCTS = 20_000

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

CITIES = ["Warsaw", "Wroclaw", "Krakow", "Poznan", "Lodz", "Gdansk"]

CATEGORIES = {
    "Electronics": (50, 2500),
    "Books": (8, 60),
    "Home": (15, 600),
    "Fashion": (15, 400),
    "Sports": (10, 900),
    "Beauty": (5, 250),
    "Pets": (5, 300),
    "Food": (2, 100),
    "Toys": (5, 350),
    "Automotive": (20, 1500)
}

BRANDS = [
    "Alpha", "Nova", "Prime", "Vision", "Elite",
    "Eco", "Ultra", "Smart", "Pro", "Next"
]
