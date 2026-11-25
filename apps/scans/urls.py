from django.urls import path
from . import views

app_name = "scans"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("history/", views.ScanListView.as_view(), name="list"),
    path("new/", views.ScanCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ScanDetailView.as_view(), name="detail"),
    path("<int:pk>/recalculate/", views.ScanRecalculateView.as_view(), name="recalculate"),
    path("<int:pk>/delete/", views.ScanDeleteView.as_view(), name="delete"),
]
