"""Circulation App — Forms."""

from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

from .models import Loan, Fine
from apps.catalog.models import BookCopy


class BorrowBookForm(forms.ModelForm):
    """
    Librarian issues a loan: selects user + book copy and sets due date.
    Only AVAILABLE copies are shown in the dropdown.
    """

    class Meta:
        model = Loan
        fields = ["user", "book_copy", "due_date"]
        widgets = {
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        # Optional: pre-select a specific book copy (when called from detail page)
        book_copy_pk = kwargs.pop("book_copy_pk", None)
        super().__init__(*args, **kwargs)

        # Only show available copies
        self.fields["book_copy"].queryset = BookCopy.objects.filter(
            status=BookCopy.Status.AVAILABLE
        ).select_related("book")

        if book_copy_pk:
            self.fields["book_copy"].initial = book_copy_pk

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "user",
            "book_copy",
            "due_date",
            Submit("submit", "Issue Loan", css_class="btn btn-success"),
        )

    def clean_book_copy(self):
        copy = self.cleaned_data.get("book_copy")
        if copy and copy.status != BookCopy.Status.AVAILABLE:
            raise forms.ValidationError("This copy is not currently available.")
        return copy


class ReturnBookForm(forms.Form):
    """Simple confirmation form for returning a specific loan (identified by pk)."""
    confirm = forms.BooleanField(
        required=True,
        label="I confirm that the book has been physically returned.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Confirm Return", css_class="btn btn-warning"))


class PayFineForm(forms.Form):
    """Confirmation form for marking a fine as paid."""
    confirm = forms.BooleanField(
        required=True,
        label="I confirm the fine has been collected from the borrower.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Mark as Paid", css_class="btn btn-primary"))
