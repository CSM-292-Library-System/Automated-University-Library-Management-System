"""Circulation App — Django Admin."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Fine, Loan


class FineInline(admin.StackedInline):
    """Show a loan's fine inline on the Loan admin page."""
    model = Fine
    extra = 0
    readonly_fields = ["created_at", "paid_at"]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "book_title", "borrow_date", "due_date", "return_date",
        "status", "is_overdue_display",
    ]
    list_filter = ["status"]
    search_fields = [
        "user__username", "user__surname", "book_copy__book__title",
        "book_copy__accession_number",
    ]
    readonly_fields = ["borrow_date", "is_overdue_display"]
    raw_id_fields = ["user", "book_copy"]
    inlines = [FineInline]
    ordering = ["-borrow_date"]

    def book_title(self, obj):
        return obj.book_copy.book.title
    book_title.short_description = "Book"

    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color:red;font-weight:bold;">⚠ OVERDUE</span>')
        return "—"
    is_overdue_display.short_description = "Overdue?"


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "amount", "status", "created_at", "paid_at"]
    list_filter = ["status"]
    search_fields = ["user__username", "user__surname", "loan__id"]
    readonly_fields = ["created_at", "paid_at"]
    raw_id_fields = ["loan", "user"]
    ordering = ["-created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "loan__book_copy__book")
