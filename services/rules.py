"""
Compliance Engine for Legal Metrology (Packaged Commodities) Rules, 2011.

NOTE: All statutory references, rules, and numerical standards must be verified
against the official gazette notifications and published text of the
Legal Metrology Act, 2009 and the Legal Metrology (Packaged Commodities) Rules, 2011,
as amended from time to time by the Ministry of Consumer Affairs, Food & Public Distribution.
"""
import re
from typing import Dict, List, Tuple
from django.db import transaction


# Rule Evaluator Registry: maps rule.code -> callable function
EVALUATOR_REGISTRY = {}


def register_evaluator(code: str):
    """Decorator to register an evaluator function for a given Rule code."""
    def decorator(func):
        EVALUATOR_REGISTRY[code] = func
        return func
    return decorator


@register_evaluator("RULE_MFR_ADDR")
def evaluate_mfr_address(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(a): Name and complete address of the manufacturer, or where the
    manufacturer is not the packer, the name and address of the manufacturer and packer,
    and for any imported commodity, the name and address of the importer.
    """
    val = fields.get("manufacturer_details", "").strip()
    if not val:
        return (
            "FAIL",
            "Mandatory declaration of Manufacturer, Packer, or Importer name and postal address is missing from the package label.",
            "",
        )

    # Basic length check to ensure it's not just a solitary word
    if len(val) < 12 or not any(kw in val.lower() for kw in ["pvt", "ltd", "mfg", "packed", "by", "road", "street", "nagar", "plot", "area", "dist", "floor"]):
        return (
            "NEEDS_REVIEW",
            f"Manufacturer declaration '{val}' is detected but may lack full postal address or pincode required under Rule 6(1)(a). Physical verification recommended.",
            val,
        )

    return (
        "PASS",
        f"Manufacturer / Packer / Importer details successfully declared: '{val[:80]}...'",
        val,
    )


@register_evaluator("RULE_GENERIC_NAME")
def evaluate_generic_name(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(b): The common or generic names of the commodity contained in the package
    and in case of packages with more than one product, the name and number or quantity of each product.
    """
    val = fields.get("generic_name", "").strip()
    if not val:
        return (
            "FAIL",
            "Mandatory declaration of the common or generic name of the commodity is missing from the label.",
            "",
        )

    return (
        "PASS",
        f"Generic/common commodity name declared: '{val}'.",
        val,
    )


@register_evaluator("RULE_NET_QTY")
def evaluate_net_quantity(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(c) & Rule 12: The net quantity, in terms of the standard unit of weight or
    measure, of the commodity contained in the package. Standard metric units: g, kg, ml, L, mm, cm, m, N.
    """
    val = fields.get("net_quantity", "").strip()
    if not val:
        return (
            "FAIL",
            "Net quantity declaration not found. Rule 6(1)(c) mandates net weight, volume, or count in standard units.",
            "",
        )

    # Standard SI units permitted under Legal Metrology Rules
    valid_si_pattern = re.compile(
        r"^[0-9]+(?:\.[0-9]+)?\s*(g|gm|gms|kg|kilograms?|ml|millilitres?|l|ltr|litres?|liter|mm|cm|m|metres?|n|u|units?|nos?|count|pieces?|pcs?)$",
        re.I,
    )
    if not valid_si_pattern.match(val):
        return (
            "WARNING",
            f"Net quantity '{val}' is present but could not be definitively validated against standard SI metric units (g, kg, ml, L, N).",
            val,
        )

    return (
        "PASS",
        f"Net quantity is declared in standard metric units: '{val}'.",
        val,
    )


@register_evaluator("RULE_NET_QTY_NO_APPROX")
def evaluate_net_qty_prohibited_terms(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 12(1) & Rule 13: Net quantity shall not be qualified by expressions like
    'approximate', 'about', 'when packed', or other indeterminate expressions.
    """
    net_val = fields.get("net_quantity", "").strip()
    prohibited = ["approx", "about", "approximate", "when packed", "minimum"]

    # Check extracted net qty
    for word in prohibited:
        if word in net_val.lower():
            return (
                "FAIL",
                f"Prohibited non-standard expression '{word}' detected near net quantity declaration. Violates Rule 12(1).",
                net_val,
            )

    # Check proximity in raw text near "net"
    net_window_pattern = re.compile(r"net\s*(?:wt|qty|content|quantity)[^\n]{0,50}", re.I)
    matches = net_window_pattern.findall(raw_text)
    for m in matches:
        for word in prohibited:
            if word in m.lower():
                return (
                    "FAIL",
                    f"Prohibited qualification '{word}' found in net quantity declaration: '{m}'.",
                    m,
                )

    return (
        "PASS",
        "Net quantity declaration is free from non-standard qualifying terms ('approx', 'about', 'when packed').",
        net_val,
    )


@register_evaluator("RULE_MFG_DATE")
def evaluate_mfg_date(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(d): The month and year in which the commodity is manufactured or
    packed or imported shall be declared on the package.
    """
    val = fields.get("mfg_date", "").strip()
    if not val:
        return (
            "FAIL",
            "Month and Year of manufacture, packing, or import is missing from the label.",
            "",
        )

    # Validate month/year format e.g. 05/2026, May 2026, 05-26
    date_format_check = re.compile(
        r"(0[1-9]|1[0-2]|[a-zA-Z]{3,9})[\/\.\-\s]+(20[2-3][0-9]|[0-9]{2})",
        re.I,
    )
    if not date_format_check.search(val):
        return (
            "NEEDS_REVIEW",
            f"Manufacturing date '{val}' found, but format should be confirmed as standard Month/Year under Rule 6(1)(d).",
            val,
        )

    return (
        "PASS",
        f"Month and Year of manufacture/packing/import is declared: '{val}'.",
        val,
    )


@register_evaluator("RULE_MRP_DECLARATION")
def evaluate_mrp_declaration(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(e): The maximum retail price (MRP) at which the commodity in packaged
    form may be sold to the consumer.
    """
    val = fields.get("mrp", "").strip()
    if not val:
        return (
            "FAIL",
            "Maximum Retail Price (MRP) declaration is missing from the label.",
            "",
        )

    num_match = re.search(r"[0-9]+(?:\.[0-9]{1,2})?", val)
    if not num_match:
        return (
            "FAIL",
            f"MRP field '{val}' does not contain a discernible numeric price value.",
            val,
        )

    return (
        "PASS",
        f"Maximum Retail Price is declared: '{val}'.",
        val,
    )


@register_evaluator("RULE_MRP_INCLUSIVE_TAXES")
def evaluate_mrp_taxes(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(e): The retail sale price shall be declared in the form 'Maximum or Max. retail
    price... inclusive of all taxes' or in the form 'MRP Rs... incl. of all taxes'.
    """
    val = fields.get("mrp", "").strip()
    raw_lower = raw_text.lower()

    if not val:
        return (
            "FAIL",
            "Cannot verify inclusive of taxes requirement because MRP declaration is missing.",
            "",
        )

    # Check if 'incl' or 'taxes' is part of the extracted field or in proximity to MRP in raw text
    val_lower = val.lower()
    if "incl" in val_lower and "tax" in val_lower:
        return (
            "PASS",
            f"MRP explicitly declares inclusive of all taxes: '{val}'.",
            val,
        )

    # Search raw text in proximity to MRP
    mrp_tax_pattern = re.compile(
        r"m\.?r\.?p\.?[^\n\r]{0,40}(?:incl\.?|inclusive)\s*(?:of)?\s*all\s*taxes",
        re.I,
    )
    m = mrp_tax_pattern.search(raw_text)
    if m:
        return (
            "PASS",
            f"MRP declared with statutory tax wording: '{m.group(0)}'.",
            m.group(0),
        )

    return (
        "WARNING",
        f"MRP value '{val}' is present, but explicit phrase '(Inclusive of all taxes)' was not confirmed on the label. Mandatory under Rule 6(1)(e).",
        val,
    )


@register_evaluator("RULE_CONSUMER_CARE")
def evaluate_consumer_care(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(n): Name, address, telephone number, and e-mail address of the person
    who can be contacted in case of consumer complaints.
    """
    val = fields.get("consumer_care", "").strip()
    if not val:
        return (
            "FAIL",
            "Mandatory Consumer Care helpline details (tel, email, and/or address) missing from label. Violates Rule 6(1)(n).",
            "",
        )

    has_tel = "tel:" in val.lower() or bool(re.search(r"\b\d{8,12}\b", val))
    has_email = "email:" in val.lower() or "@" in val

    if has_tel and has_email:
        return (
            "PASS",
            f"Consumer care contacts fully declared with telephone and email: '{val}'.",
            val,
        )
    elif has_tel or has_email:
        return (
            "WARNING",
            f"Consumer care details partially declared ('{val}'). Both telephone number and email address are required under Rule 6(1)(n).",
            val,
        )

    return (
        "NEEDS_REVIEW",
        f"Consumer care text detected ('{val}'), but standard helpline phone or email could not be parsed.",
        val,
    )


@register_evaluator("RULE_COUNTRY_OF_ORIGIN")
def evaluate_country_of_origin(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(aa): The name of the country of origin or manufacture or assembly shall
    be mentioned on the package, mandatory for imported commodities.
    """
    val = fields.get("country_of_origin", "").strip()
    is_imported = category == "imported" or "import" in raw_text.lower()

    if val:
        return (
            "PASS",
            f"Country of origin explicitly declared: '{val}'.",
            val,
        )

    if is_imported:
        return (
            "FAIL",
            "Country of origin declaration is mandatory for imported packaged goods under Rule 6(1)(aa), but was not found.",
            "",
        )

    # For domestic or general goods where not explicitly marked imported
    return (
        "NEEDS_REVIEW",
        "Country of origin declaration not detected. If this commodity is imported, Rule 6(1)(aa) strictly requires Country of Origin.",
        "",
    )


@register_evaluator("RULE_UNIT_SALE_PRICE")
def evaluate_unit_sale_price(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 6(1)(f): Unit sale price in rupees and paise per g/kg/ml/l/unit for packages
    containing more than 1 unit or greater than 100g/100ml.
    """
    val = fields.get("unit_sale_price", "").strip()
    if val:
        return (
            "PASS",
            f"Unit Sale Price (USP) declared: '{val}'.",
            val,
        )

    return (
        "NEEDS_REVIEW",
        "Unit Sale Price (USP) declaration not identified. Required under Rule 6(1)(f) for packages containing more than 1 number or net quantity > 100g/100ml. Verify specimen packaging.",
        "",
    )


@register_evaluator("RULE_NUMERAL_HEIGHT")
def evaluate_numeral_height(fields: Dict[str, str], raw_text: str, category: str) -> Tuple[str, str, str]:
    """
    Rule 7 & First Schedule (Table 1): Minimum height of numerals and letters
    in declarations (e.g. 1.0mm to 6.0mm depending on net quantity range and area of display).
    Digital photos without calibrated scale markers cannot guarantee physical millimeter height.
    """
    net_val = fields.get("net_quantity", "").strip()
    guidance = (
        f"Rule 7 / Table 1 requires minimum numeral height (e.g. <=50g: 1mm, 50-200g: 2mm, 200g-1kg: 4mm, >1kg: 6mm). "
        f"For Net Qty '{net_val or 'Unspecified'}', physical print height must be manually measured on specimen packaging."
    )
    return (
        "NEEDS_REVIEW",
        guidance,
        net_val,
    )


class ComplianceEngine:
    """Executes registered rules against a Scan and persists RuleResult records."""

    def __init__(self, scan):
        self.scan = scan

    @transaction.atomic
    def evaluate(self) -> Dict:
        """
        Run all active database rules matching scan category or 'all'.
        Deletes old RuleResults, creates fresh ones, recalculates scan score and status.
        """
        from apps.compliance.models import Rule, RuleResult
        from apps.scans.models import ExtractedField

        # Gather extracted fields dictionary
        fields_qs = self.scan.extracted_fields.all()
        fields_dict = {f.key: f.value for f in fields_qs}
        raw_text = self.scan.combined_ocr_text

        # Fetch active rules for scan's category + 'all'
        applicable_rules = Rule.objects.filter(
            is_active=True
        ).filter(
            applies_to_category__in=["all", self.scan.category]
        ).order_by("code")

        # Clear previous results for this scan
        self.scan.rule_results.all().delete()

        pass_count = 0
        fail_count = 0
        warning_count = 0
        review_count = 0
        total_eval = 0

        created_results = []
        for rule in applicable_rules:
            evaluator_fn = EVALUATOR_REGISTRY.get(rule.code)
            if evaluator_fn:
                status, message, matched = evaluator_fn(
                    fields_dict, raw_text, self.scan.category
                )
            else:
                status = "NEEDS_REVIEW"
                message = f"No automated evaluator registered for rule {rule.code}. Manual verification required."
                matched = ""

            # Count statuses
            total_eval += 1
            if status == "PASS":
                pass_count += 1
            elif status == "FAIL":
                fail_count += 1
            elif status == "WARNING":
                warning_count += 1
            elif status == "NEEDS_REVIEW":
                review_count += 1

            result_obj = RuleResult(
                scan=self.scan,
                rule=rule,
                status=status,
                message=message,
                matched_text=matched,
            )
            created_results.append(result_obj)

        RuleResult.objects.bulk_create(created_results)

        # Calculate compliance score (PASS = 1.0, WARNING = 0.5, NEEDS_REVIEW = 0.5, FAIL = 0.0)
        if total_eval > 0:
            weighted_points = (pass_count * 1.0) + (warning_count * 0.5) + (review_count * 0.5)
            score = round((weighted_points / total_eval) * 100.0, 1)
        else:
            score = 0.0

        # Overall Status Verdict
        if fail_count > 0:
            verdict = "NON_COMPLIANT"
        elif review_count > 0 or warning_count > 0:
            verdict = "NEEDS_REVIEW"
        else:
            verdict = "COMPLIANT"

        self.scan.score = score
        self.scan.status = verdict
        self.scan.save(update_fields=["score", "status", "updated_at"])

        return {
            "score": score,
            "status": verdict,
            "total_rules": total_eval,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "warning_count": warning_count,
            "review_count": review_count,
        }
