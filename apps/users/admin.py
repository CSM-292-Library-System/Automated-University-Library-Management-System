"""Users App — Django Admin Registration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserEditForm, LibraryUserRegistrationForm
from .models import LibraryUser


@admin.register(LibraryUser)
class LibraryUserAdmin(UserAdmin):
    """
    Full Django admin integration for LibraryUser.
    Librarians (is_staff=True) see this; superusers see everything.
    """

    add_form = LibraryUserRegistrationForm
    form = AdminUserEditForm
    model = LibraryUser

    list_display = [
        "username",
        "full_name",
        "email",
        "role",
        "identification_number",
        "is_active",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "first_name", "surname", "email", "identification_number"]
    ordering = ["surname", "first_name"]
    readonly_fields = ["date_joined", "last_login"]

    fieldsets = (
        ("Account", {"fields": ("username", "password")}),
        ("Personal Info", {
            "fields": ("first_name", "other_names", "surname", "email", "phone_number")
        }),
        ("Library Info", {"fields": ("role", "identification_number")}),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "first_name", "surname",
                "identification_number", "role",
                "password1", "password2",
            ),
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "Full Name"
