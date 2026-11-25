"""
Views for Scans: Dashboard, Multi-Image Upload & OCR Execution,
Detailed Legal Metrology Compliance Inspection, and Field Re-evaluation.
"""
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView
from .forms import ScanUploadForm
from .models import ExtractedField, Scan, ScanImage
from apps.compliance.models import Rule, RuleResult
from services.extractor import FieldExtractor
from services.ocr import OCRPipeline, OCRServiceError
from services.rules import ComplianceEngine

logger = logging.getLogger(__name__)


class UserOwnedQuerysetMixin:
    """Ensures regular users only access their own scans, while superusers/staff see all."""

    def get_queryset(self):
        qs = Scan.objects.select_related("user").prefetch_related("images", "rule_results__rule")
        if self.request.user.is_superuser or self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "scans/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        base_qs = Scan.objects.all() if (user.is_superuser or user.is_staff) else Scan.objects.filter(user=user)

        total_scans = base_qs.count()
        compliant_scans = base_qs.filter(status="COMPLIANT").count()
        non_compliant_scans = base_qs.filter(status="NON_COMPLIANT").count()
        needs_review_scans = base_qs.filter(status="NEEDS_REVIEW").count()

        compliance_rate = round((compliant_scans / total_scans * 100), 1) if total_scans > 0 else 0.0

        recent_scans = base_qs.order_by("-created_at")[:6]
        category_stats = base_qs.values("category").annotate(count=Count("id")).order_by("-count")

        ctx.update(
            {
                "total_scans": total_scans,
                "compliant_scans": compliant_scans,
                "non_compliant_scans": non_compliant_scans,
                "needs_review_scans": needs_review_scans,
                "compliance_rate": compliance_rate,
                "recent_scans": recent_scans,
                "category_stats": category_stats,
            }
        )
        return ctx


class ScanListView(LoginRequiredMixin, UserOwnedQuerysetMixin, ListView):
    model = Scan
    template_name = "scans/scan_list.html"
    context_object_name = "scans"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        category = self.request.GET.get("category", "").strip()
        date_from = self.request.GET.get("date_from", "").strip()
        date_to = self.request.GET.get("date_to", "").strip()

        if query:
            qs = qs.filter(Q(product_name__icontains=query) | Q(notes__icontains=query))

        if status:
            qs = qs.filter(status=status)

        if category:
            qs = qs.filter(category=category)

        if date_from:
            d_from = parse_date(date_from)
            if d_from:
                qs = qs.filter(created_at__date__gte=d_from)

        if date_to:
            d_to = parse_date(date_to)
            if d_to:
                qs = qs.filter(created_at__date__lte=d_to)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_category"] = self.request.GET.get("category", "")
        ctx["current_date_from"] = self.request.GET.get("date_from", "")
        ctx["current_date_to"] = self.request.GET.get("date_to", "")
        return ctx


class ScanCreateView(LoginRequiredMixin, CreateView):
    model = Scan
    form_class = ScanUploadForm
    template_name = "scans/scan_create.html"

    def form_valid(self, form):
        uploaded_files = form.cleaned_data.get("images", [])

        with transaction.atomic():
            scan = form.save(commit=False)
            scan.user = self.request.user
            scan.status = "PROCESSING"
            scan.save()

            # Initialize OCR pipeline
            ocr_pipeline = OCRPipeline()
            merged_ocr_lines = []
            ocr_diagnostics = []

            for i, f in enumerate(uploaded_files):
                # Infer panel type based on upload index if not specified
                panel = "front" if i == 0 else ("back" if i == 1 else "side")
                scan_img = ScanImage(scan=scan, image=f, label_type=panel)
                scan_img.save()

                try:
                    # Run OpenCV preprocessing + Tesseract
                    extracted_text, avg_conf, meta = ocr_pipeline.extract_text(scan_img.image)
                    scan_img.ocr_text = extracted_text
                    scan_img.avg_confidence = avg_conf
                    scan_img.save(update_fields=["ocr_text", "avg_confidence"])

                    if extracted_text.strip():
                        merged_ocr_lines.append(extracted_text)

                    if meta.get("error"):
                        ocr_diagnostics.append(meta.get("message"))
                except Exception as e:
                    logger.exception("Error extracting OCR from image %s: %s", f.name, e)
                    ocr_diagnostics.append(str(e))

            # Combine OCR output across all panel images
            full_text = "\n\n".join(merged_ocr_lines)

            # Run statutory field extraction heuristics
            extractor = FieldExtractor(full_text)
            extracted_fields = extractor.extract_all()

            for key, field_data in extracted_fields.items():
                ExtractedField.objects.create(
                    scan=scan,
                    key=key,
                    label=field_data["label"],
                    value=field_data["value"],
                    confidence=field_data["confidence"],
                    is_user_edited=False,
                )

            # Run compliance rules engine
            engine = ComplianceEngine(scan)
            results = engine.evaluate()

        if ocr_diagnostics:
            messages.warning(
                self.request,
                f"Scan #{scan.id} created. OCR diagnostic notice: {ocr_diagnostics[0]}. "
                "You can review or enter declarations manually in the table below."
            )
        else:
            messages.success(
                self.request,
                f"Scan #{scan.id} processed successfully. "
                f"Overall Status: {scan.get_status_display()} ({scan.score}% compliance score)."
            )

        return redirect("scans:detail", pk=scan.pk)


class ScanDetailView(LoginRequiredMixin, UserOwnedQuerysetMixin, DetailView):
    model = Scan
    template_name = "scans/scan_detail.html"
    context_object_name = "scan"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["extracted_fields"] = self.object.extracted_fields.all().order_by("id")
        ctx["rule_results"] = self.object.rule_results.select_related("rule").all().order_by("rule__code")
        ctx["images"] = self.object.images.all()
        return ctx


class ScanRecalculateView(LoginRequiredMixin, View):
    """
    POST handler allowing the inspector to manually update OCR mistakes
    in extracted declarations and immediately re-evaluate compliance rules.
    """

    def post(self, request, pk):
        qs = Scan.objects.filter(pk=pk)
        if not (request.user.is_superuser or request.user.is_staff):
            qs = qs.filter(user=request.user)
        scan = get_object_or_404(qs)

        with transaction.atomic():
            for field in scan.extracted_fields.all():
                post_key = f"field_{field.key}"
                if post_key in request.POST:
                    new_val = request.POST.get(post_key, "").strip()
                    if new_val != field.value:
                        field.value = new_val
                        field.is_user_edited = True
                        field.confidence = 100.0  # Verified by human inspector
                        field.save(update_fields=["value", "is_user_edited", "confidence", "updated_at"])

            # Re-evaluate compliance rules
            engine = ComplianceEngine(scan)
            engine.evaluate()

        messages.success(
            request,
            f"Statutory declarations updated. Rules re-evaluated. New Status: {scan.get_status_display()} ({scan.score}%)."
        )
        return redirect("scans:detail", pk=scan.pk)


class ScanDeleteView(LoginRequiredMixin, UserOwnedQuerysetMixin, DeleteView):
    model = Scan
    template_name = "scans/scan_confirm_delete.html"
    success_url = reverse_lazy("scans:list")

    def delete(self, request, *args, **kwargs):
        scan = self.get_object()
        # Clean up image files from media storage
        for img in scan.images.all():
            if img.image:
                img.image.delete(save=False)
        messages.success(request, f"Scan #{scan.id} and associated image records were deleted.")
        return super().delete(request, *args, **kwargs)
