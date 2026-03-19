from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("staff", "Staff"),
        ("user", "User"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")

    def __str__(self):
        return self.username


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Status(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Complaint(models.Model):
    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )
    TEAM_CHOICES = (
        ("support", "Support Team"),
        ("technical", "Technical Team"),
        ("billing", "Billing Team"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.ForeignKey(Status, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
        limit_choices_to={"role__in": ["admin", "staff"]},
    )
    assigned_team = models.CharField(max_length=20, choices=TEAM_CHOICES, blank=True)
    ticket_id = models.CharField(max_length=12, unique=True, blank=True)
    attachment = models.FileField(upload_to="complaints/", null=True, blank=True)
    sla_days = models.PositiveIntegerField(default=3)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def is_resolved(self):
        return self.status and self.status.slug == "resolved"

    @property
    def is_overdue(self):
        return self.due_at and not self.is_resolved and self.due_at < timezone.now()

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            import uuid

            token = uuid.uuid4().hex[:10].upper()
            while Complaint.objects.filter(ticket_id=token).exists():
                token = uuid.uuid4().hex[:10].upper()
            self.ticket_id = token
        super().save(*args, **kwargs)


class Comment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    remark = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.complaint}"


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    old_status = models.ForeignKey(
        Status, on_delete=models.SET_NULL, null=True, related_name="old_status_entries"
    )
    new_status = models.ForeignKey(
        Status, on_delete=models.SET_NULL, null=True, related_name="new_status_entries"
    )
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.complaint} - {self.new_status}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.message}"


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("status", "Status Change"),
        ("assign", "Assign"),
    )
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=50, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.actor} - {self.action} - {self.entity}"
