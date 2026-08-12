"""Catalog App — Django Admin Registration."""

from django.contrib import admin

from .models import Book, BookCopy


class BookCopyInline(admin.TabularInline):
    """Show copies inline on the Book admin page."""
    model = BookCopy
    extra = 1
    fields = ["accession_number", "status"]
    readonly_fields = []


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "isbn", "category", "publication_year", "available_copies_count"]
    list_filter = ["category", "publication_year"]
    search_fields = ["title", "author", "isbn", "category"]
    ordering = ["title"]
    inlines = [BookCopyInline]

    def available_copies_count(self, obj):
        return obj.available_copies_count
    available_copies_count.short_description = "Available"


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ["accession_number", "book", "status"]
    list_filter = ["status"]
    search_fields = ["accession_number", "book__title", "book__isbn"]
    ordering = ["accession_number"]
    autocomplete_fields = ["book"]
