"""
Catalog App — Views
===================
Handles book catalog browsing and librarian catalog management.

Access matrix:
  Browse / Search book list   → Any authenticated user
  Book detail                 → Any authenticated user
  Add / Edit / Delete book    → Staff (is_librarian) only
  Add / Edit / Delete copy    → Staff only
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from .forms import BookForm, BookCopyForm
from .models import Book, BookCopy


# ── Public (authenticated) views ─────────────────────────────────────────────

class BookListView(LoginRequiredMixin, ListView):
    """
    Main catalog page — displays all books with search and category filter.
    Annotates each book with available_copies so templates can show stock.
    """
    model = Book
    template_name = "catalog/book_list.html"
    context_object_name = "books"
    paginate_by = 20

    def get_queryset(self):
        qs = Book.objects.annotate(
            available=Count("copies", filter=Q(copies__status=BookCopy.Status.AVAILABLE))
        ).order_by("title")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(author__icontains=q)
                | Q(isbn__icontains=q)
                | Q(category__icontains=q)
            )

        category = self.request.GET.get("category", "").strip()
        if category:
            qs = qs.filter(category__iexact=category)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = (
            Book.objects.values_list("category", flat=True).distinct().order_by("category")
        )
        ctx["q"] = self.request.GET.get("q", "")
        ctx["current_category"] = self.request.GET.get("category", "")
        return ctx


class BookDetailView(LoginRequiredMixin, DetailView):
    """
    Book detail — shows metadata and all physical copies with their statuses.
    """
    model = Book
    template_name = "catalog/book_detail.html"
    context_object_name = "book"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["copies"] = self.get_object().copies.all().order_by("accession_number")
        return ctx


# ── Staff-only: Catalog Management ───────────────────────────────────────────

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin that restricts access to staff (librarian) users."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_librarian


class BookCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    """Add a new book to the catalog."""
    model = Book
    form_class = BookForm
    template_name = "catalog/book_form.html"
    success_url = reverse_lazy("catalog:book-list")

    def form_valid(self, form):
        messages.success(self.request, "Book added to catalog.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Add New Book"
        return ctx


class BookUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    """Edit an existing book's metadata."""
    model = Book
    form_class = BookForm
    template_name = "catalog/book_form.html"
    success_url = reverse_lazy("catalog:book-list")

    def form_valid(self, form):
        messages.success(self.request, "Book updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Edit Book"
        return ctx


class BookDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    """Remove a book from the catalog. All copies are cascade-deleted."""
    model = Book
    template_name = "catalog/book_confirm_delete.html"
    success_url = reverse_lazy("catalog:book-list")

    def form_valid(self, form):
        messages.warning(self.request, f'Book "{self.object.title}" deleted.')
        return super().form_valid(form)


# ── Book Copies Management ────────────────────────────────────────────────────

class BookCopyCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    """Add a physical copy (accession entry) for a specific book."""
    model = BookCopy
    form_class = BookCopyForm
    template_name = "catalog/copy_form.html"

    def get_initial(self):
        book = get_object_or_404(Book, pk=self.kwargs.get("book_pk"))
        return {"book": book}

    def get_success_url(self):
        return reverse_lazy("catalog:book-detail", kwargs={"pk": self.object.book.pk})

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Copy {form.instance.accession_number} added.",
        )
        return super().form_valid(form)


class BookCopyUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    """Update a copy's status (e.g., mark as MAINTENANCE)."""
    model = BookCopy
    form_class = BookCopyForm
    template_name = "catalog/copy_form.html"

    def get_success_url(self):
        return reverse_lazy("catalog:book-detail", kwargs={"pk": self.object.book.pk})

    def form_valid(self, form):
        messages.success(self.request, "Copy updated.")
        return super().form_valid(form)
