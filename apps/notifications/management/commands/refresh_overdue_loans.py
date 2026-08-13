"""
Management Command: refresh_overdue_loans
==========================================
Backfill / catch-up pass: creates OVERDUE notifications for any loan that is
already OVERDUE but doesn't have one yet.

This deliberately does NOT scan due_date to decide what counts as overdue --
that scan already exists as `apps.reports.management.commands
.mark_overdue_loans`, which is circulation's own shared overdue-detection
logic (it flips Loan.status to OVERDUE one instance at a time specifically
so per-row signals fire). Duplicating that scan here would be exactly the
"reimplemented overdue math in two places" bug the architecture doc warns
about.

Instead, `apps.notifications.signals` reacts to that command's Loan saves in
real time and creates the OVERDUE notification immediately -- no polling
needed for the normal path. This command exists only as a safety net for
loans that became OVERDUE without the signal firing (e.g. a loan that was
already OVERDUE before this app existed, or was bulk-updated via
QuerySet.update() somewhere, which bypasses signals).

Usage:
    python manage.py refresh_overdue_loans

Safe to run repeatedly / on a schedule -- it only ever creates the missing
notification once per loan.
"""

from django.apps import apps
from django.core.management.base import BaseCommand

from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Backfill OVERDUE notifications for already-overdue loans that don't have one yet."

    def handle(self, *args, **options):
        Loan = apps.get_model("circulation", "Loan")

        already_notified_loan_ids = Notification.objects.filter(
            notification_type=Notification.NotificationType.OVERDUE
        ).values_list("loan_id", flat=True)

        missing = Loan.objects.filter(status=Loan.Status.OVERDUE).exclude(pk__in=already_notified_loan_ids)

        created_count = 0
        for loan in missing:
            Notification.objects.create(
                recipient=loan.user,
                loan=loan,
                notification_type=Notification.NotificationType.OVERDUE,
                message=(
                    f"Your loan of {loan.book_copy} was due on "
                    f"{loan.due_date:%d %b %Y} and is now overdue."
                ),
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled {created_count} overdue notification(s)."))
