from rest_framework import serializers
from .models import Category, Complaint, Notification, Status, User


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ["id", "name", "slug", "order"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_active"]


class ComplaintSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    status = StatusSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    assigned_to = serializers.StringRelatedField(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="status", write_only=True, required=False
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=["admin", "staff"]),
        source="assigned_to",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Complaint
        fields = [
            "id",
            "ticket_id",
            "title",
            "description",
            "priority",
            "attachment",
            "created_at",
            "updated_at",
            "resolved_at",
            "sla_days",
            "due_at",
            "assigned_team",
            "user",
            "status",
            "category",
            "assigned_to",
            "status_id",
            "category_id",
            "assigned_to_id",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    complaint_id = serializers.IntegerField(source="complaint.id", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "message", "is_read", "created_at", "complaint_id"]
