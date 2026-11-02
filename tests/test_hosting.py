"""Transport tests do not start lifespan or need a database; CI also tests real startup."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app, public_origin
from backend import db


class HostingOriginTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"PUBLIC_ORIGIN":"", "RENDER_EXTERNAL_URL":""})
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def write(self, origin, **headers):
        # A permitted origin reaches the normal 405 response; no auth/write is faked.
        return self.client.post("/healthz", headers={"Origin":origin, **headers}).status_code

    def test_local_origin_and_spoofed_forwarding_headers(self):
        self.assertEqual(self.write("http://testserver"), 405)
        self.assertEqual(self.write("https://foreign.example"), 403)
        self.assertEqual(self.write("https://testserver", **{"X-Forwarded-Proto":"https"}), 403)

    def test_https_render_origin_over_internal_http(self):
        os.environ["RENDER_EXTERNAL_URL"] = "https://wecode-demo.onrender.com"
        self.assertEqual(self.write("https://wecode-demo.onrender.com"), 405)
        self.assertEqual(self.write("https://foreign.example"), 403)
        self.assertEqual(self.write("http://testserver"), 403)

    def test_explicit_custom_origin_takes_priority(self):
        os.environ.update(PUBLIC_ORIGIN="https://wecode.example/", RENDER_EXTERNAL_URL="https://wecode-demo.onrender.com")
        self.assertEqual(self.write("https://wecode.example"), 405)
        self.assertEqual(self.write("https://wecode-demo.onrender.com"), 403)

    def test_invalid_public_origin_fails_closed(self):
        for value in ["http://wecode.example", "https://user:secret@example.com", "https://example.com/path",
                      "https://example.com?query=1", "https://example.com#fragment", "https://bad host", "*"]:
            with self.subTest(value=value), patch.dict(os.environ, PUBLIC_ORIGIN=value):
                with self.assertRaises(ValueError):
                    public_origin()


class DatabaseStartupTests(unittest.TestCase):
    def test_transient_connection_error_is_retried(self):
        import psycopg
        with patch.object(db, "migrate", side_effect=[psycopg.OperationalError("not ready"), None]) as migrate, patch.object(db.time, "sleep") as pause:
            db.migrate_with_retry(attempts=2)
            self.assertEqual(migrate.call_count, 2)
            pause.assert_called_once_with(2)

    def test_retries_are_bounded(self):
        import psycopg
        with patch.object(db, "migrate", side_effect=psycopg.OperationalError("unavailable")) as migrate, patch.object(db.time, "sleep"):
            with self.assertRaises(psycopg.OperationalError):
                db.migrate_with_retry(attempts=2)
            self.assertEqual(migrate.call_count, 2)

    def test_migration_integrity_errors_are_not_retried(self):
        with patch.object(db, "migrate", side_effect=RuntimeError("Applied migration changed")) as migrate, patch.object(db.time, "sleep") as pause:
            with self.assertRaises(RuntimeError):
                db.migrate_with_retry()
            self.assertEqual(migrate.call_count, 1)
            pause.assert_not_called()
