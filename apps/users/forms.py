"""Users App — Forms."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML

from .models import LibraryUser


class LibraryUserRegistrationForm(UserCreationForm):
    """
    Registration form for new library members.
    Students and outsiders self-register; staff roles are assigned by admin.
    """

    class Meta:
        model = LibraryUser
        fields = [
            "username",
            "first_name",
            "other_names",
            "surname",
            "email",
            "phone_number",
            "identification_number",
            "role",
            "password1",
            "password2",
        ]
        widgets = {
            "role": forms.Select(
                choices=[
                    (LibraryUser.Role.STUDENT, "Student"),
                    (LibraryUser.Role.LECTURER, "Lecturer"),
                    (LibraryUser.Role.OUTSIDER, "Outsider"),
                ]
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-md-4"),
                Column("other_names", css_class="col-md-4"),
                Column("surname", css_class="col-md-4"),
            ),
            Row(
                Column("username", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            Row(
                Column("phone_number", css_class="col-md-6"),
                Column("identification_number", css_class="col-md-6"),
            ),
            "role",
            Row(
                Column("password1", css_class="col-md-6"),
                Column("password2", css_class="col-md-6"),
            ),
            Submit("submit", "Register", css_class="btn btn-primary w-100 mt-3"),
        )


class LibraryLoginForm(AuthenticationForm):
    """Styled login form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "username",
            "password",
            Submit("submit", "Sign In", css_class="btn btn-primary w-100 mt-2"),
        )


class LibraryUserUpdateForm(forms.ModelForm):
    """Profile update form (non-sensitive fields)."""

    class Meta:
        model = LibraryUser
        fields = ["first_name", "other_names", "surname", "email", "phone_number"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Update Profile", css_class="btn btn-success"))


class AdminUserEditForm(UserChangeForm):
    """
    Admin form for editing any user field, used in Django Admin.
    Excludes password — handled separately via Django admin's built-in flow.
    """

    class Meta:
        model = LibraryUser
        fields = "__all__"
