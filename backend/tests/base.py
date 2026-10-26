"""Shared test setup.

By default every test gets a brand-new temporary SQLite database.
To run the same tests against PostgreSQL, set TEST_DATABASE_URL to an EMPTY
test database (it is wiped before every test!), for example:

    TEST_DATABASE_URL=postgresql://postgres@localhost/furniture_test python -m unittest
"""

import os
import tempfile
import unittest

from app import create_app
from app.db import Database

from .fakes import FakeGateway

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _reset_postgres(url):
    db = Database(url)
    try:
        db.run_script("SET client_min_messages TO WARNING; DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        db.commit()
    finally:
        db.close()


class ApiTestCase(unittest.TestCase):
    """Each test gets a fresh app, a fresh database and a fake payment gateway."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        if TEST_DATABASE_URL:
            _reset_postgres(TEST_DATABASE_URL)
            database = TEST_DATABASE_URL
        else:
            database = os.path.join(self.tmp.name, "test.db")
        self.gateway = FakeGateway()
        self.app = create_app({"DATABASE": database, "SECRET_KEY": "test-secret-key-that-is-long-enough-123",
                               "ALLOWED_ORIGINS": "http://localhost:5173",
                               "PAYMENT_GATEWAY": self.gateway})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    # ---------- helpers ----------

    def search(self, **params):
        response = self.client.get("/api/products", query_string=params)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def signup(self, email="asha@example.com", password="correct-horse", name="Asha"):
        response = self.client.post("/api/auth/signup",
                                    json={"name": name, "email": email, "password": password})
        self.assertEqual(response.status_code, 201, response.json)
        return response.json["token"]

    @staticmethod
    def auth(token):
        return {"Authorization": f"Bearer {token}"}
