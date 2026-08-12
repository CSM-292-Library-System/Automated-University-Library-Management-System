"""
Circulation App — Django Signals
=================================
Uses Django's post_save signal to automate fine creation.

Signal flow:
  1. A management command (or scheduled task) calls `loan.status = 'OVERDUE'`
     and saves the loan.
  2. The `post_save` signal fires and creates / updates a Fine record.
  3. No manual fine creation is needed anywhere in views or commands.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Loan, Fine


@receiver(post_save, sender=Loan)
def create_or_update_fine_on_overdue(sender, instance, created, **kwargs):
    """
    Automatically creates (or updates) a Fine when a Loan transitions to OVERDUE.

    Behaviour:
      - If a Fine already exists for this loan, the amount is recalculated.
      - If no Fine exists yet, a new one is created.
      - If the loan is RETURNED with an existing UNPAID fine, the fine is
        preserved (the user still owes it) but no new fine is created.
    """
    if instance.status == Loan.Status.OVERDUE:
        calculated = instance.calculated_fine
        try:
            fine = instance.fine  # OneToOne accessor
            if fine.status == Fine.Status.UNPAID:
                fine.amount = calculated
                fine.save(update_fields=["amount"])
        except Fine.DoesNotExist:
            Fine.objects.create(
                loan=instance,
                user=instance.user,
                amount=calculated,
                status=Fine.Status.UNPAID,
            )
