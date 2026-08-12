"""
Management Command: send_overdue_alerts
========================================
Prints (or emails) an overdue alert for each borrower with overdue loans.

This command is designed to be run daily via cron or a task scheduler.
Currently it writes console output. Plugging in Django's email backend
(e.g. SMTP or SendGrid) requires only uncommenting the email block below.

Usage:
    python manage.py send_overdue_alerts
    python manage.py send_overdue_alerts --dry-run

Cron example (daily at 8 AM):
    0 8 * * * /path/to/venv/bin/python /path/to/manage.py send_overdue_alerts
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
# from django.core.mail import send_mail  # Uncomment when email is configured

from apps.circulation.models import Loan


class Command(BaseCommand):
    help = "Send overdue notifications to borrowers with past-due loans."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print alerts without sending emails.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        overdue_loans = (
            Loan.objects.filter(
                Q(status=Loan.Status.OVERDUE)
                | Q(status=Loan.Status.ACTIVE, due_date__lt=now)
            )
            .select_related("user", "book_copy__book")
            .order_by("user__surname", "user__first_name")
        )

        if not overdue_loans.exists():
            self.stdout.write(self.style.SUCCESS("No overdue loans. No alerts needed."))
            return

        # Group by user
        user_loans: dict = {}
        for loan in overdue_loans:
            user_loans.setdefault(loan.user, []).append(loan)

        alerts_sent = 0
        for user, loans in user_loans.items():
            loan_lines = "\n".join(
                f"  - {l.book_copy.book.title} (due {l.due_date.strftime('%d %b %Y')})"
                for l in loans
            )
            message = (
                f"Dear {user.full_name},\n\n"
                f"You have {len(loans)} overdue book(s) at the University Library:\n"
                f"{loan_lines}\n\n"
                f"Please return them as soon as possible to avoid further fines.\n\n"
                f"University Library Team"
            )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"\n[DRY RUN] Alert for {user.email}:\n{message}")
                )
            else:
                self.stdout.write(f"Sending alert to {user.email}…")
                # ── Uncomment below when SMTP / email backend is configured ──
                # send_mail(
                #     subject="Library Overdue Notice",
                #     message=message,
                #     from_email="library@university.edu.gh",
                #     recipient_list=[user.email],
                #     fail_silently=False,
                # )
                # ── For now, log to stdout ────────────────────────────────────
                self.stdout.write(self.style.SUCCESS(f"  ✓ Alert logged for {user.email}"))
                alerts_sent += 1

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"\nDone. {alerts_sent} alert(s) sent.")
            )
