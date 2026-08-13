from django import forms

from .models import Notification


class NotificationMarkReadForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["is_read"]
