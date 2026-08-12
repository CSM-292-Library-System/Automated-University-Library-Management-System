"""Catalog App — Forms."""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

from .models import Book, BookCopy


class BookForm(forms.ModelForm):
    """Add / edit a book record in the catalog. Staff only."""

    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "category", "publication_year"]
        widgets = {
            "publication_year": forms.NumberInput(attrs={"min": 1, "max": 2100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "title",
            "author",
            Row(
                Column("isbn", css_class="col-md-4"),
                Column("category", css_class="col-md-4"),
                Column("publication_year", css_class="col-md-4"),
            ),
            Submit("submit", "Save Book", css_class="btn btn-primary"),
        )


class BookCopyForm(forms.ModelForm):
    """Add / edit a physical copy of a book. Staff only."""

    class Meta:
        model = BookCopy
        fields = ["book", "accession_number", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Save Copy", css_class="btn btn-primary"))


class CatalogSearchForm(forms.Form):
    """
    Public search form — available to any logged-in user.
    Searches title, author, ISBN, and category.
    """
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Title, author, ISBN, category…"}),
    )
    category = forms.CharField(required=False, label="Category")
