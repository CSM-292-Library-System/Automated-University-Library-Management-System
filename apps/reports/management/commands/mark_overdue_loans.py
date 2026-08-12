"""
Management Command: mark_overdue_loans
======================================
Scans all ACTIVE loans whose due_date has passed and marks them OVERDUE.
When each loan is saved as OVERDUE, the `post_save` signal in
`apps.circulation.signals` automatically creates / updates the Fine record.

Usage:
    python manage.py mark_overdue_loans

Schedule via cron (e.g., run every hour):
    0 * * * * /path/to/venv/bin/python /path/to/manage.py mark_overdue_loans

Or via Render/Railway cron jobs (see deployment docs).
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.circulation.models import Loan


class Command(BaseCommand):
    help = "Mark all past-due ACTIVE loans as OVERDUE and trigger fine creation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print affected loans without saving changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        overdue_candidates = Loan.objects.filter(
            status=Loan.Status.ACTIVE,
            due_date__lt=now,
        ).select_related("user", "book_copy__book")

        count = overdue_candidates.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No loans to mark overdue. All good!"))
            return

        self.stdout.write(f"Found {count} loan(s) to mark overdue.")

        for loan in overdue_candidates:
            days = (now - loan.due_date).days
            self.stdout.write(
                f"  Loan #{loan.pk} — {loan.book_copy.book.title} "
                f"({loan.user.username}) — {days} day(s) overdue"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes saved."))
            return

        with transaction.atomic():
            updated = overdue_candidates.update(status=Loan.Status.OVERDUE)
            # Re-fetch updated loans to trigger signals (bulk update doesn't fire signals)
            for loan in Loan.objects.filter(
                status=Loan.Status.OVERDUE,
                due_date__lt=now,
            ).select_related("user"):
                loan.save(update_fields=["status"])  # Fire post_save signal → fine creation

        self.stdout.write(
            self.style.SUCCESS(f"Successfully marked {updated} loan(s) as OVERDUE.")
        )
