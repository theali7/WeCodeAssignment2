import os
import time
import unittest
from uuid import uuid4

os.environ.setdefault("AUTH_SECRET", "unit-test-secret-" * 4)

from backend.security import access_token, verify_access, password_hash, password_matches, token_hash


class SecurityTests(unittest.TestCase):
    def test_password_hash_is_salted_and_checked(self):
        encoded = password_hash("long-password")
        self.assertNotEqual(encoded, password_hash("long-password"))
        self.assertTrue(password_matches("long-password", encoded))
        self.assertFalse(password_matches("wrong-password", encoded))
        self.assertFalse(password_matches("long-password", "bad-format"))

    def test_token_signature_expiry_and_identity(self):
        token = access_token("user", "session", "secret", now=100)
        self.assertEqual(verify_access(token, "secret", now=101)["sub"], "user")
        for value, key, now in [(token, "wrong", 101), (token, "secret", 3700), (token + "x", "secret", 101), ("broken", "secret", 101)]:
            with self.assertRaises(ValueError):
                verify_access(value, key, now=now)

    def test_refresh_tokens_are_not_stored_as_plaintext(self):
        self.assertNotEqual(token_hash("refresh"), "refresh")
        self.assertEqual(token_hash("refresh"), token_hash("refresh"))


@unittest.skipUnless(os.environ.get("WECODE_TEST_DATABASE_URL"), "Requires isolated PostgreSQL test database")
class DatabaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.app import app
        from backend import db
        os.environ["DATABASE_URL"] = os.environ["WECODE_TEST_DATABASE_URL"]
        cls.db = db
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def setUp(self):
        self.users = []
        self.first = self.signup()
        self.second = self.signup()
        self.headers = {"Authorization": "Bearer " + self.first["access_token"]}

    def tearDown(self):
        with self.db.connect() as connection:
            for uid in self.users:
                connection.execute("DELETE FROM wecode_private.users WHERE id=%s", (uid,))

    def signup(self):
        body = {"email": f"test-{uuid4()}@example.test", "password": "strong-test-password", "data": {"display_name": "Test"}}
        response = self.client.post("/api/auth/v1/signup", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.users.append(result["user"]["id"])
        return result

    def test_health_and_idempotent_migrations(self):
        self.db.migrate()
        self.assertEqual(self.client.get("/api/health").json()["database"], "postgresql")

    def test_login_errors_and_success(self):
        url = "/api/auth/v1/token?grant_type=password"
        email = self.first["user"]["email"]
        self.assertEqual(self.client.post(url, json={"email": email, "password": "wrong"}).status_code, 400)
        response = self.client.post(url, json={"email": email, "password": "strong-test-password"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], self.first["user"]["id"])

    def test_authentication_and_cross_user_read(self):
        self.assertEqual(self.client.get("/api/rest/v1/profiles").status_code, 401)
        response = self.client.get("/api/rest/v1/profiles", headers=self.headers)
        self.assertEqual([r["id"] for r in response.json()], [self.first["user"]["id"]])
        response = self.client.get("/api/rest/v1/profiles?id=eq." + self.second["user"]["id"], headers=self.headers)
        self.assertEqual(response.json(), [])

    def test_profile_validation_and_cross_user_write(self):
        url = "/api/rest/v1/profiles"
        own = self.first["user"]["id"]
        self.assertEqual(self.client.post(url, headers=self.headers, json={"id": self.second["user"]["id"], "level": 2}).status_code, 403)
        self.assertEqual(self.client.post(url, headers=self.headers, json={"id": own, "level": 9}).status_code, 422)
        self.assertEqual(self.client.post(url, headers=self.headers, json={"id": own, "display_name": "Updated", "path_id": "java", "level": 1}).status_code, 201)
        response = self.client.get(url + "?select=display_name,path_id,level", headers=self.headers)
        self.assertEqual(response.json(), [{"display_name": "Updated", "path_id": "java", "level": 1}])

    def test_learning_way_upsert_is_idempotent_and_atomic(self):
        url = "/api/rest/v1/learning_way_progress?on_conflict=user_id,item_id"
        row = {"user_id": self.first["user"]["id"], "item_id": "notes:python-variables"}
        for _ in range(2):
            self.assertEqual(self.client.post(url, headers=self.headers, json=[row]).status_code, 201)
        self.assertEqual(len(self.client.get(url.split("?")[0], headers=self.headers).json()), 1)
        invalid = {"user_id": self.second["user"]["id"], "item_id": "stolen"}
        another = {**row, "item_id": "task:not-committed"}
        self.assertEqual(self.client.post(url, headers=self.headers, json=[another, invalid]).status_code, 403)
        self.assertEqual(len(self.client.get(url.split("?")[0], headers=self.headers).json()), 1)

    def test_refresh_rotation_and_logout_revocation(self):
        url = "/api/auth/v1/token?grant_type=refresh_token"
        response = self.client.post(url, json={"refresh_token": self.first["refresh_token"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(url, json={"refresh_token": self.first["refresh_token"]}).status_code, 400)
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        self.assertEqual(self.client.get("/api/auth/v1/user", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/v1/logout", headers=headers).status_code, 204)
        self.assertEqual(self.client.get("/api/auth/v1/user", headers=headers).status_code, 401)
        self.assertEqual(self.client.post(url, json={"refresh_token": response.json()["refresh_token"]}).status_code, 400)

    def test_reject_unknown_resources_and_columns(self):
        self.assertEqual(self.client.get("/api/rest/v1/users", headers=self.headers).status_code, 404)
        self.assertEqual(self.client.get("/api/rest/v1/profiles?select=password_hash", headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post("/api/rest/v1/lessons", headers=self.headers, json={"published": True}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
