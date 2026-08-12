"""
Circulation App — Models
========================
Maps to `loans` and `fines` tables in the PostgreSQL schema.

Business Rules (from the project plan):
  - Default loan period: DEFAULT_LOAN_DAYS (configured in settings, default 14)
  - A fine is created automatically when a loan becomes OVERDUE
  - Fine rate: FINE_PER_DAY per calendar day overdue (default 0.50 GHS)
  - A copy cannot be borrowed if it is BORROWED or MAINTENANCE
  - A user with unpaid fines can still borrow (warn, do not block — configurable)

Relationships:
  loans → library_users   (RESTRICT delete — no deleting users with loans)
  loans → book_copies     (RESTRICT delete — no deleting copies with loans)
  fines → loans           (CASCADE — fine deleted when loan deleted)
  fines → library_users   (CASCADE — fine deleted when user deleted)
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


def default_due_date():
    """Returns now + DEFAULT_LOAN_DAYS as the default due date."""
    days = getattr(settings, "DEFAULT_LOAN_DAYS", 14)
    return timezone.now() + timedelta(days=days)


class Loan(models.Model):
    """
    DB table: loans
    ──────────────────────────────────────────────────────────────────────
    id              SERIAL PK
    user_id         INT FK → library_users(id) ON DELETE RESTRICT
    book_copy_id    INT FK → book_copies(id)   ON DELETE RESTRICT
    borrow_date     TIMESTAMPTZ DEFAULT NOW()
    due_date        TIMESTAMPTZ NOT NULL
    return_date     TIMESTAMPTZ (NULL until returned)
    status          VARCHAR(20) DEFAULT 'ACTIVE'
                      CHECK IN ('ACTIVE', 'RETURNED', 'OVERDUE')
    ──────────────────────────────────────────────────────────────────────
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RETURNED = "RETURNED", "Returned"
        OVERDUE = "OVERDUE", "Overdue"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="loan_set",
    )
    book_copy = models.ForeignKey(
        "catalog.BookCopy",
        on_delete=models.RESTRICT,
        related_name="loan_set",
    )
    borrow_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(default=default_due_date)
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        db_table = "loans"
        ordering = ["-borrow_date"]
        indexes = [
            models.Index(fields=["user_id"], name="idx_loans_user"),
            models.Index(fields=["status"], name="idx_loans_status"),
        ]
        verbose_name = "Loan"
        verbose_name_plural = "Loans"

    # ── Business logic ────────────────────────────────────────────────────

    @property
    def is_overdue(self):
        """True if the loan is active and past its due date."""
        return self.status == self.Status.ACTIVE and timezone.now() > self.due_date

    @property
    def days_overdue(self):
        """Number of full calendar days past due date (0 if not overdue)."""
        if not self.is_overdue:
            return 0
        delta = timezone.now() - self.due_date
        return delta.days

    @property
    def calculated_fine(self):
        """Fine amount based on days overdue × FINE_PER_DAY rate."""
        rate = getattr(settings, "FINE_PER_DAY", 0.50)
        return round(self.days_overdue * rate, 2)

    def return_book(self):
        """
        Mark this loan as RETURNED, set return_date, and release the copy.
        Caller is responsible for committing the transaction.
        """
        from apps.catalog.models import BookCopy
        self.return_date = timezone.now()
        self.status = self.Status.RETURNED
        self.save(update_fields=["return_date", "status"])
        self.book_copy.status = BookCopy.Status.AVAILABLE
        self.book_copy.save(update_fields=["status"])

    def renew(self, extra_days=None):
        """
        Extend the due_date by DEFAULT_LOAN_DAYS (or a custom number of days).
        Only ACTIVE loans can be renewed.
        Raises ValueError if the loan is OVERDUE or RETURNED.
        """
        if self.status != self.Status.ACTIVE:
            raise ValueError("Only active loans can be renewed.")
        if self.is_overdue:
            raise ValueError("Overdue loans cannot be renewed without clearing the fine first.")
        days = extra_days or getattr(settings, "DEFAULT_LOAN_DAYS", 14)
        self.due_date = self.due_date + timedelta(days=days)
        self.save(update_fields=["due_date"])

    def __str__(self):
        return (
            f"Loan #{self.pk} — {self.book_copy.book.title} "
            f"({self.user.username}) [{self.status}]"
        )


class Fine(models.Model):
    """
    DB table: fines
    ──────────────────────────────────────────────────────────────────────
    id          SERIAL PK
    loan_id     INT UNIQUE FK → loans(id) ON DELETE CASCADE
    user_id     INT FK → library_users(id) ON DELETE CASCADE
    amount      DECIMAL(10,2) CHECK >= 0
    status      VARCHAR(20) DEFAULT 'UNPAID'  CHECK IN ('UNPAID', 'PAID')
    created_at  TIMESTAMPTZ DEFAULT NOW()
    paid_at     TIMESTAMPTZ (NULL until paid)
    ──────────────────────────────────────────────────────────────────────
    Note: loan_id is UNIQUE — one fine record per loan (updated if deeper).
    """

    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"

    loan = models.OneToOneField(
        Loan,
        on_delete=models.CASCADE,
        related_name="fine",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fine_set",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "fines"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"], name="idx_fines_user"),
        ]
        verbose_name = "Fine"
        verbose_name_plural = "Fines"

    def mark_paid(self):
        """Mark this fine as PAID and record the payment timestamp."""
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])

    def __str__(self):
        return f"Fine #{self.pk} — {self.user.username} GHS {self.amount} [{self.status}]"
