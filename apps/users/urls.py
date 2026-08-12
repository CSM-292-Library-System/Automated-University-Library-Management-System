"""Users App — URL Configuration."""

from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    # ── Authentication ────────────────────────────────────────────────────
    path("login/",    views.UserLoginView.as_view(),  name="login"),
    path("logout/",   views.UserLogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(),   name="register"),

    # ── Profile (self) ────────────────────────────────────────────────────
    path("profile/",       views.ProfileView.as_view(),       name="profile"),
    path("profile/edit/",  views.ProfileUpdateView.as_view(), name="profile-edit"),

    # ── Staff: Member Management ──────────────────────────────────────────
    path("members/",                  views.MemberListView.as_view(),   name="member-list"),
    path("members/<int:pk>/",         views.MemberDetailView.as_view(), name="member-detail"),
    path("members/<int:pk>/toggle/",  views.deactivate_member,          name="member-toggle"),
]
