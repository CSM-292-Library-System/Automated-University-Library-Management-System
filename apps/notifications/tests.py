from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Book, BookCopy
from apps.circulation.models import Fine, Loan
from apps.notifications.models import Notification

User = get_user_model()


class LoanSignalTests(TestCase):
    """Signal fires correctly on Loan state changes (Section 5, item 1 of the checklist)."""

    def setUp(self):
        self.borrower = User.objects.create_user(
            username="student1",
            email="student1@example.edu.gh",
            identification_number="STU-001",
            password="pass1234",
            first_name="Ama",
            surname="Mensah",
        )
        book = Book.objects.create(
            title="Intro to Testing", author="J. Doe", isbn="9781440000011", category="CS", publication_year=2020
        )
        self.copy = BookCopy.objects.create(book=book, accession_number="ACC-001")
        self.loan = Loan.objects.create(
            user=self.borrower,
            book_copy=self.copy,
            borrow_date=timezone.now() - timezone.timedelta(days=10),
            due_date=timezone.now() - timezone.timedelta(days=3),
        )

    def test_mark_returned_creates_return_confirmed_notification(self):
        self.loan.return_book()

        notification = Notification.objects.get(
            loan=self.loan, notification_type=Notification.NotificationType.RETURN_CONFIRMED
        )
        self.assertEqual(notification.recipient, self.borrower)
        self.assertFalse(notification.is_read)

    def test_loan_marked_overdue_creates_overdue_notification(self):
        self.loan.status = Loan.Status.OVERDUE
        self.loan.save(update_fields=["status"])

        self.assertTrue(
            Notification.objects.filter(
                loan=self.loan, notification_type=Notification.NotificationType.OVERDUE
            ).exists()
        )

    def test_overdue_transition_also_creates_fine_issued_notification(self):
        # apps.circulation.signals auto-creates a Fine when a Loan becomes OVERDUE --
        # our Fine-created handler should react to that with its own notice.
        self.loan.status = Loan.Status.OVERDUE
        self.loan.save(update_fields=["status"])

        self.assertTrue(Fine.objects.filter(loan=self.loan).exists())
        self.assertTrue(
            Notification.objects.filter(
                loan=self.loan, notification_type=Notification.NotificationType.FINE_ISSUED
            ).exists()
        )

    def test_saving_loan_without_status_change_does_not_notify(self):
        Notification.objects.all().delete()

        self.loan.due_date = self.loan.due_date  # no status change
        self.loan.save()

        self.assertFalse(Notification.objects.filter(loan=self.loan).exists())


class RefreshOverdueLoansCommandTests(TestCase):
    """Backfill command notifies already-overdue loans and doesn't duplicate."""

    def setUp(self):
        self.borrower = User.objects.create_user(
            username="student2",
            email="student2@example.edu.gh",
            identification_number="STU-002",
            password="pass1234",
            first_name="Kofi",
            surname="Owusu",
        )
        book = Book.objects.create(
            title="Overdue Theory", author="A. Smith", isbn="9781440000028", category="CS", publication_year=2021
        )
        self.copy = BookCopy.objects.create(book=book, accession_number="ACC-002")
        # Bypass the signal path entirely (bulk_create skips post_save) so this
        # loan is OVERDUE with no notification yet -- exactly the gap the
        # backfill command exists to cover.
        self.loan = Loan.objects.bulk_create(
            [
                Loan(
                    user=self.borrower,
                    book_copy=self.copy,
                    borrow_date=timezone.now() - timezone.timedelta(days=20),
                    due_date=timezone.now() - timezone.timedelta(days=5),
                    status=Loan.Status.OVERDUE,
                )
            ]
        )[0]

    def test_command_backfills_missing_overdue_notification(self):
        call_command("refresh_overdue_loans")

        self.assertEqual(
            Notification.objects.filter(
                loan=self.loan, notification_type=Notification.NotificationType.OVERDUE
            ).count(),
            1,
        )

    def test_command_does_not_duplicate_notifications_on_repeated_runs(self):
        call_command("refresh_overdue_loans")
        call_command("refresh_overdue_loans")

        self.assertEqual(
            Notification.objects.filter(
                loan=self.loan, notification_type=Notification.NotificationType.OVERDUE
            ).count(),
            1,
        )

    def test_command_ignores_loans_that_are_not_overdue(self):
        active_copy = BookCopy.objects.create(book=self.copy.book, accession_number="ACC-003")
        active_loan = Loan.objects.create(
            user=self.borrower,
            book_copy=active_copy,
            due_date=timezone.now() + timezone.timedelta(days=7),
        )

        call_command("refresh_overdue_loans")

        self.assertFalse(Notification.objects.filter(loan=active_loan).exists())
