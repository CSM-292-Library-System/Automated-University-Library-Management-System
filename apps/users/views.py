"""
Users App — Views
=================
Handles authentication, registration, profile, and user management.

Role-based access:
  - Students / Lecturers / Outsiders: self-service (register, view profile)
  - Staff (librarians): can list and deactivate members
  - Superusers: full access via /admin/
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, DetailView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy

from .forms import LibraryUserRegistrationForm, LibraryLoginForm, LibraryUserUpdateForm
from .models import LibraryUser


# ── Authentication ────────────────────────────────────────────────────────────

class UserLoginView(LoginView):
    """Renders the login page and authenticates users."""
    template_name = "registration/login.html"
    authentication_form = LibraryLoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """Logs out the user and redirects to login page."""
    next_page = "users:login"


class RegisterView(CreateView):
    """
    Public registration for students, lecturers, and outsiders.
    Staff accounts are created by superusers via /admin/.
    """
    model = LibraryUser
    form_class = LibraryUserRegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Account created successfully! Please log in.",
        )
        return response

    def get(self, request, *args, **kwargs):
        # Redirect already-authenticated users away from the registration page
        if request.user.is_authenticated:
            return redirect("catalog:book-list")
        return super().get(request, *args, **kwargs)


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileView(LoginRequiredMixin, DetailView):
    """Displays the logged-in user's profile, loan history, and fine summary."""
    model = LibraryUser
    template_name = "registration/profile.html"
    context_object_name = "profile_user"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["active_loans"] = user.loan_set.filter(status="ACTIVE").select_related(
            "book_copy__book"
        )
        ctx["loan_history"] = user.loan_set.exclude(status="ACTIVE").select_related(
            "book_copy__book"
        ).order_by("-borrow_date")[:20]
        ctx["unpaid_fines"] = user.fine_set.filter(status="UNPAID")
        return ctx


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Allows a user to update their own non-sensitive profile data."""
    model = LibraryUser
    form_class = LibraryUserUpdateForm
    template_name = "registration/profile_edit.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)


# ── Staff-only: Member Management ────────────────────────────────────────────

class MemberListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Lists all registered library members.
    Only accessible to staff users (librarians).
    """
    model = LibraryUser
    template_name = "registration/member_list.html"
    context_object_name = "members"
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_librarian

    def get_queryset(self):
        qs = LibraryUser.objects.all().order_by("surname", "first_name")
        role = self.request.GET.get("role")
        if role in LibraryUser.Role.values:
            qs = qs.filter(role=role)
        query = self.request.GET.get("q")
        if query:
            from django.db.models import Q
            qs = qs.filter(
                Q(first_name__icontains=query)
                | Q(surname__icontains=query)
                | Q(username__icontains=query)
                | Q(identification_number__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["roles"] = LibraryUser.Role.choices
        ctx["current_role"] = self.request.GET.get("role", "")
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class MemberDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Staff view of a specific member's full profile, loans, and fines.
    """
    model = LibraryUser
    template_name = "registration/member_detail.html"
    context_object_name = "member"

    def test_func(self):
        return self.request.user.is_librarian

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        member = self.get_object()
        ctx["loans"] = member.loan_set.select_related("book_copy__book").order_by("-borrow_date")
        ctx["fines"] = member.fine_set.order_by("-created_at")
        return ctx


@login_required
def deactivate_member(request, pk):
    """
    Staff can deactivate (soft-delete) a member account.
    Deactivated users can no longer log in.
    POST-only for safety.
    """
    if not request.user.is_librarian:
        messages.error(request, "Permission denied.")
        return redirect("users:member-list")

    member = get_object_or_404(LibraryUser, pk=pk)

    if request.method == "POST":
        member.is_active = not member.is_active
        member.save(update_fields=["is_active"])
        action = "activated" if member.is_active else "deactivated"
        messages.success(request, f"Account {action} for {member.full_name}.")

    return redirect("users:member-detail", pk=pk)
