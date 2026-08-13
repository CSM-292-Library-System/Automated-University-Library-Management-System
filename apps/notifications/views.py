from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()
    return render(request, "notifications/notification_list.html", {"notifications": notifications})


@login_required
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if request.method == "POST":
        notification.mark_read()
    return redirect("notifications:list")
