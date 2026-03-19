from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_default_statuses(sender, **kwargs):
    from .models import Status

    defaults = [
        ("Pending", "pending", 1),
        ("In Progress", "in-progress", 2),
        ("Resolved", "resolved", 3),
    ]
    for name, slug, order in defaults:
        Status.objects.get_or_create(name=name, defaults={"slug": slug, "order": order})


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        post_migrate.connect(create_default_statuses, sender=self)
