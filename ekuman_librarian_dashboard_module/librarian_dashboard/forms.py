from django import forms
from catalog.models import Book, BookCopy
from accounts.models import User
from circulation.models import Fine

class BookForm(forms.ModelForm):
    copies_to_add = forms.IntegerField(
        label='Number of copies',
        min_value=0,
        required=False,
        help_text='Copies to create for a new book (or additional copies to add when editing).',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0})
    )

    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'category', 'publisher', 'publication_year', 'cover_url', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Introduction to Algorithms'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Thomas H. Cormen'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 978-0262033848'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MIT Press'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'cover_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://images.unsplash.com/...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter book summary...'}),
        }

class UserManagementForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'student_id', 'department', 'phone_number', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class FinePaymentForm(forms.Form):
    action_type = forms.ChoiceField(
        choices=[('PAY', 'Mark as Paid'), ('WAIVE', 'Waive Fine')],
        widget=forms.RadioSelect(attrs={'class': 'btn-check'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'})
    )
