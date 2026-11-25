from django.contrib import admin
from .models import ExtractedField, Scan, ScanImage


class ScanImageInline(admin.TabularInline):
    model = ScanImage
    extra = 0
    readonly_fields = ("uploaded_at", "avg_confidence")


class ExtractedFieldInline(admin.TabularInline):
    model = ExtractedField
    extra = 0


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ("id", "product_name", "user", "category", "status", "score", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("product_name", "user__username", "user__email", "notes")
    inlines = [ScanImageInline, ExtractedFieldInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(ScanImage)
class ScanImageAdmin(admin.ModelAdmin):
    list_display = ("id", "scan", "label_type", "avg_confidence", "uploaded_at")
    list_filter = ("label_type", "uploaded_at")


@admin.register(ExtractedField)
class ExtractedFieldAdmin(admin.ModelAdmin):
    list_display = ("id", "scan", "key", "value", "confidence", "is_user_edited")
    list_filter = ("key", "is_user_edited")
    search_fields = ("key", "value", "scan__product_name")
