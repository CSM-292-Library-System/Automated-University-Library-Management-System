"""
Users App — Models
==================
Maps directly to the `library_users` table in the PostgreSQL schema.

Django's AbstractBaseUser + PermissionsMixin is used so that we keep the
native Django authentication machinery (sessions, password hashing, admin)
while matching the columns defined in the SQL schema exactly.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class LibraryUserManager(BaseUserManager):
    """Custom manager so we can create users with our fields."""

    def create_user(self, username, email, identification_number, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not identification_number:
            raise ValueError("Identification number is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(
            username=username,
            email=email,
            identification_number=identification_number,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, identification_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", LibraryUser.Role.STAFF)
        return self.create_user(username, email, identification_number, password, **extra_fields)


class LibraryUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.

    DB table: library_users
    ─────────────────────────────────────────────────────────────────────────
    id                  SERIAL PK
    username            VARCHAR(150) UNIQUE NOT NULL
    email               VARCHAR(255) UNIQUE NOT NULL
    first_name          VARCHAR(150) NOT NULL
    other_names         VARCHAR(150)
    surname             VARCHAR(150) NOT NULL
    role                VARCHAR(20)  DEFAULT 'STUDENT'
    phone_number        VARCHAR(25)
    identification_number VARCHAR(50) UNIQUE NOT NULL
    is_active           BOOLEAN      DEFAULT TRUE
    date_joined         TIMESTAMPTZ  DEFAULT NOW()
    ─────────────────────────────────────────────────────────────────────────
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        LECTURER = "LECTURER", "Lecturer"
        OUTSIDER = "OUTSIDER", "Outsider"
        STAFF = "STAFF", "Staff"

    # ── Core identity ────────────────────────────────────────────────────
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=True)

    # ── Name fields ──────────────────────────────────────────────────────
    first_name = models.CharField(max_length=150)
    other_names = models.CharField(max_length=150, blank=True, default="")
    surname = models.CharField(max_length=150)

    # ── Role ─────────────────────────────────────────────────────────────
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    # ── Contact ──────────────────────────────────────────────────────────
    phone_number = models.CharField(max_length=25, blank=True, default="")

    # ── Identification (Student ID / Staff ID / National ID) ─────────────
    identification_number = models.CharField(max_length=50, unique=True)

    # ── Status & audit ───────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access
    date_joined = models.DateTimeField(default=timezone.now)

    objects = LibraryUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "identification_number"]

    class Meta:
        db_table = "library_users"
        ordering = ["surname", "first_name"]
        indexes = [
            models.Index(fields=["role"], name="idx_users_role"),
        ]
        verbose_name = "Library User"
        verbose_name_plural = "Library Users"

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def full_name(self):
        parts = [self.first_name, self.other_names, self.surname]
        return " ".join(p for p in parts if p).strip()

    @property
    def is_librarian(self):
        """Returns True if the user has librarian / staff privileges."""
        return self.role == self.Role.STAFF or self.is_staff

    @property
    def unpaid_fines_total(self):
        """Returns the sum of all unpaid fines for this user."""
        from apps.circulation.models import Fine
        result = Fine.objects.filter(user=self, status=Fine.Status.UNPAID).aggregate(
            total=models.Sum("amount")
        )
        return result["total"] or 0

    def __str__(self):
        return f"{self.full_name} ({self.username}) — {self.role}"
