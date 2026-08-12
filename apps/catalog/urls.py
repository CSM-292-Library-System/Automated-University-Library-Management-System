"""Catalog App — URL Configuration."""

from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    # ── Book Catalog ──────────────────────────────────────────────────────
    path("",                      views.BookListView.as_view(),   name="book-list"),
    path("<int:pk>/",             views.BookDetailView.as_view(), name="book-detail"),
    path("add/",                  views.BookCreateView.as_view(), name="book-add"),
    path("<int:pk>/edit/",        views.BookUpdateView.as_view(), name="book-edit"),
    path("<int:pk>/delete/",      views.BookDeleteView.as_view(), name="book-delete"),

    # ── Book Copies ───────────────────────────────────────────────────────
    path("<int:book_pk>/copies/add/",        views.BookCopyCreateView.as_view(), name="copy-add"),
    path("copies/<int:pk>/edit/",            views.BookCopyUpdateView.as_view(), name="copy-edit"),
]
