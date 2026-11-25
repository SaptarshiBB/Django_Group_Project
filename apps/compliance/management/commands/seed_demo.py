"""
Management command to seed administrative users and demonstration inspection scans.
Reads credentials strictly from django.conf.settings (which reads from .env).
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.compliance.management.commands.seed_rules import Command as SeedRulesCommand
from apps.compliance.models import Rule
from apps.scans.models import ExtractedField, Scan, ScanImage
from services.rules import ComplianceEngine

User = get_user_model()


class Command(BaseCommand):
    help = "Seed superuser and demo inspector user with realistic sample packaged commodity scans"

    def handle(self, *args, **options):
        # 1. Ensure rules are seeded first
        self.stdout.write("Ensuring compliance rules are populated...")
        SeedRulesCommand().handle()

        # 2. Superuser creation
        su_username = getattr(settings, "DJANGO_SUPERUSER_USERNAME", "admin")
        su_email = getattr(settings, "DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        su_password = getattr(settings, "DJANGO_SUPERUSER_PASSWORD", "")

        if su_username and su_password:
            admin_user, created = User.objects.get_or_create(
                username=su_username,
                defaults={"email": su_email, "is_staff": True, "is_superuser": True},
            )
            admin_user.set_password(su_password)
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} superuser '{su_username}'."))
        else:
            self.stdout.write(self.style.WARNING("DJANGO_SUPERUSER_PASSWORD is not set. Skipping superuser creation."))

        # 3. Demo Inspector user creation
        demo_password = getattr(settings, "DEMO_USER_PASSWORD", "")
        if not demo_password:
            demo_password = "DemoOfficerPassword2026!"

        demo_user, d_created = User.objects.get_or_create(
            username="demo_officer",
            defaults={"email": "officer@metrology.gov.local", "first_name": "Demo", "last_name": "Officer"},
        )
        demo_user.set_password(demo_password)
        demo_user.is_staff = False
        demo_user.save()
        action = "Created" if d_created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} demo user 'demo_officer'."))

        # 4. Seed realistic sample scans for demo_officer
        self.stdout.write("Creating demonstration packaged commodity scans...")

        # Sample 1: Fully Compliant Premium Basmati Rice Pack
        scan1, _ = Scan.objects.get_or_create(
            user=demo_user,
            product_name="Heritage Premium Aged Basmati Rice",
            defaults={
                "category": "food",
                "pre_packed_type": "Standard Retail Pouch",
                "notes": "Specimen packaging verified from authorized retail market inspection.",
            },
        )
        ScanImage.objects.get_or_create(
            scan=scan1,
            label_type="front",
            defaults={
                "ocr_text": (
                    "HERITAGE PREMIUM BASMATI RICE\n"
                    "COMMODITY: TRADITIONAL BASMATI RICE\n"
                    "NET QUANTITY: 5 kg\n"
                    "MRP Rs. 650.00 (Incl. of all taxes)\n"
                    "MFD: 10/2026  BATCH: BR-882\n"
                    "MANUFACTURED & PACKED BY: Heritage Agro Mills Pvt. Ltd., Plot 45, Sector 12, Karnal, Haryana - 132001\n"
                    "CUSTOMER CARE: Heritage Consumer Desk, Tel: 1800-200-4455, Email: care@heritageagro.in\n"
                    "UNIT SALE PRICE: Rs. 130.00 per kg\n"
                    "COUNTRY OF ORIGIN: INDIA\n"
                    "BEST BEFORE: 24 MONTHS FROM MANUFACTURE"
                ),
                "avg_confidence": 92.4,
            },
        )
        fields1 = {
            "generic_name": ("Traditional Basmati Rice", "Common / Generic Name of Commodity", 92.0),
            "net_quantity": ("5 kg", "Net Quantity", 95.0),
            "mrp": ("₹ 650.00 (Incl. of all taxes)", "Maximum Retail Price (MRP)", 94.0),
            "mfg_date": ("10/2026", "Month & Year of Manufacture", 91.0),
            "manufacturer_details": ("Heritage Agro Mills Pvt. Ltd., Plot 45, Sector 12, Karnal, Haryana - 132001", "Manufacturer Name & Address", 88.0),
            "consumer_care": ("Tel: 1800-200-4455 | Email: care@heritageagro.in", "Consumer Care Helpline & Email", 90.0),
            "country_of_origin": ("INDIA", "Country of Origin", 96.0),
            "unit_sale_price": ("₹ 130.00 per kg", "Unit Sale Price (USP)", 89.0),
            "best_before": ("24 Months From Manufacture", "Best Before", 87.0),
        }
        for k, (v, lbl, c) in fields1.items():
            ExtractedField.objects.update_or_create(
                scan=scan1, key=k, defaults={"value": v, "label": lbl, "confidence": c, "is_user_edited": False}
            )
        ComplianceEngine(scan1).evaluate()

        # Sample 2: Non-compliant Biscuit Pack (Missing Tax statement, approx net wt, missing email)
        scan2, _ = Scan.objects.get_or_create(
            user=demo_user,
            product_name="Crispy Butter Crunch Biscuits",
            defaults={
                "category": "food",
                "pre_packed_type": "Flexible Pillow Pack",
                "notes": "Notice issued for violation of Rule 12(1) (Approx net weight) and Rule 6(1)(e) (Taxes omission).",
            },
        )
        ScanImage.objects.get_or_create(
            scan=scan2,
            label_type="front",
            defaults={
                "ocr_text": (
                    "CRISPY CRUNCH BAKES\n"
                    "PRODUCT: BUTTER COOKIES\n"
                    "NET WT: Approx 200 g\n"
                    "MRP Rs. 45.00\n"
                    "DATE OF PKG: 09/2026\n"
                    "PACKED BY: City Bakery Works, Industrial Estate, Pune 411001\n"
                    "FEEDBACK: Call 020-24458899\n"
                ),
                "avg_confidence": 78.5,
            },
        )
        fields2 = {
            "generic_name": ("Butter Cookies", "Common / Generic Name of Commodity", 85.0),
            "net_quantity": ("Approx 200 g", "Net Quantity", 80.0),
            "mrp": ("₹ 45.00", "Maximum Retail Price (MRP)", 75.0),
            "mfg_date": ("09/2026", "Month & Year of Manufacture", 82.0),
            "manufacturer_details": ("City Bakery Works, Industrial Estate, Pune 411001", "Manufacturer Name & Address", 79.0),
            "consumer_care": ("Tel: 020-24458899", "Consumer Care Helpline & Email", 70.0),
            "country_of_origin": ("", "Country of Origin", 0.0),
            "unit_sale_price": ("", "Unit Sale Price (USP)", 0.0),
            "best_before": ("", "Best Before", 0.0),
        }
        for k, (v, lbl, c) in fields2.items():
            ExtractedField.objects.update_or_create(
                scan=scan2, key=k, defaults={"value": v, "label": lbl, "confidence": c, "is_user_edited": False}
            )
        ComplianceEngine(scan2).evaluate()

        # Sample 3: Needs Review Imported Wireless Headphones
        scan3, _ = Scan.objects.get_or_create(
            user=demo_user,
            product_name="ProAcoustic ANC Wireless Earbuds",
            defaults={
                "category": "imported",
                "pre_packed_type": "Rigid Box",
                "notes": "Flagged for manual physical verification of importer address details and font height.",
            },
        )
        ScanImage.objects.get_or_create(
            scan=scan3,
            label_type="front",
            defaults={
                "ocr_text": (
                    "PROACOUSTIC SOUND\n"
                    "GENERIC NAME: BLUETOOTH STEREO EARBUDS\n"
                    "NET QUANTITY: 1 N\n"
                    "MRP: Rs. 2,999.00 (Incl. of all taxes)\n"
                    "MONTH & YEAR OF IMPORT: 08/2026\n"
                    "IMPORTED BY: Global Gadgets India Ltd\n"
                    "COUNTRY OF ORIGIN: VIETNAM\n"
                    "CONSUMER CARE: Global Gadgets, Helpline: 1800-111-999, Email: service@globalgadgets.in"
                ),
                "avg_confidence": 88.0,
            },
        )
        fields3 = {
            "generic_name": ("Bluetooth Stereo Earbuds", "Common / Generic Name of Commodity", 90.0),
            "net_quantity": ("1 N", "Net Quantity", 92.0),
            "mrp": ("₹ 2,999.00 (Incl. of all taxes)", "Maximum Retail Price (MRP)", 91.0),
            "mfg_date": ("08/2026", "Month & Year of Manufacture", 88.0),
            "manufacturer_details": ("Global Gadgets India Ltd", "Manufacturer Name & Address", 65.0),
            "consumer_care": ("Tel: 1800-111-999 | Email: service@globalgadgets.in", "Consumer Care Helpline & Email", 90.0),
            "country_of_origin": ("VIETNAM", "Country of Origin", 95.0),
            "unit_sale_price": ("₹ 2999.00 per N", "Unit Sale Price (USP)", 85.0),
            "best_before": ("", "Best Before", 0.0),
        }
        for k, (v, lbl, c) in fields3.items():
            ExtractedField.objects.update_or_create(
                scan=scan3, key=k, defaults={"value": v, "label": lbl, "confidence": c, "is_user_edited": False}
            )
        ComplianceEngine(scan3).evaluate()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded demo environment! Login with username 'demo_officer' to inspect samples."
            )
        )
