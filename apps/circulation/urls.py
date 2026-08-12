"""Circulation App — URL Configuration."""

from django.urls import path
from . import views

app_name = "circulation"

urlpatterns = [
    # ── Student self-service ──────────────────────────────────────────────
    path("my-loans/",              views.MyLoanListView.as_view(), name="my-loans"),
    path("loans/<int:loan_pk>/renew/", views.renew_loan,           name="renew-loan"),

    # ── Staff: Loan management ────────────────────────────────────────────
    path("loans/",                     views.AllLoanListView.as_view(), name="all-loans"),
    path("loans/issue/",               views.IssueLoanView.as_view(),   name="issue-loan"),
    path("loans/<int:loan_pk>/return/", views.return_book,              name="return-book"),

    # ── Staff: Fine management ────────────────────────────────────────────
    path("fines/",                   views.FineListView.as_view(), name="fine-list"),
    path("fines/<int:fine_pk>/pay/", views.pay_fine,               name="pay-fine"),
]
