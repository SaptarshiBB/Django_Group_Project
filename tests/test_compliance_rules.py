"""
Tests for Compliance Rules Engine and Statutory Evaluator Functions.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.compliance.management.commands.seed_rules import Command as SeedRulesCommand
from apps.compliance.models import Rule, RuleResult
from apps.scans.models import ExtractedField, Scan
from services.rules import (
    ComplianceEngine,
    evaluate_consumer_care,
    evaluate_country_of_origin,
    evaluate_generic_name,
    evaluate_mfg_date,
    evaluate_mfr_address,
    evaluate_mrp_declaration,
    evaluate_mrp_taxes,
    evaluate_net_qty_prohibited_terms,
    evaluate_net_quantity,
    evaluate_numeral_height,
)

User = get_user_model()


class ComplianceRulesEvaluatorTestCase(TestCase):
    def setUp(self):
        SeedRulesCommand().handle()
        self.user = User.objects.create_user(username="test_officer", password="TestPassword123!")

    def test_rule_mfr_address_evaluator(self):
        # 1. Missing
        status, msg, _ = evaluate_mfr_address({}, "", "general")
        self.assertEqual(status, "FAIL")

        # 2. Incomplete (single word, no postal details)
        status, msg, _ = evaluate_mfr_address({"manufacturer_details": "Acme"}, "", "general")
        self.assertEqual(status, "NEEDS_REVIEW")

        # 3. Full address
        status, msg, _ = evaluate_mfr_address(
            {"manufacturer_details": "Acme Agro Foods Pvt. Ltd., Industrial Area, Pune 411001"}, "", "general"
        )
        self.assertEqual(status, "PASS")

    def test_rule_generic_name_evaluator(self):
        status, _, _ = evaluate_generic_name({}, "", "food")
        self.assertEqual(status, "FAIL")

        status, _, _ = evaluate_generic_name({"generic_name": "Sunflower Edible Oil"}, "", "food")
        self.assertEqual(status, "PASS")

    def test_rule_net_quantity_metric_units(self):
        # Valid standard SI metric units
        for valid_qty in ["500 g", "1 kg", "250 ml", "1 L", "10 N"]:
            status, _, _ = evaluate_net_quantity({"net_quantity": valid_qty}, "", "general")
            self.assertEqual(status, "PASS", f"Failed for {valid_qty}")

        # Missing
        status, _, _ = evaluate_net_quantity({}, "", "general")
        self.assertEqual(status, "FAIL")

        # Non-standard unit
        status, _, _ = evaluate_net_quantity({"net_quantity": "500 lbs"}, "", "general")
        self.assertEqual(status, "WARNING")

    def test_rule_net_quantity_prohibited_terms(self):
        # Violations (approx, about, when packed)
        status, _, _ = evaluate_net_qty_prohibited_terms({"net_quantity": "Approx 500 g"}, "", "general")
        self.assertEqual(status, "FAIL")

        status, _, _ = evaluate_net_qty_prohibited_terms({"net_quantity": "500 g"}, "Net Wt: When packed 500g", "general")
        self.assertEqual(status, "FAIL")

        # Clean
        status, _, _ = evaluate_net_qty_prohibited_terms({"net_quantity": "500 g"}, "Net Wt: 500 g", "general")
        self.assertEqual(status, "PASS")

    def test_rule_mfg_date_evaluator(self):
        status, _, _ = evaluate_mfg_date({}, "", "general")
        self.assertEqual(status, "FAIL")

        status, _, _ = evaluate_mfg_date({"mfg_date": "10/2026"}, "", "general")
        self.assertEqual(status, "PASS")

    def test_rule_mrp_and_inclusive_taxes(self):
        # MRP missing
        status, _, _ = evaluate_mrp_declaration({}, "", "general")
        self.assertEqual(status, "FAIL")

        # MRP present
        status, _, _ = evaluate_mrp_declaration({"mrp": "₹ 199.00"}, "", "general")
        self.assertEqual(status, "PASS")

        # Taxes without statement
        status, _, _ = evaluate_mrp_taxes({"mrp": "₹ 199.00"}, "MRP Rs. 199.00", "general")
        self.assertEqual(status, "WARNING")

        # Taxes with statement
        status, _, _ = evaluate_mrp_taxes(
            {"mrp": "₹ 199.00 (Incl. of all taxes)"}, "MRP Rs. 199.00 Incl. of all taxes", "general"
        )
        self.assertEqual(status, "PASS")

    def test_rule_consumer_care_evaluator(self):
        # Missing
        status, _, _ = evaluate_consumer_care({}, "", "general")
        self.assertEqual(status, "FAIL")

        # Partial (Tel only)
        status, _, _ = evaluate_consumer_care({"consumer_care": "Tel: 1800-111-222"}, "", "general")
        self.assertEqual(status, "WARNING")

        # Complete (Tel & Email)
        status, _, _ = evaluate_consumer_care(
            {"consumer_care": "Tel: 1800-111-222 | Email: support@example.com"}, "", "general"
        )
        self.assertEqual(status, "PASS")

    def test_rule_numeral_height_evaluator(self):
        status, msg, _ = evaluate_numeral_height({"net_quantity": "500 g"}, "", "general")
        self.assertEqual(status, "NEEDS_REVIEW")
        self.assertIn("Table 1", msg)

    def test_compliance_engine_end_to_end(self):
        scan = Scan.objects.create(
            user=self.user,
            product_name="Test Basmati Rice",
            category="food",
        )
        fields = {
            "generic_name": "Basmati Rice",
            "net_quantity": "5 kg",
            "mrp": "₹ 400.00 (Incl. of all taxes)",
            "mfg_date": "08/2026",
            "manufacturer_details": "Agro Millers Pvt Ltd, Industrial Area, Sector 5, Karnal 132001",
            "consumer_care": "Tel: 1800-999-000 | Email: care@agromill.in",
            "country_of_origin": "India",
            "unit_sale_price": "₹ 80.00 per kg",
        }
        for k, v in fields.items():
            ExtractedField.objects.create(scan=scan, key=k, value=v, confidence=90.0)

        engine = ComplianceEngine(scan)
        res = engine.evaluate()

        scan.refresh_from_db()
        self.assertIn(scan.status, ["COMPLIANT", "NEEDS_REVIEW"])
        self.assertGreater(scan.score, 75.0)
        self.assertEqual(scan.rule_results.count(), Rule.objects.filter(is_active=True).count())
