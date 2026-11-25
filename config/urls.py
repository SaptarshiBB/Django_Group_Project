"""
URL configuration for the Legal Metrology Packaged Commodity Compliance Checker.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("scans/", include("apps.scans.urls", namespace="scans")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("", RedirectView.as_view(pattern_name="scans:dashboard", permanent=False)),
]

# Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
