"""
Notifications App — Django Signals
====================================
Fires on-site notices immediately on the relevant Loan/Fine state changes
instead of polling:

  - Loan transitions to OVERDUE  -> OVERDUE notification
  - Loan transitions to RETURNED -> RETURN_CONFIRMED notification
  - A Fine is created            -> FINE_ISSUED notification

Connected from NotificationsConfig.ready() (not at import time) and looked
up via apps.get_model() rather than `from apps.circulation.models import
Loan, Fine`, so this module doesn't need circulation to already be loaded
when it's imported -- Django guarantees every INSTALLED_APPS app is loaded
by the time ready() runs, avoiding app-loading-order/circular-import issues.

Note on apps.circulation.management.commands.mark_overdue_loans: it marks
loans OVERDUE via `loan.save(update_fields=["status"])` in a loop
specifically so that per-instance signals fire (it explicitly avoids
QuerySet.update(), which bypasses signals) -- see that command's own
comments. That means this OVERDUE handler fires correctly for it without
any extra wiring on our side.
"""

from django.apps import apps
from django.db.models.signals import post_save, pre_save

from .models import Notification


def connect():
    Loan = apps.get_model("circulation", "Loan")
    Fine = apps.get_model("circulation", "Fine")

    pre_save.connect(_stash_previous_status, sender=Loan, dispatch_uid="notifications_stash_loan_status")
    post_save.connect(_on_loan_saved, sender=Loan, dispatch_uid="notifications_on_loan_saved")
    post_save.connect(_on_fine_created, sender=Fine, dispatch_uid="notifications_on_fine_created")


def _stash_previous_status(sender, instance, **kwargs):
    """Record the loan's pre-save status so post_save can detect a transition."""
    if instance.pk:
        try:
            instance._previous_status = sender.objects.only("status").get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


def _on_loan_saved(sender, instance, created, **kwargs):
    if created:
        return

    previous_status = getattr(instance, "_previous_status", None)
    if previous_status == instance.status:
        return

    if instance.status == sender.Status.OVERDUE:
        _notify_once(
            recipient=instance.user,
            loan=instance,
            notification_type=Notification.NotificationType.OVERDUE,
            message=(
                f"Your loan of {instance.book_copy} was due on "
                f"{instance.due_date:%d %b %Y} and is now overdue."
            ),
        )
    elif instance.status == sender.Status.RETURNED:
        Notification.objects.create(
            recipient=instance.user,
            loan=instance,
            notification_type=Notification.NotificationType.RETURN_CONFIRMED,
            message=f"Your loan of {instance.book_copy} has been marked returned.",
        )


def _on_fine_created(sender, instance, created, **kwargs):
    if not created:
        return

    Notification.objects.create(
        recipient=instance.user,
        loan=instance.loan,
        notification_type=Notification.NotificationType.FINE_ISSUED,
        message=f"A fine of GHS {instance.amount} has been issued for your overdue loan.",
    )


def _notify_once(*, recipient, loan, notification_type, message):
    """Avoid a duplicate notice if this loan/type pair was already notified."""
    already_notified = Notification.objects.filter(loan=loan, notification_type=notification_type).exists()
    if already_notified:
        return
    Notification.objects.create(
        recipient=recipient, loan=loan, notification_type=notification_type, message=message
    )
