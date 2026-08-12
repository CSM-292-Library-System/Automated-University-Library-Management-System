"""
Catalog App — Models
====================
Maps to the `books` and `book_copies` tables in the PostgreSQL schema.

books       — bibliographic metadata (one record per unique title/ISBN)
book_copies — physical copies of a book (one record per barcode/accession tag)

A book can have many copies; a copy belongs to exactly one book (CASCADE delete).
"""

from django.db import models


class Book(models.Model):
    """
    DB table: books
    ──────────────────────────────────────────────────────────────────────
    id                SERIAL PK
    title             VARCHAR(255) NOT NULL
    author            VARCHAR(255) NOT NULL
    isbn              VARCHAR(13)  UNIQUE NOT NULL
    category          VARCHAR(100) NOT NULL
    publication_year  INT CHECK > 0
    created_at        TIMESTAMPTZ  DEFAULT NOW()
    ──────────────────────────────────────────────────────────────────────
    """

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True, verbose_name="ISBN")
    category = models.CharField(max_length=100)
    publication_year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "books"
        ordering = ["title"]
        indexes = [
            models.Index(fields=["isbn"], name="idx_books_isbn"),
        ]
        verbose_name = "Book"
        verbose_name_plural = "Books"

    @property
    def available_copies_count(self):
        """Returns the number of copies currently available to borrow."""
        return self.copies.filter(status=BookCopy.Status.AVAILABLE).count()

    @property
    def total_copies_count(self):
        return self.copies.count()

    def __str__(self):
        return f"{self.title} — {self.author} (ISBN: {self.isbn})"


class BookCopy(models.Model):
    """
    DB table: book_copies
    ──────────────────────────────────────────────────────────────────────
    id                SERIAL PK
    book_id           INT FK → books(id)  ON DELETE CASCADE
    accession_number  VARCHAR(50) UNIQUE NOT NULL  (barcode / RFID tag)
    status            VARCHAR(20) DEFAULT 'AVAILABLE'
                        CHECK IN ('AVAILABLE', 'BORROWED', 'MAINTENANCE')
    ──────────────────────────────────────────────────────────────────────
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        BORROWED = "BORROWED", "Borrowed"
        MAINTENANCE = "MAINTENANCE", "Under Maintenance"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    accession_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    class Meta:
        db_table = "book_copies"
        ordering = ["accession_number"]
        indexes = [
            models.Index(fields=["accession_number"], name="idx_copies_accession"),
        ]
        verbose_name = "Book Copy"
        verbose_name_plural = "Book Copies"

    def __str__(self):
        return f"{self.accession_number} — {self.book.title} [{self.status}]"
