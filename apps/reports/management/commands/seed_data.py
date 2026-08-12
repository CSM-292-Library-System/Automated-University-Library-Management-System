"""
Management Command: seed_data
==============================
Populates the database with realistic sample data for testing and demo.

Creates:
  - 1 superuser (librarian)
  - 5 students, 2 lecturers, 1 outsider
  - 15 books across 5 categories
  - 2-3 copies per book
  - Several active and returned loans
  - 2 overdue loans with fines

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear  (drops all existing data first)
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import LibraryUser
from apps.catalog.models import Book, BookCopy
from apps.circulation.models import Loan, Fine


BOOKS_DATA = [
    ("Introduction to Algorithms", "Cormen et al.", "9780262033848", "Computer Science", 2022),
    ("Clean Code", "Robert C. Martin", "9780132350884", "Computer Science", 2008),
    ("Database System Concepts", "Silberschatz et al.", "9780078022159", "Computer Science", 2019),
    ("Calculus: Early Transcendentals", "James Stewart", "9781285741550", "Mathematics", 2015),
    ("Linear Algebra and Its Applications", "David Lay", "9780321982384", "Mathematics", 2015),
    ("Principles of Economics", "N. Gregory Mankiw", "9781305585126", "Economics", 2018),
    ("Microeconomic Theory", "Mas-Colell et al.", "9780195073409", "Economics", 1995),
    ("Organic Chemistry", "Paula Bruice", "9780134042282", "Chemistry", 2016),
    ("Biochemistry", "Jeremy Berg et al.", "9781319114657", "Chemistry", 2019),
    ("Physics for Scientists and Engineers", "Serway & Jewett", "9781337553278", "Physics", 2018),
    ("University Physics", "Young & Freedman", "9780135159552", "Physics", 2019),
    ("The Art of War", "Sun Tzu", "9780195014761", "Literature", 500),
    ("Things Fall Apart", "Chinua Achebe", "9780385474542", "Literature", 1958),
    ("African Politics in Comparative Perspective", "Goran Hyden", "9780521678230", "Political Science", 2006),
    ("Research Methods in Education", "Cohen et al.", "9780415583367", "Education", 2018),
]


class Command(BaseCommand):
    help = "Seed the database with sample data for development and demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding (DESTRUCTIVE).",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data…"))
            Fine.objects.all().delete()
            Loan.objects.all().delete()
            BookCopy.objects.all().delete()
            Book.objects.all().delete()
            LibraryUser.objects.all().delete()

        # ── Users ─────────────────────────────────────────────────────────
        self.stdout.write("Creating users…")

        librarian, _ = LibraryUser.objects.get_or_create(
            username="librarian",
            defaults=dict(
                email="librarian@university.edu.gh",
                first_name="Head",
                surname="Librarian",
                identification_number="STAFF-001",
                role=LibraryUser.Role.STAFF,
                is_staff=True,
                is_superuser=True,
            ),
        )
        librarian.set_password("library@2024")
        librarian.save()

        students = []
        for i in range(1, 6):
            u, _ = LibraryUser.objects.get_or_create(
                username=f"student{i:02d}",
                defaults=dict(
                    email=f"student{i:02d}@university.edu.gh",
                    first_name=f"Student",
                    surname=f"Mensah{i}",
                    identification_number=f"UG-2024-{i:04d}",
                    role=LibraryUser.Role.STUDENT,
                ),
            )
            u.set_password("pass1234")
            u.save()
            students.append(u)

        # ── Books & Copies ────────────────────────────────────────────────
        self.stdout.write("Creating books and copies…")

        copies_pool = []
        for i, (title, author, isbn, category, year) in enumerate(BOOKS_DATA, start=1):
            book, _ = Book.objects.get_or_create(isbn=isbn, defaults=dict(
                title=title, author=author, category=category, publication_year=year
            ))
            for j in range(1, random.randint(2, 4)):
                acc = f"ACC-{i:04d}-{j}"
                copy, _ = BookCopy.objects.get_or_create(
                    accession_number=acc,
                    defaults={"book": book, "status": BookCopy.Status.AVAILABLE},
                )
                copies_pool.append(copy)

        # ── Loans ─────────────────────────────────────────────────────────
        self.stdout.write("Creating loans…")

        available_copies = [c for c in copies_pool if c.status == BookCopy.Status.AVAILABLE]
        random.shuffle(available_copies)

        # 3 active loans
        for i in range(min(3, len(available_copies))):
            copy = available_copies.pop()
            student = random.choice(students)
            Loan.objects.create(
                user=student,
                book_copy=copy,
                due_date=timezone.now() + timedelta(days=random.randint(3, 14)),
                status=Loan.Status.ACTIVE,
            )
            copy.status = BookCopy.Status.BORROWED
            copy.save()

        # 2 overdue loans (with fines)
        for i in range(min(2, len(available_copies))):
            copy = available_copies.pop()
            student = random.choice(students)
            overdue_loan = Loan.objects.create(
                user=student,
                book_copy=copy,
                borrow_date=timezone.now() - timedelta(days=21),
                due_date=timezone.now() - timedelta(days=7),
                status=Loan.Status.OVERDUE,
            )
            copy.status = BookCopy.Status.BORROWED
            copy.save()
            # Fine is created by signal — but seed forces it here too for safety
            Fine.objects.get_or_create(
                loan=overdue_loan,
                defaults=dict(
                    user=student,
                    amount=round(7 * 0.50, 2),
                    status=Fine.Status.UNPAID,
                ),
            )

        # 2 returned loans
        for i in range(min(2, len(available_copies))):
            copy = available_copies.pop()
            student = random.choice(students)
            Loan.objects.create(
                user=student,
                book_copy=copy,
                borrow_date=timezone.now() - timedelta(days=30),
                due_date=timezone.now() - timedelta(days=16),
                return_date=timezone.now() - timedelta(days=17),
                status=Loan.Status.RETURNED,
            )

        self.stdout.write(self.style.SUCCESS("\n✓ Seed data created successfully!"))
        self.stdout.write("  Superuser:  username=librarian  password=library@2024")
        self.stdout.write("  Students:   student01–student05  password=pass1234")
