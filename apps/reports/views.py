"""
Reports App — Views
===================
Provides staff-only reporting dashboards.

Reports available:
  1. Overdue Report         — all currently overdue loans
  2. Borrowing Statistics   — top borrowed books, loans by role
  3. Inventory Report       — copy status breakdown per book
  4. Fine Summary           — total collected vs outstanding fines
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from django.views.generic import TemplateView

from apps.catalog.models import Book, BookCopy
from apps.circulation.models import Fine, Loan
from apps.users.models import LibraryUser


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_librarian


class OverdueReportView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    """
    Lists every loan that is currently ACTIVE and past its due date.
    Also covers loans already marked OVERDUE in the database.
    """
    template_name = "reports/overdue_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()

        overdue_loans = (
            Loan.objects.filter(
                Q(status=Loan.Status.OVERDUE)
                | Q(status=Loan.Status.ACTIVE, due_date__lt=now)
            )
            .select_related("user", "book_copy__book")
            .order_by("due_date")
        )

        ctx["overdue_loans"] = overdue_loans
        ctx["overdue_count"] = overdue_loans.count()
        ctx["generated_at"] = now
        return ctx


class BorrowingStatisticsView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    """
    Aggregated borrowing statistics:
      - Most borrowed books (top 10)
      - Loans grouped by user role
      - Monthly loan trend (last 6 months)
    """
    template_name = "reports/borrowing_stats.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Top 10 most borrowed books
        ctx["top_books"] = (
            Book.objects.annotate(loan_count=Count("copies__loan_set"))
            .order_by("-loan_count")[:10]
        )

        # Loans by user role
        ctx["loans_by_role"] = (
            Loan.objects.values("user__role")
            .annotate(total=Count("id"))
            .order_by("-total")
        )

        # Total loans summary
        ctx["total_loans"] = Loan.objects.count()
        ctx["active_loans"] = Loan.objects.filter(status=Loan.Status.ACTIVE).count()
        ctx["returned_loans"] = Loan.objects.filter(status=Loan.Status.RETURNED).count()
        ctx["overdue_loans_count"] = Loan.objects.filter(status=Loan.Status.OVERDUE).count()

        ctx["generated_at"] = timezone.now()
        return ctx


class InventoryReportView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    """
    Shows inventory status for the whole catalog:
      - Total books, total copies
      - Copies by status (AVAILABLE / BORROWED / MAINTENANCE)
    """
    template_name = "reports/inventory_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        status_counts = BookCopy.objects.values("status").annotate(total=Count("id"))
        ctx["status_breakdown"] = {row["status"]: row["total"] for row in status_counts}
        ctx["total_books"] = Book.objects.count()
        ctx["total_copies"] = BookCopy.objects.count()

        # Books with zero available copies (needs restocking attention)
        ctx["no_available_copies"] = (
            Book.objects.annotate(
                available=Count("copies", filter=Q(copies__status=BookCopy.Status.AVAILABLE))
            ).filter(available=0)
        )

        ctx["generated_at"] = timezone.now()
        return ctx


class FineSummaryView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    """
    Financial summary of fines:
      - Total outstanding (UNPAID) fines
      - Total collected (PAID) fines
      - Users with the most outstanding fines
    """
    template_name = "reports/fine_summary.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["total_unpaid"] = (
            Fine.objects.filter(status=Fine.Status.UNPAID)
            .aggregate(t=Sum("amount"))["t"] or 0
        )
        ctx["total_paid"] = (
            Fine.objects.filter(status=Fine.Status.PAID)
            .aggregate(t=Sum("amount"))["t"] or 0
        )
        ctx["top_debtors"] = (
            LibraryUser.objects.annotate(
                owed=Sum("fine_set__amount", filter=Q(fine_set__status=Fine.Status.UNPAID))
            ).filter(owed__gt=0)
            .order_by("-owed")[:10]
        )
        ctx["generated_at"] = timezone.now()
        return ctx
