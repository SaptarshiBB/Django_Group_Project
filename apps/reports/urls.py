from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("<int:pk>/pdf/", views.DownloadPDFReportView.as_view(), name="download_pdf"),
]
