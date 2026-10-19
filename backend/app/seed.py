"""Generates a reproducible catalogue of sample furniture products.

The data is synthetic (made up by this script), not real Wayfair or store data.
A fixed random seed means everyone who runs the project gets the same catalogue.
"""

import random

# category -> (singular name, min price, max price) in INR
CATEGORIES = {
    "Sofas": ("Sofa", 18000, 95000),
    "Beds": ("Bed", 15000, 80000),
    "Dining Tables": ("Dining Table", 12000, 70000),
    "Chairs": ("Chair", 2500, 22000),
    "Wardrobes": ("Wardrobe", 14000, 65000),
    "Bookshelves": ("Bookshelf", 4000, 25000),
    "Coffee Tables": ("Coffee Table", 3500, 28000),
    "Desks": ("Desk", 5000, 35000),
    "Lamps": ("Lamp", 1200, 12000),
    "Rugs": ("Rug", 1500, 30000),
}

STYLES = ["Modern", "Scandinavian", "Industrial", "Mid-Century", "Traditional", "Boho"]
MATERIALS = ["Sheesham Wood", "Oak", "Engineered Wood", "Metal", "Rattan", "Velvet", "Linen", "Marble"]
COLORS = ["Walnut", "Natural", "Black", "White", "Grey", "Teal", "Beige", "Mustard"]

STYLE_NOTES = {
    "Modern": "clean lines and a minimal profile",
    "Scandinavian": "light tones and a simple, functional shape",
    "Industrial": "an exposed-frame look with a sturdy build",
    "Mid-Century": "tapered legs and a retro silhouette",
    "Traditional": "classic detailing and a warm finish",
    "Boho": "relaxed textures and an eclectic feel",
}


def generate_products(count=200, seed=42):
    """Return a list of product dicts, the same list every time for a given seed."""
    rng = random.Random(seed)
    products = []
    categories = list(CATEGORIES)

    for i in range(count):
        category = categories[i % len(categories)]  # spread products evenly across categories
        singular, low, high = CATEGORIES[category]
        style = rng.choice(STYLES)
        material = rng.choice(MATERIALS)
        color = rng.choice(COLORS)
        price = round(rng.randint(low, high), -2)  # round to the nearest 100

        products.append({
            "name": f"{style} {color} {material} {singular}",
            "category": category,
            "style": style,
            "material": material,
            "color": color,
            "price": price,
            "rating": round(rng.uniform(3.0, 5.0), 1),
            "review_count": rng.randint(0, 850),
            "description": (
                f"{_article(style)} {style.lower()} {singular.lower()} in {color.lower()} {material.lower()}, "
                f"with {STYLE_NOTES[style]}."
            ),
        })
    return products


def _article(word):
    """'An' before a vowel sound ("An industrial ..."), otherwise 'A'."""
    return "An" if word[0].lower() in "aeiou" else "A"
