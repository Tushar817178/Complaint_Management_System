from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.models import Category, Complaint, Status, User


class Command(BaseCommand):
    help = "Seed sample categories, statuses, and complaints."

    def handle(self, *args, **options):
        if not Status.objects.exists():
            Status.objects.create(name="Pending", slug="pending", order=1)
            Status.objects.create(name="In Progress", slug="in-progress", order=2)
            Status.objects.create(name="Resolved", slug="resolved", order=3)
            Status.objects.create(name="Withdrawn", slug="withdrawn", order=4)

        categories = ["Technical", "Billing", "Service", "Delivery", "Other"]
        for name in categories:
            Category.objects.get_or_create(name=name)

        user, _ = User.objects.get_or_create(
            username="demo_user",
            defaults={"email": "demo@example.com", "role": "user"},
        )
        if not user.has_usable_password():
            user.set_password("demo12345")
            user.save()

        status_pending = Status.objects.filter(slug="pending").first()
        category = Category.objects.first()

        if not Complaint.objects.filter(user=user).exists():
            for i in range(1, 6):
                Complaint.objects.create(
                    user=user,
                    title=f"Sample complaint {i}",
                    description="This is a sample complaint for demo purposes.",
                    category=category,
                    priority="medium",
                    status=status_pending,
                    sla_days=3,
                    due_at=timezone.now() + timedelta(days=3),
                )

        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))
