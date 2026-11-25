"""
Models for the Legal Metrology Compliance Engine.
Stores statutory rules and per-scan rule verification results.
"""
from django.db import models


class Rule(models.Model):
    """
    Statutory rule under Legal Metrology (Packaged Commodities) Rules, 2011.
    """
    SEVERITY_CHOICES = [
        ("critical", "Critical (Mandatory)"),
        ("major", "Major"),
        ("minor", "Minor / Advisory"),
    ]

    CATEGORY_CHOICES = [
        ("all", "All Commodity Categories"),
        ("food", "Food & Beverages"),
        ("cosmetics", "Cosmetics & Toiletries"),
        ("electronics", "Electronics & Electrical Appliances"),
        ("imported", "Imported Goods"),
        ("general", "General Commodities"),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique rule identifier matching the evaluator code (e.g. RULE_MFR_ADDR)",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Statutory requirement explanation")
    rule_reference = models.CharField(
        max_length=255,
        help_text="Official reference in Legal Metrology (Packaged Commodities) Rules, 2011",
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="critical",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Disable to skip this rule during evaluation",
    )
    applies_to_category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="all",
        help_text="Commodity category filter",
    )

    class Meta:
        verbose_name = "Compliance Rule"
        verbose_name_plural = "Compliance Rules"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class RuleResult(models.Model):
    """
    Evaluation outcome of a specific Rule against a Scan.
    """
    STATUS_CHOICES = [
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
        ("WARNING", "Warning"),
        ("NEEDS_REVIEW", "Needs Review"),
    ]

    scan = models.ForeignKey(
        "scans.Scan",
        on_delete=models.CASCADE,
        related_name="rule_results",
    )
    rule = models.ForeignKey(
        Rule,
        on_delete=models.CASCADE,
        related_name="results",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
    )
    message = models.TextField(help_text="Detailed finding and explanation")
    matched_text = models.TextField(
        blank=True,
        default="",
        help_text="Extracted text excerpt that triggered or satisfied the rule",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rule Evaluation Result"
        verbose_name_plural = "Rule Evaluation Results"
        indexes = [
            models.Index(fields=["scan", "status"]),
        ]
        ordering = ["rule__code"]

    def __str__(self):
        return f"{self.scan_id} - {self.rule.code}: {self.status}"
