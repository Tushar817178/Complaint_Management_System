from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Complaint, Notification, Status
from .serializers import (
    CategorySerializer,
    ComplaintSerializer,
    NotificationSerializer,
    StatusSerializer,
)
from .models import Category


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "user"


class ComplaintListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role in ["admin", "staff"]:
            complaints = Complaint.objects.all().order_by("-created_at")
        else:
            complaints = Complaint.objects.filter(user=request.user).order_by("-created_at")
        serializer = ComplaintSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "user":
            return Response(
                {"detail": "Only users can create complaints."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ComplaintSerializer(data=request.data)
        if serializer.is_valid():
            status_obj = Status.objects.filter(slug="pending").first() or Status.objects.order_by(
                "order"
            ).first()
            if not status_obj:
                status_obj = Status.objects.create(name="Pending", slug="pending", order=1)
            complaint = serializer.save(user=request.user, status=status_obj)
            return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ComplaintDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk):
        if request.user.role == "admin":
            return Complaint.objects.filter(pk=pk).first()
        return Complaint.objects.filter(pk=pk, user=request.user).first()

    def get(self, request, pk):
        complaint = self.get_object(request, pk)
        if not complaint:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ComplaintSerializer(complaint).data)

    def put(self, request, pk):
        complaint = self.get_object(request, pk)
        if not complaint:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if request.user.role == "user" and complaint.is_resolved:
            return Response(
                {"detail": "Resolved complaints cannot be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ComplaintSerializer(complaint, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        complaint = self.get_object(request, pk)
        if not complaint:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if request.user.role not in ["admin", "staff"]:
            return Response(status=status.HTTP_403_FORBIDDEN)
        complaint.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = CategorySerializer(Category.objects.all().order_by("name"), many=True)
        return Response(serializer.data)


class StatusListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = StatusSerializer(Status.objects.all().order_by("order"), many=True)
        return Response(serializer.data)


class NotificationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = Notification.objects.filter(user=request.user).order_by("-created_at")
        serializer = NotificationSerializer(items, many=True)
        return Response(serializer.data)
