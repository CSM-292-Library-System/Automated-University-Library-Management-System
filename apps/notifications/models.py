"""
Notifications App — Models
===========================
On-site notices for borrowers: overdue alerts, due-soon reminders, return
confirmations, and fine notices.

Relationships:
  notifications → library_users  (CASCADE — notification deleted with user)
  notifications → loans          (CASCADE — notification deleted with loan)
"""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    DB table: notifications
    ──────────────────────────────────────────────────────────────────────
    id                  SERIAL PK
    recipient_id        INT FK → library_users(id) ON DELETE CASCADE
    loan_id             INT FK → loans(id)         ON DELETE CASCADE
    notification_type   VARCHAR(20)
    message             TEXT
    created_at          TIMESTAMPTZ DEFAULT NOW()
    is_read             BOOLEAN     DEFAULT FALSE
    ──────────────────────────────────────────────────────────────────────
    """

    class NotificationType(models.TextChoices):
        OVERDUE = "OVERDUE", "Overdue"
        DUE_SOON = "DUE_SOON", "Due Soon"
        RETURN_CONFIRMED = "RETURN_CONFIRMED", "Return Confirmed"
        FINE_ISSUED = "FINE_ISSUED", "Fine Issued"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    loan = models.ForeignKey(
        "circulation.Loan",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"], name="idx_notif_recipient_unread"),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.notification_type} -> {self.recipient} (loan #{self.loan_id})"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])
