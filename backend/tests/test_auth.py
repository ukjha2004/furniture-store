"""Sign-up, login and token tests."""

from datetime import datetime, timedelta, timezone

import jwt

from .base import ApiTestCase


class SignupTests(ApiTestCase):
    def test_signup_returns_token_and_user_without_password(self):
        response = self.client.post("/api/auth/signup", json={
            "name": "  Asha  ", "email": "Asha@Example.com ", "password": "correct-horse"})
        self.assertEqual(response.status_code, 201)
        user = response.json["user"]
        self.assertEqual(user["name"], "Asha")
        self.assertEqual(user["email"], "asha@example.com")   # trimmed and lowercased
        self.assertNotIn("password", str(response.json).lower().replace("password_", ""))
        self.assertTrue(response.json["token"])

    def test_password_is_stored_hashed(self):
        self.signup(password="correct-horse")
        from app.db import Database
        db = Database(self.app.config["DATABASE"])
        stored = db.scalar("SELECT password_hash FROM users")
        db.close()
        self.assertNotIn("correct-horse", stored)
        self.assertTrue(stored.startswith(("scrypt:", "pbkdf2:")))

    def test_duplicate_email_is_rejected(self):
        self.signup(email="asha@example.com")
        response = self.client.post("/api/auth/signup", json={
            "name": "Other", "email": "ASHA@example.com", "password": "another-pass"})
        self.assertEqual(response.status_code, 409)

    def test_signup_validation(self):
        bad = [
            {"name": "A", "email": "a@example.com", "password": "longenough"},
            {"name": "Asha", "email": "not-an-email", "password": "longenough"},
            {"name": "Asha", "email": "a@example.com", "password": "short"},
            {"name": "Asha", "email": "a@example.com"},
            {},
        ]
        for body in bad:
            response = self.client.post("/api/auth/signup", json=body)
            self.assertEqual(response.status_code, 400, body)
            self.assertIn("error", response.json)


class LoginTests(ApiTestCase):
    def test_login_with_correct_password(self):
        self.signup(email="asha@example.com", password="correct-horse")
        response = self.client.post("/api/auth/login",
                                    json={"email": " ASHA@example.com", "password": "correct-horse"})
        self.assertEqual(response.status_code, 200)
        me = self.client.get("/api/auth/me", headers=self.auth(response.json["token"]))
        self.assertEqual(me.json["email"], "asha@example.com")

    def test_wrong_password_and_unknown_email_give_same_error(self):
        self.signup(email="asha@example.com", password="correct-horse")
        wrong_pw = self.client.post("/api/auth/login",
                                    json={"email": "asha@example.com", "password": "wrong-password"})
        no_user = self.client.post("/api/auth/login",
                                   json={"email": "nobody@example.com", "password": "whatever-123"})
        self.assertEqual(wrong_pw.status_code, 401)
        self.assertEqual(no_user.status_code, 401)
        self.assertEqual(wrong_pw.json, no_user.json)


class TokenTests(ApiTestCase):
    def test_me_requires_a_token(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth("garbage")).status_code, 401)

    def test_forged_token_is_rejected(self):
        self.signup()
        forged = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                            "attacker-guessed-key-that-is-also-long-00", algorithm="HS256")
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(forged)).status_code, 401)

    def test_expired_token_is_rejected(self):
        self.signup()
        expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
                             "test-secret-key-that-is-long-enough-123", algorithm="HS256")
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(expired)).status_code, 401)

    def test_unsigned_token_is_rejected(self):
        self.signup()
        unsigned = jwt.encode({"sub": "1"}, None, algorithm="none")
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(unsigned)).status_code, 401)

    def test_cors_allows_authorization_header(self):
        response = self.client.options("/api/auth/me", headers={"Origin": "http://localhost:5173"})
        self.assertIn("Authorization", response.headers.get("Access-Control-Allow-Headers", ""))
