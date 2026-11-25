"""
Field Extraction Service.
Applies statutory regular expressions and NLP heuristics to extract mandatory packaged
commodity declarations under the Legal Metrology (Packaged Commodities) Rules, 2011.
"""
import re
from typing import Dict, Optional, Tuple


FIELD_DEFINITIONS = [
    {
        "key": "generic_name",
        "label": "Common / Generic Name of Commodity",
        "reference": "Rule 6(1)(b)",
        "mandatory": True,
    },
    {
        "key": "net_quantity",
        "label": "Net Quantity (Weight, Volume or Number)",
        "reference": "Rule 6(1)(c), Rule 12",
        "mandatory": True,
    },
    {
        "key": "mrp",
        "label": "Maximum Retail Price (MRP incl. of all taxes)",
        "reference": "Rule 6(1)(e)",
        "mandatory": True,
    },
    {
        "key": "mfg_date",
        "label": "Month & Year of Manufacture / Packing / Import",
        "reference": "Rule 6(1)(d)",
        "mandatory": True,
    },
    {
        "key": "manufacturer_details",
        "label": "Name & Address of Manufacturer / Packer / Importer",
        "reference": "Rule 6(1)(a)",
        "mandatory": True,
    },
    {
        "key": "consumer_care",
        "label": "Consumer Care Details (Name, Address, Tel, Email)",
        "reference": "Rule 6(1)(n)",
        "mandatory": True,
    },
    {
        "key": "country_of_origin",
        "label": "Country of Origin (For Imported Goods)",
        "reference": "Rule 6(1)(aa)",
        "mandatory": False,
    },
    {
        "key": "unit_sale_price",
        "label": "Unit Sale Price (USP)",
        "reference": "Rule 6(1)(f)",
        "mandatory": False,
    },
    {
        "key": "best_before",
        "label": "Best Before / Use By Date",
        "reference": "Rule 6(1)(m)",
        "mandatory": False,
    },
]


class FieldExtractor:
    """Extracts Legal Metrology declarations from OCR raw text."""

    def __init__(self, text: str):
        self.raw_text = text or ""
        # Normalized text with standardized whitespace and lowercased copy for pattern scanning
        self.clean_text = " ".join(self.raw_text.split())
        self.lines = [line.strip() for line in self.raw_text.splitlines() if line.strip()]

    def extract_all(self) -> Dict[str, Dict]:
        """
        Run extraction pipelines for all registered statutory fields.
        Returns dictionary keyed by canonical field key.
        """
        results = {}
        extractors = {
            "generic_name": self.extract_generic_name,
            "net_quantity": self.extract_net_quantity,
            "mrp": self.extract_mrp,
            "mfg_date": self.extract_mfg_date,
            "manufacturer_details": self.extract_manufacturer_details,
            "consumer_care": self.extract_consumer_care,
            "country_of_origin": self.extract_country_of_origin,
            "unit_sale_price": self.extract_unit_sale_price,
            "best_before": self.extract_best_before,
        }

        for meta in FIELD_DEFINITIONS:
            key = meta["key"]
            fn = extractors.get(key)
            val, conf = fn() if fn else ("", 0.0)
            results[key] = {
                "key": key,
                "label": meta["label"],
                "value": val.strip(),
                "confidence": conf,
                "mandatory": meta["mandatory"],
                "reference": meta["reference"],
            }
        return results

    def extract_generic_name(self) -> Tuple[str, float]:
        """
        Extract generic or common name.
        Matches explicit 'Commodity: ...', 'Product: ...', 'Generic Name: ...'
        """
        pattern = re.compile(
            r"(?:commodity|generic\s*name|product\s*name|product|item)[\s\:\.\-]+([A-Za-z0-9\s\(\)\,\-\/]+?)(?=(?:net\s*wt|mrp|mfg|batch|pkg|pkd|packed|call|email|$|\n))",
            re.IGNORECASE,
        )
        match = pattern.search(self.raw_text)
        if match:
            cand = match.group(1).strip()
            # Clean trailing punctuation
            cand = re.sub(r"[\:\,\-\.]+$", "", cand).strip()
            if len(cand) >= 3:
                return cand, 85.0

        # Heuristic fallback: check first 3 non-empty lines for typical product titles
        for line in self.lines[:3]:
            # If line is all uppercase or capitalized and not a technical code
            if len(line) >= 3 and not re.search(r"(mrp|mfd|date|batch|exp|lic|fssai|regd)", line, re.I):
                return line, 60.0

        return "", 0.0

    def extract_net_quantity(self) -> Tuple[str, float]:
        """
        Extract net quantity declaration.
        Legal Metrology requires metric units: g, kg, ml, l, mm, cm, m, or N (units).
        """
        # Explicit declaration: Net Qty / Net Content / Net Wt / Net Volume
        patterns = [
            # Pattern with explicit keyword
            re.compile(
                r"(?:net\s*(?:quantity|qty|wt|weight|vol|volume|content))[\s\:\.\-]*([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gm|gms|grams|l|ltr|litres?|liter|ml|milli\s*litres?|mm|cm|m|meters?|metres?|n|u|units?|nos?|count|pieces?|pcs?)\b",
                re.I,
            ),
            # Standalone number + unit (e.g., 500 g, 1 L, 750 ml, 10 N)
            re.compile(
                r"\b([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gm|gms|l|ltr|liter|litres?|ml|mm|cm|m|n|u)\b",
                re.I,
            ),
        ]

        for i, pat in enumerate(patterns):
            match = pat.search(self.raw_text)
            if match:
                val = match.group(1).strip()
                unit = match.group(2).strip()
                # Standardize units: gm -> g, ltr -> L, ml -> mL
                conf = 90.0 if i == 0 else 70.0
                return f"{val} {unit}", conf

        return "", 0.0

    def extract_mrp(self) -> Tuple[str, float]:
        """
        Extract Maximum Retail Price (MRP).
        Must detect value, currency symbol, and inclusive of all taxes.
        """
        # Look for full declaration first: MRP Rs. 99.00 (Incl. of all taxes)
        full_pattern = re.compile(
            r"(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price)[\s\:\.\*]*(?:rs\.?|₹|inr)?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*([\(\[]?[^\n\r]{0,35}(?:taxes|tax|incl)[^\n\r]{0,35}[\)\]]?)?",
            re.IGNORECASE,
        )
        match = full_pattern.search(self.raw_text)
        if match:
            amount = match.group(1)
            tax_text = match.group(2) or ""
            res = f"₹ {amount}"
            if "incl" in tax_text.lower():
                res += " (Incl. of all taxes)"
            elif tax_text.strip():
                res += f" ({tax_text.strip()})"
            return res, 90.0

        # Secondary search: Rs. XX.XX or ₹ XX.XX
        simple_pat = re.compile(r"(?:rs\.?|₹|inr)\s*([0-9]+(?:\.[0-9]{2})?)", re.I)
        simple_match = simple_pat.search(self.raw_text)
        if simple_match:
            return f"₹ {simple_match.group(1)}", 65.0

        return "", 0.0

    def extract_mfg_date(self) -> Tuple[str, float]:
        """
        Extract Month and Year of manufacture / packing / import.
        Accepts MM/YYYY, Month YYYY, MMM-YY, etc.
        """
        date_pattern = re.compile(
            r"(?:mfd|mfg|manufactur(?:ed|ing)|packed|pkg|pkd|import(?:ed)?|date\s*of\s*mfg)[\s\:\.\/]*([0-1]?[0-9][\/\.\-][0-9]{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\.\,\/\-]*[0-9]{2,4})",
            re.IGNORECASE,
        )
        match = date_pattern.search(self.raw_text)
        if match:
            return match.group(1).strip(), 88.0

        # General date fallback near "date" keyword
        fallback = re.compile(
            r"\b(0[1-9]|1[0-2])[\/\.\-](20[2-3][0-9]|[1-9][0-9])\b"
        )
        f_match = fallback.search(self.raw_text)
        if f_match:
            return f_match.group(0), 65.0

        return "", 0.0

    def extract_manufacturer_details(self) -> Tuple[str, float]:
        """
        Extract name and complete postal address of manufacturer / packer / importer.
        """
        pattern = re.compile(
            r"(?:manufactured|mfg|packed|pkd|imported|marketed)\s*(?:by|at)?[\s\:\-]+(.+?)(?=(?:customer\s*care|call|email|mrp|net\s*wt|batch|expiry|best\s*before|feedback|$))",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(self.raw_text)
        if match:
            val = match.group(1).strip()
            # Clean multiple spaces/newlines
            clean_val = " ".join(val.split())
            if len(clean_val) > 10:
                # Limit length to sane address length
                return clean_val[:255], 82.0

        # Search for lines containing Ltd, Pvt, Private, Factory, Industrial Area
        for line in self.lines:
            if re.search(r"\b(pvt|ltd|limited|industries|private\s*limited|mfg|co\.)\b", line, re.I):
                return line, 65.0

        return "", 0.0

    def extract_consumer_care(self) -> Tuple[str, float]:
        """
        Extract consumer care details: phone, email, and/or address.
        """
        parts = []

        # Phone / Helpline
        phone_pat = re.compile(
            r"(?:toll\s*free|helpline|care\s*no|contact|phone|tel|call)[\s\:\.\-]*(\+?[0-9\-\s]{8,15})",
            re.I,
        )
        p_match = phone_pat.search(self.raw_text)
        if p_match:
            parts.append(f"Tel: {p_match.group(1).strip()}")

        # Email
        email_pat = re.compile(
            r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b"
        )
        e_match = email_pat.search(self.raw_text)
        if e_match:
            parts.append(f"Email: {e_match.group(1).strip()}")

        # Postal Address / Customer Care Manager
        mgr_pat = re.compile(
            r"(?:consumer\s*care|customer\s*care|feedback)[\s\:\.\-]*([^\n\r]{10,80})",
            re.I,
        )
        m_match = mgr_pat.search(self.raw_text)
        if m_match and not any(m_match.group(1).strip() in part for part in parts):
            parts.append(f"Contact: {m_match.group(1).strip()}")

        if parts:
            return " | ".join(parts), 85.0

        return "", 0.0

    def extract_country_of_origin(self) -> Tuple[str, float]:
        """
        Extract Country of Origin (mandatory for imported packaged goods).
        """
        pattern = re.compile(
            r"(?:country\s*of\s*origin|made\s*in|origin|imported\s*from)[\s\:\.\-]+([A-Za-z\s]+?)(?=(?:[\,\.\;\n\r]|net|mrp|$))",
            re.IGNORECASE,
        )
        match = pattern.search(self.raw_text)
        if match:
            country = match.group(1).strip()
            if len(country) >= 3:
                return country, 88.0

        return "", 0.0

    def extract_unit_sale_price(self) -> Tuple[str, float]:
        """
        Extract Unit Sale Price (USP). e.g., 'Rs. 0.20 per g' or '₹ 1.50/ml'
        """
        pattern = re.compile(
            r"(?:unit\s*sale\s*price|u\.?s\.?p\.?)[\s\:\.\*]*(?:rs\.?|₹|inr)?\s*([0-9]+(?:\.[0-9]{1,4})?)\s*(?:per|\/)\s*([a-zA-Z]+)",
            re.IGNORECASE,
        )
        match = pattern.search(self.raw_text)
        if match:
            price = match.group(1)
            unit = match.group(2)
            return f"₹ {price} per {unit}", 85.0

        return "", 0.0

    def extract_best_before(self) -> Tuple[str, float]:
        """
        Extract best before, expiry, or use-by date declaration.
        """
        pattern = re.compile(
            r"(?:best\s*before|use\s*by|expiry|exp\s*date)[\s\:\.\/]*([A-Za-z0-9\s\/\.\-]+?)(?=(?:batch|mfg|mrp|call|$|\n))",
            re.IGNORECASE,
        )
        match = pattern.search(self.raw_text)
        if match:
            cand = match.group(1).strip()
            if len(cand) >= 3:
                return cand, 80.0

        return "", 0.0
