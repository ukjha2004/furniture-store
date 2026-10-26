"""API tests. Run from the backend folder with:  python -m unittest -v
(pytest also finds and runs these if you prefer:  pytest -v)
"""

import unittest

from app.models import Cart, CartItem, Product
from app.recommender import CategoryRecommender, Recommender, TfidfRecommender

from .base import ApiTestCase


class ProductSearchTests(ApiTestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/api/health").json, {"status": "ok"})

    def test_lists_all_products_with_pagination_info(self):
        data = self.search()
        self.assertEqual(data["total"], 200)
        self.assertEqual(len(data["items"]), 12)
        self.assertEqual(data["total_pages"], 17)

    def test_every_search_word_must_match(self):
        data = self.search(q="oak sofa", page_size=48)
        self.assertGreater(data["total"], 0)
        for product in data["items"]:
            text = f"{product['name']} {product['description']}".lower()
            self.assertIn("oak", text)
            self.assertIn("sofa", text)

    def test_search_is_case_insensitive(self):
        self.assertEqual(self.search(q="RATTAN")["total"], self.search(q="rattan")["total"])

    def test_category_and_price_filters(self):
        data = self.search(category="Chairs", min_price=5000, max_price=15000, page_size=48)
        self.assertGreater(data["total"], 0)
        for product in data["items"]:
            self.assertEqual(product["category"], "Chairs")
            self.assertTrue(5000 <= product["price"] <= 15000)

    def test_sort_by_price(self):
        prices = [p["price"] for p in self.search(sort="price_asc", page_size=48)["items"]]
        self.assertEqual(prices, sorted(prices))
        prices = [p["price"] for p in self.search(sort="price_desc", page_size=48)["items"]]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_pages_do_not_overlap(self):
        first = {p["id"] for p in self.search(page=1)["items"]}
        second = {p["id"] for p in self.search(page=2)["items"]}
        self.assertFalse(first & second)

    def test_rejects_bad_parameters(self):
        for params in [{"sort": "DROP TABLE products"}, {"page": "0"}, {"page_size": "500"},
                       {"min_price": "abc"}, {"min_price": "9000", "max_price": "100"}]:
            response = self.client.get("/api/products", query_string=params)
            self.assertEqual(response.status_code, 400, params)
            self.assertIn("error", response.json)

    def test_sql_injection_in_search_text_is_harmless(self):
        data = self.search(q="'; DROP TABLE products; --")
        self.assertEqual(data["total"], 0)
        self.assertEqual(self.search()["total"], 200)  # table still exists

    def test_categories_are_grouped_with_counts(self):
        categories = self.client.get("/api/categories").json
        self.assertEqual(len(categories), 10)
        self.assertEqual(sum(c["product_count"] for c in categories), 200)
        for c in categories:
            self.assertLessEqual(c["min_price"], c["max_price"])

    def test_get_product_and_404(self):
        self.assertEqual(self.client.get("/api/products/1").json["id"], 1)
        self.assertEqual(self.client.get("/api/products/99999").status_code, 404)


class SimilarProductTests(ApiTestCase):
    def test_similar_excludes_itself_and_prefers_same_category(self):
        product = self.client.get("/api/products/1").json
        similar = self.client.get("/api/products/1/similar?k=4").json
        self.assertEqual(len(similar), 4)
        self.assertNotIn(1, [p["id"] for p in similar])
        self.assertTrue(all(p["category"] == product["category"] for p in similar))

    def test_similar_for_missing_product_is_404(self):
        self.assertEqual(self.client.get("/api/products/99999/similar").status_code, 404)


class CartTests(ApiTestCase):
    def new_cart(self):
        response = self.client.post("/api/carts")
        self.assertEqual(response.status_code, 201)
        return response.json["id"]

    def test_add_items_and_totals(self):
        cart_id = self.new_cart()
        price_1 = self.client.get("/api/products/1").json["price"]
        price_2 = self.client.get("/api/products/2").json["price"]

        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 1, "quantity": 2})
        cart = self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 2}).json

        self.assertEqual(cart["item_count"], 3)
        self.assertEqual(cart["subtotal"], 2 * price_1 + price_2)

    def test_adding_same_product_twice_increases_quantity(self):
        cart_id = self.new_cart()
        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 5})
        cart = self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 5}).json
        self.assertEqual(len(cart["items"]), 1)
        self.assertEqual(cart["items"][0]["quantity"], 2)

    def test_update_and_remove_item(self):
        cart_id = self.new_cart()
        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 3})
        cart = self.client.put(f"/api/carts/{cart_id}/items/3", json={"quantity": 4}).json
        self.assertEqual(cart["items"][0]["quantity"], 4)
        cart = self.client.delete(f"/api/carts/{cart_id}/items/3").json
        self.assertEqual(cart["items"], [])
        self.assertEqual(self.client.delete(f"/api/carts/{cart_id}/items/3").status_code, 404)

    def test_quantity_rules(self):
        cart_id = self.new_cart()
        for bad in [0, -1, 11, "2", 1.5, True]:
            response = self.client.post(f"/api/carts/{cart_id}/items",
                                        json={"product_id": 1, "quantity": bad})
            self.assertEqual(response.status_code, 400, bad)
        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 1, "quantity": 10})
        over = self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 1})
        self.assertEqual(over.status_code, 400)

    def test_unknown_cart_or_product(self):
        self.assertEqual(self.client.get("/api/carts/not-a-cart").status_code, 404)
        cart_id = self.new_cart()
        response = self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 99999})
        self.assertEqual(response.status_code, 404)


class CorsTests(ApiTestCase):
    def test_allowed_origin_gets_cors_header(self):
        response = self.client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")

    def test_other_origin_does_not(self):
        response = self.client.get("/api/health", headers={"Origin": "http://evil.example"})
        self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))


class UnitTests(unittest.TestCase):
    """Tests for the plain Python classes, no HTTP involved."""

    @staticmethod
    def make_product(pid, category="Sofas", price=1000, name="Test Sofa"):
        return Product(id=pid, name=name, category=category, style="Modern", material="Oak",
                       color="Black", price=price, rating=4.0, review_count=10,
                       description="A test product.")

    def test_cart_totals(self):
        cart = Cart(id="c1", items=[CartItem(self.make_product(1, price=500), 3),
                                    CartItem(self.make_product(2, price=200), 1)])
        self.assertEqual(cart.subtotal, 1700)
        self.assertEqual(cart.item_count, 4)

    def test_recommenders_share_one_interface(self):
        products = [self.make_product(1), self.make_product(2),
                    self.make_product(3, category="Lamps", name="Test Lamp")]
        for recommender in (CategoryRecommender(), TfidfRecommender()):
            self.assertIsInstance(recommender, Recommender)
            recommender.fit(products)
            self.assertEqual(recommender.similar(1, k=1), [2])
            self.assertEqual(recommender.similar(42), [])


if __name__ == "__main__":
    unittest.main()
