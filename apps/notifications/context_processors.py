"""Makes the logged-in user's unread notification count available on every
page, since the nav bar in templates/base.html is shared across all apps."""


def unread_notifications_count(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {"unread_notifications_count": user.notifications.filter(is_read=False).count()}
