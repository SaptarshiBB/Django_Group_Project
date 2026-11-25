"""
Views for PDF Compliance Inspection Reports.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from apps.scans.models import Scan
from services.reports import ComplianceReportGenerator


class DownloadPDFReportView(LoginRequiredMixin, View):
    """Generates and streams an official Legal Metrology A4 PDF Compliance Report."""

    def get(self, request, pk):
        qs = Scan.objects.select_related("user").prefetch_related(
            "images", "extracted_fields", "rule_results__rule"
        )
        if not (request.user.is_superuser or request.user.is_staff):
            qs = qs.filter(user=request.user)

        scan = get_object_or_404(qs, pk=pk)

        # Generate ReportLab PDF buffer
        generator = ComplianceReportGenerator(scan)
        pdf_buffer = generator.generate()

        filename = f"Legal_Metrology_Inspection_INSP-{scan.id:06d}.pdf"
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
