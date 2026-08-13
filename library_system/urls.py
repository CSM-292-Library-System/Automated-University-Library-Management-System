"""Root URL Configuration for the Automated University Library Management System."""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include


def home_redirect(request):
    """Redirect root URL to the catalog book list."""
    return redirect("catalog:book-list")


urlpatterns = [
    # Django admin interface for librarians / superusers
    path("admin/", admin.site.urls),

    # Authentication module  (login, logout, register, profile)
    path("accounts/", include("apps.users.urls", namespace="users")),

    # Book catalog  (search, browse, book detail, add/edit/delete — librarian only)
    path("catalog/", include("apps.catalog.urls", namespace="catalog")),

    # Circulation  (borrow, return, renew, loan history, fines)
    path("circulation/", include("apps.circulation.urls", namespace="circulation")),

    # Reports  (overdue list, borrowing stats, inventory)
    path("reports/", include("apps.reports.urls", namespace="reports")),

    # Notifications  (on-site overdue alerts, return confirmations)
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),

    # Default route → redirect to catalog
    path("", home_redirect, name="home"),
]

# Customise admin site headers
admin.site.site_header = "University Library Administration"
admin.site.site_title = "Library Admin"
admin.site.index_title = "Library Management Dashboard"

