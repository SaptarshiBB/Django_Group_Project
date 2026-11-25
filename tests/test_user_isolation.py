"""
Tests for User Isolation & Access Control.
Ensures regular officers only see their own scans while administrators have oversight.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from apps.compliance.management.commands.seed_rules import Command as SeedRulesCommand
from apps.scans.models import Scan

User = get_user_model()


class UserIsolationTestCase(TestCase):
    def setUp(self):
        SeedRulesCommand().handle()
        self.user_a = User.objects.create_user(username="officer_a", password="Password123!")
        self.user_b = User.objects.create_user(username="officer_b", password="Password123!")
        self.admin_user = User.objects.create_superuser(username="admin_user", password="AdminPassword123!")

        self.scan_a = Scan.objects.create(user=self.user_a, product_name="Commodity Alpha")
        self.scan_b = Scan.objects.create(user=self.user_b, product_name="Commodity Beta")

        self.client_a = Client()
        self.client_a.login(username="officer_a", password="Password123!")

        self.client_b = Client()
        self.client_b.login(username="officer_b", password="Password123!")

        self.client_admin = Client()
        self.client_admin.login(username="admin_user", password="AdminPassword123!")

    def test_user_can_view_own_scan_detail(self):
        resp = self.client_a.get(reverse("scans:detail", kwargs={"pk": self.scan_a.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_view_other_user_scan_detail(self):
        resp = self.client_a.get(reverse("scans:detail", kwargs={"pk": self.scan_b.pk}))
        self.assertEqual(resp.status_code, 404)

    def test_user_cannot_download_other_user_pdf(self):
        resp = self.client_a.get(reverse("reports:download_pdf", kwargs={"pk": self.scan_b.pk}))
        self.assertEqual(resp.status_code, 404)

    def test_user_cannot_delete_other_user_scan(self):
        resp = self.client_a.post(reverse("scans:delete", kwargs={"pk": self.scan_b.pk}))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Scan.objects.filter(pk=self.scan_b.pk).exists())

    def test_history_list_only_shows_own_scans(self):
        resp = self.client_a.get(reverse("scans:list"))
        self.assertEqual(resp.status_code, 200)
        scans_in_context = resp.context["scans"]
        self.assertIn(self.scan_a, scans_in_context)
        self.assertNotIn(self.scan_b, scans_in_context)

    def test_admin_can_view_all_scans(self):
        resp_a = self.client_admin.get(reverse("scans:detail", kwargs={"pk": self.scan_a.pk}))
        resp_b = self.client_admin.get(reverse("scans:detail", kwargs={"pk": self.scan_b.pk}))
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_b.status_code, 200)
