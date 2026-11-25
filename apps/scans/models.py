"""
Models for Commodity Label Scans, Uploaded Images, and Extracted Fields.
"""
import os
import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse


def randomized_upload_path(instance, filename: str) -> str:
    """Generate a collision-resistant, randomized upload path for uploaded label images."""
    ext = os.path.splitext(filename)[1].lower()
    clean_ext = ext if ext else ".jpg"
    return f"scans/{uuid.uuid4().hex}{clean_ext}"


class Scan(models.Model):
    """
    Top-level compliance inspection scan record for a packaged product.
    """
    CATEGORY_CHOICES = [
        ("food", "Food & Beverages"),
        ("cosmetics", "Cosmetics & Personal Care"),
        ("electronics", "Electronics & Appliances"),
        ("imported", "Imported Goods"),
        ("general", "General Merchandise"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending Analysis"),
        ("PROCESSING", "Processing OCR & Rules"),
        ("COMPLIANT", "Compliant"),
        ("NON_COMPLIANT", "Non-Compliant"),
        ("NEEDS_REVIEW", "Needs Manual Verification"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scans",
        db_index=True,
    )
    product_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional product trade or brand name",
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="general",
    )
    pre_packed_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="e.g., Standard Retail Pack, Multi-piece, Combination Pack",
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
    )
    score = models.FloatField(
        default=0.0,
        help_text="Calculated compliance percentage (0.0 to 100.0)",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Inspector observations or manual annotations",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Commodity Scan"
        verbose_name_plural = "Commodity Scans"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "category"]),
        ]

    def __str__(self):
        title = self.product_name or f"Scan #{self.id}"
        return f"{title} [{self.get_status_display()}]"

    def get_absolute_url(self):
        return reverse("scans:detail", kwargs={"pk": self.pk})

    @property
    def status_badge_class(self) -> str:
        mapping = {
            "COMPLIANT": "badge-compliant",
            "NON_COMPLIANT": "badge-non-compliant",
            "NEEDS_REVIEW": "badge-review",
            "PENDING": "badge-pending",
            "PROCESSING": "badge-pending",
        }
        return mapping.get(self.status, "badge-pending")

    @property
    def combined_ocr_text(self) -> str:
        """Combine raw OCR text across all images in panel priority."""
        return "\n\n".join(
            img.ocr_text for img in self.images.all() if img.ocr_text.strip()
        )


class ScanImage(models.Model):
    """
    Individual label/package panel image attached to a Scan.
    """
    PANEL_CHOICES = [
        ("front", "Front Panel (Principal Display)"),
        ("back", "Back Panel (Information Panel)"),
        ("side", "Side / Flange Panel"),
        ("other", "Other / Supplementary"),
    ]

    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=randomized_upload_path)
    label_type = models.CharField(
        max_length=20,
        choices=PANEL_CHOICES,
        default="front",
    )
    ocr_text = models.TextField(blank=True, default="")
    avg_confidence = models.FloatField(
        default=0.0,
        help_text="Average OCR token recognition confidence score (0-100)",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Scan Image"
        verbose_name_plural = "Scan Images"
        ordering = ["id"]

    def __str__(self):
        return f"Image #{self.id} for {self.scan} ({self.get_label_type_display()})"


class ExtractedField(models.Model):
    """
    Parsed declaration key-value pair extracted from OCR text or edited by user.
    """
    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name="extracted_fields",
    )
    key = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Canonical field key (e.g., manufacturer_details, net_quantity, mrp)",
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Human-readable statutory label",
    )
    value = models.TextField(blank=True, default="")
    confidence = models.FloatField(default=0.0)
    is_user_edited = models.BooleanField(
        default=False,
        help_text="Indicates whether this field was manually modified by the inspector",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Extracted Field"
        verbose_name_plural = "Extracted Fields"
        unique_together = ("scan", "key")
        ordering = ["id"]

    def __str__(self):
        return f"{self.key}: {self.value[:30]}"
