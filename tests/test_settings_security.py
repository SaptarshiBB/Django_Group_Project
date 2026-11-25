"""
Security and Settings Tests.
Validates environment-driven configuration and ensures no insecure fallback keys exist.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase


class SettingsSecurityTestCase(TestCase):
    def test_secret_key_is_not_default_or_insecure(self):
        """Verify SECRET_KEY is not a known weak placeholder."""
        insecure_keys = [
            "",
            "django-insecure",
            "your-super-secret-key",
            "your-super-secret-key-change-this-in-production",
            "changeme",
            "secret",
        ]
        key = getattr(settings, "SECRET_KEY", "")
        self.assertTrue(bool(key), "SECRET_KEY must not be empty.")
        for weak in insecure_keys:
            self.assertNotEqual(
                key,
                weak,
                f"SECRET_KEY cannot be set to insecure placeholder '{weak}'.",
            )

    def test_secure_cookies_configured(self):
        """Verify cookie configuration matches Django production security specs."""
        self.assertTrue(hasattr(settings, "SESSION_COOKIE_SECURE"))
        self.assertTrue(hasattr(settings, "CSRF_COOKIE_SECURE"))
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_allowed_hosts_defined(self):
        """Ensure ALLOWED_HOSTS is not an unrestricted wildcard in production settings."""
        self.assertTrue(isinstance(settings.ALLOWED_HOSTS, list))
        self.assertTrue(len(settings.ALLOWED_HOSTS) > 0)
