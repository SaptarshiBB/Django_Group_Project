from django.contrib import admin
from .models import Rule, RuleResult


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "rule_reference", "severity", "applies_to_category", "is_active")
    list_filter = ("severity", "applies_to_category", "is_active")
    search_fields = ("code", "title", "description", "rule_reference")
    ordering = ("code",)


@admin.register(RuleResult)
class RuleResultAdmin(admin.ModelAdmin):
    list_display = ("scan", "rule", "status", "created_at")
    list_filter = ("status", "rule")
    search_fields = ("scan__product_name", "rule__title", "message", "matched_text")
    readonly_fields = ("scan", "rule", "status", "message", "matched_text", "created_at")
