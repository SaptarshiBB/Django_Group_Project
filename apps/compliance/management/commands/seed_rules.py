"""
Management command to seed statutory rules from Legal Metrology (Packaged Commodities) Rules, 2011.
"""
from django.core.management.base import BaseCommand
from apps.compliance.models import Rule


DEFAULT_RULES = [
    {
        "code": "RULE_MFR_ADDR",
        "title": "Manufacturer / Packer / Importer Name & Address",
        "description": "Mandates complete name and definite postal address of manufacturer, packer, or importer.",
        "rule_reference": "Rule 6(1)(a), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_GENERIC_NAME",
        "title": "Common or Generic Name of Commodity",
        "description": "The common or generic name of commodity must be prominently stated on principal display panel.",
        "rule_reference": "Rule 6(1)(b), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_NET_QTY",
        "title": "Net Quantity in Standard SI Metric Units",
        "description": "Net quantity shall be stated in standard units of weight, volume, or count (g, kg, ml, L, N).",
        "rule_reference": "Rule 6(1)(c) & Rule 12, Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_NET_QTY_NO_APPROX",
        "title": "Prohibition of Expressions like 'Approx' or 'When Packed'",
        "description": "Net quantity shall not be qualified by expressions such as 'approximate', 'about', 'when packed', etc.",
        "rule_reference": "Rule 12(1), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "major",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_MFG_DATE",
        "title": "Month and Year of Manufacture / Packing / Import",
        "description": "Month and year of manufacture, packing, or import must be clearly declared.",
        "rule_reference": "Rule 6(1)(d), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_MRP_DECLARATION",
        "title": "Maximum Retail Price (MRP) Declaration",
        "description": "The maximum retail price (MRP) at which the pre-packed commodity may be sold to the consumer.",
        "rule_reference": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_MRP_INCLUSIVE_TAXES",
        "title": "MRP Inclusive of All Taxes Specification",
        "description": "MRP must explicitly include the words 'Inclusive of all taxes' or 'Incl. of all taxes'.",
        "rule_reference": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "major",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_CONSUMER_CARE",
        "title": "Consumer Care Redressal Contacts",
        "description": "Name, address, telephone number, and email address of person/office to be contacted for consumer grievances.",
        "rule_reference": "Rule 6(1)(n), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_COUNTRY_OF_ORIGIN",
        "title": "Country of Origin Declaration",
        "description": "Name of country of origin or manufacture shall be stated on package, mandatory for imported commodities.",
        "rule_reference": "Rule 6(1)(aa), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "critical",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_UNIT_SALE_PRICE",
        "title": "Unit Sale Price (USP) Declaration",
        "description": "Declaration of unit sale price in rupees and paise per g/kg/ml/l/unit for multi-piece or packages > 100g/ml.",
        "rule_reference": "Rule 6(1)(f), Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "major",
        "applies_to_category": "all",
        "is_active": True,
    },
    {
        "code": "RULE_NUMERAL_HEIGHT",
        "title": "Numeral and Letter Height Standards",
        "description": "Minimum numeral height according to First Schedule Table 1 based on net quantity band. Requires physical specimen check.",
        "rule_reference": "Rule 7 & First Schedule, Legal Metrology (Packaged Commodities) Rules, 2011",
        "severity": "minor",
        "applies_to_category": "all",
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Seed or update default Legal Metrology (Packaged Commodities) Rules, 2011"

    def handle(self, *args, **options):
        self.stdout.write("Seeding statutory Legal Metrology compliance rules...")
        created_count = 0
        updated_count = 0

        for r_data in DEFAULT_RULES:
            obj, created = Rule.objects.update_or_create(
                code=r_data["code"],
                defaults={
                    "title": r_data["title"],
                    "description": r_data["description"],
                    "rule_reference": r_data["rule_reference"],
                    "severity": r_data["severity"],
                    "applies_to_category": r_data["applies_to_category"],
                    "is_active": r_data["is_active"],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {len(DEFAULT_RULES)} rules ({created_count} created, {updated_count} updated)."
            )
        )
