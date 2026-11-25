"""
Tests for Statutory Field Extraction Service.
"""
from django.test import SimpleTestCase
from services.extractor import FieldExtractor


class FieldExtractorTestCase(SimpleTestCase):
    def setUp(self):
        self.sample_text = (
            "HERITAGE PREMIUM BASMATI RICE\n"
            "COMMODITY: TRADITIONAL BASMATI RICE\n"
            "NET QUANTITY: 5 kg\n"
            "MRP Rs. 650.00 (Incl. of all taxes)\n"
            "MFD: 10/2026\n"
            "MANUFACTURED & PACKED BY: Heritage Agro Mills Pvt. Ltd., Plot 45, Sector 12, Karnal, Haryana - 132001\n"
            "CUSTOMER CARE: Heritage Consumer Desk, Tel: 1800-200-4455, Email: care@heritageagro.in\n"
            "UNIT SALE PRICE: Rs. 130.00 per kg\n"
            "COUNTRY OF ORIGIN: INDIA\n"
            "BEST BEFORE: 24 MONTHS FROM MANUFACTURE"
        )
        self.extractor = FieldExtractor(self.sample_text)

    def test_extract_generic_name(self):
        val, conf = self.extractor.extract_generic_name()
        self.assertEqual(val.lower(), "traditional basmati rice")
        self.assertGreaterEqual(conf, 70.0)

    def test_extract_net_quantity(self):
        val, conf = self.extractor.extract_net_quantity()
        self.assertEqual(val.lower(), "5 kg")
        self.assertGreaterEqual(conf, 80.0)

    def test_extract_mrp_inclusive_taxes(self):
        val, conf = self.extractor.extract_mrp()
        self.assertIn("650.00", val)
        self.assertIn("Incl. of all taxes", val)

    def test_extract_mfg_date(self):
        val, conf = self.extractor.extract_mfg_date()
        self.assertEqual(val, "10/2026")

    def test_extract_manufacturer_details(self):
        val, conf = self.extractor.extract_manufacturer_details()
        self.assertIn("Heritage Agro Mills Pvt. Ltd.", val)
        self.assertIn("Karnal", val)

    def test_extract_consumer_care(self):
        val, conf = self.extractor.extract_consumer_care()
        self.assertIn("1800-200-4455", val)
        self.assertIn("care@heritageagro.in", val)

    def test_extract_country_of_origin(self):
        val, conf = self.extractor.extract_country_of_origin()
        self.assertEqual(val.upper(), "INDIA")

    def test_extract_unit_sale_price(self):
        val, conf = self.extractor.extract_unit_sale_price()
        self.assertIn("130.00", val)
        self.assertIn("kg", val.lower())

    def test_extract_best_before(self):
        val, conf = self.extractor.extract_best_before()
        self.assertIn("24 MONTHS", val)
