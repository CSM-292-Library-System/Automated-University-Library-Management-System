"""
Circulation App — Views
=======================
Handles loan issuance, returns, renewals, and fine management.

Access matrix:
  My Loans / My Fines         → Any logged-in user (own records only)
  Issue Loan / Return Book    → Staff (librarians) only
  Pay Fine                    → Staff only
  All Loans / All Fines       → Staff only
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView

from apps.catalog.models import BookCopy
from .forms import BorrowBookForm, ReturnBookForm, PayFineForm
from .models import Fine, Loan


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_librarian


# ── Student-facing: My Loans & My Fines ──────────────────────────────────────

class MyLoanListView(LoginRequiredMixin, ListView):
    """Shows the currently logged-in user's own loan history."""
    template_name = "circulation/my_loans.html"
    context_object_name = "loans"

    def get_queryset(self):
        return (
            Loan.objects.filter(user=self.request.user)
            .select_related("book_copy__book")
            .order_by("-borrow_date")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["unpaid_fines"] = Fine.objects.filter(
            user=self.request.user, status=Fine.Status.UNPAID
        ).select_related("loan__book_copy__book")
        return ctx


# ── Staff: All Loans ──────────────────────────────────────────────────────────

class AllLoanListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """Staff view of all loans across all users, with filtering."""
    model = Loan
    template_name = "circulation/all_loans.html"
    context_object_name = "loans"
    paginate_by = 30

    def get_queryset(self):
        qs = Loan.objects.select_related(
            "user", "book_copy__book"
        ).order_by("-borrow_date")

        status = self.request.GET.get("status")
        if status in Loan.Status.values:
            qs = qs.filter(status=status)

        user_q = self.request.GET.get("user", "").strip()
        if user_q:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__username__icontains=user_q)
                | Q(user__surname__icontains=user_q)
                | Q(user__first_name__icontains=user_q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = Loan.Status.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["user_q"] = self.request.GET.get("user", "")
        return ctx


# ── Issue a Loan (Staff) ──────────────────────────────────────────────────────

class IssueLoanView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    """
    Creates a new Loan record and marks the copy as BORROWED.
    Wrapped in a DB transaction to ensure consistency.
    """
    model = Loan
    form_class = BorrowBookForm
    template_name = "circulation/issue_loan.html"
    success_url = reverse_lazy("circulation:all-loans")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pre-select copy if a book_copy_pk is passed in URL query params
        kwargs["book_copy_pk"] = self.request.GET.get("copy")
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        loan = form.save(commit=False)

        # Double-check availability inside the transaction
        copy = BookCopy.objects.select_for_update().get(pk=loan.book_copy.pk)
        if copy.status != BookCopy.Status.AVAILABLE:
            form.add_error("book_copy", "This copy was just borrowed by someone else.")
            return self.form_invalid(form)

        # Mark copy as BORROWED
        copy.status = BookCopy.Status.BORROWED
        copy.save(update_fields=["status"])
        loan.book_copy = copy
        loan.save()

        messages.success(
            self.request,
            f"Loan issued: {loan.book_copy.book.title} → {loan.user.full_name}.",
        )
        return redirect(self.success_url)


# ── Return a Book (Staff) ─────────────────────────────────────────────────────

@login_required
def return_book(request, loan_pk):
    """
    Processes a book return:
      1. Marks loan as RETURNED, sets return_date.
      2. Marks the book copy as AVAILABLE.
      3. If the loan was OVERDUE, the fine persists (already created by signal).
    """
    if not request.user.is_librarian:
        messages.error(request, "Permission denied.")
        return redirect("circulation:my-loans")

    loan = get_object_or_404(
        Loan.objects.select_related("book_copy__book", "user"),
        pk=loan_pk,
        status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE],
    )

    form = ReturnBookForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            loan.return_book()
        messages.success(
            self.request if hasattr(request, "request") else request,
            f'"{loan.book_copy.book.title}" returned by {loan.user.full_name}.',
        )
        return redirect("circulation:all-loans")

    return render(request, "circulation/return_confirm.html", {"loan": loan, "form": form})


# ── Renew a Loan (Student self-service) ──────────────────────────────────────

@login_required
def renew_loan(request, loan_pk):
    """
    Allows a borrower to renew their own active (non-overdue) loan once.
    Staff can renew any loan.
    """
    loan = get_object_or_404(Loan, pk=loan_pk)

    # Permission check
    if loan.user != request.user and not request.user.is_librarian:
        messages.error(request, "You can only renew your own loans.")
        return redirect("circulation:my-loans")

    if request.method == "POST":
        try:
            loan.renew()
            messages.success(
                request,
                f"Loan extended. New due date: {loan.due_date.strftime('%d %b %Y')}.",
            )
        except ValueError as e:
            messages.error(request, str(e))

    redirect_url = "circulation:all-loans" if request.user.is_librarian else "circulation:my-loans"
    return redirect(redirect_url)


# ── Fines ─────────────────────────────────────────────────────────────────────

class FineListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """Staff view of all fines, with filter by status."""
    model = Fine
    template_name = "circulation/fine_list.html"
    context_object_name = "fines"
    paginate_by = 30

    def get_queryset(self):
        qs = Fine.objects.select_related(
            "user", "loan__book_copy__book"
        ).order_by("-created_at")

        status = self.request.GET.get("status")
        if status in Fine.Status.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = Fine.Status.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


@login_required
def pay_fine(request, fine_pk):
    """
    Staff records a fine payment.
    Marks the Fine as PAID and records the payment timestamp.
    """
    if not request.user.is_librarian:
        messages.error(request, "Permission denied.")
        return redirect("circulation:my-loans")

    fine = get_object_or_404(Fine, pk=fine_pk, status=Fine.Status.UNPAID)
    form = PayFineForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        fine.mark_paid()
        messages.success(
            request,
            f"Fine of GHS {fine.amount} marked as paid for {fine.user.full_name}.",
        )
        return redirect("circulation:fine-list")

    return render(request, "circulation/pay_fine.html", {"fine": fine, "form": form})
