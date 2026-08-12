"""Reports App — URL Configuration."""

from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("overdue/",    views.OverdueReportView.as_view(),       name="overdue"),
    path("stats/",      views.BorrowingStatisticsView.as_view(), name="borrowing-stats"),
    path("inventory/",  views.InventoryReportView.as_view(),     name="inventory"),
    path("fines/",      views.FineSummaryView.as_view(),         name="fine-summary"),
]
