from functools import wraps
from datetime import timedelta
import csv

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CategoryForm,
    CommentForm,
    ComplaintEditForm,
    ComplaintForm,
    ComplaintUpdateForm,
    LoginForm,
    StatusForm,
    UserUpdateForm,
    UserRegistrationForm,
)
from .models import (
    Category,
    Comment,
    Complaint,
    ComplaintStatusHistory,
    Notification,
    Status,
    User,
    AuditLog,
)


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            allowed_roles = roles if roles else []
            if allowed_roles and request.user.role not in allowed_roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def get_default_status():
    status = Status.objects.filter(slug="pending").first() or Status.objects.order_by(
        "order"
    ).first()
    if not status:
        status = Status.objects.create(name="Pending", slug="pending", order=1)
    return status


def ensure_default_statuses():
    if Status.objects.exists():
        return
    Status.objects.create(name="Pending", slug="pending", order=1)
    Status.objects.create(name="In Progress", slug="in-progress", order=2)
    Status.objects.create(name="Resolved", slug="resolved", order=3)
    Status.objects.create(name="Withdrawn", slug="withdrawn", order=4)


def get_or_create_status(slug, name, order):
    status = Status.objects.filter(slug=slug).first()
    if status:
        return status
    return Status.objects.create(name=name, slug=slug, order=order)


def log_action(actor, action, entity, entity_id="", detail=""):
    if not actor or actor.role not in ["admin", "staff"]:
        return
    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        detail=detail,
    )


# Register
def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "user"
            user.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
    else:
        form = UserRegistrationForm()

    return render(request, "register.html", {"form": form})


# Login
def user_login(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("dashboard")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


# Logout
def user_logout(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    if request.user.role in ["admin", "staff"]:
        total = Complaint.objects.count()
        pending = Complaint.objects.filter(status__slug="pending").count()
        resolved = Complaint.objects.filter(status__slug="resolved").count()
        recent = Complaint.objects.select_related("user", "status").order_by("-created_at")[:5]
        by_status = list(
            Status.objects.annotate(count=Count("complaint")).order_by("order").values(
                "name", "count"
            )
        )
        by_priority = list(
            Complaint.objects.values("priority")
            .annotate(count=Count("id"))
            .order_by("priority")
        )
        return render(
            request,
            "dashboard.html",
            {
                "is_admin": True,
                "total": total,
                "pending": pending,
                "resolved": resolved,
                "recent": recent,
                "by_status": by_status,
                "by_priority": by_priority,
            },
        )

    total = Complaint.objects.filter(user=request.user).count()
    pending = Complaint.objects.filter(user=request.user, status__slug="pending").count()
    resolved = Complaint.objects.filter(user=request.user, status__slug="resolved").count()
    recent = (
        Complaint.objects.filter(user=request.user)
        .select_related("status")
        .order_by("-created_at")[:5]
    )
    by_status = list(
        Status.objects.annotate(
            count=Count("complaint", filter=Q(complaint__user=request.user))
        )
        .order_by("order")
        .values("name", "count")
    )
    by_priority = list(
        Complaint.objects.filter(user=request.user)
        .values("priority")
        .annotate(count=Count("id"))
        .order_by("priority")
    )
    return render(
        request,
        "dashboard.html",
        {
            "is_admin": False,
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "recent": recent,
            "by_status": by_status,
            "by_priority": by_priority,
        },
    )


@role_required("user")
def create_complaint(request):
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.user = request.user
            complaint.status = get_default_status()
            complaint.sla_days = getattr(settings, "DEFAULT_SLA_DAYS", 3)
            complaint.due_at = timezone.now() + timedelta(days=complaint.sla_days)
            complaint.save()
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                old_status=None,
                new_status=complaint.status,
                changed_by=request.user,
                remark="Complaint created",
            )
            messages.success(request, "Complaint submitted successfully.")
            messages.info(
                request, f"Your tracking ID is {complaint.ticket_id}."
            )
            return redirect("my_complaints")
    else:
        form = ComplaintForm()

    return render(request, "create_complaint.html", {"form": form})


@role_required("user")
def my_complaints(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "-created_at")

    complaints = Complaint.objects.filter(user=request.user).select_related(
        "status", "category"
    )

    if q:
        complaints = complaints.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )
    if status:
        complaints = complaints.filter(status__slug=status)
    if priority:
        complaints = complaints.filter(priority=priority)
    if category:
        complaints = complaints.filter(category__id=category)

    allowed_sorts = {"created_at", "-created_at", "priority", "-priority"}
    if sort not in allowed_sorts:
        sort = "-created_at"
    complaints = complaints.order_by(sort)

    paginator = Paginator(complaints, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "my_complaints.html",
        {
            "page_obj": page_obj,
            "q": q,
            "status": status,
            "priority": priority,
            "category": category,
            "sort": sort,
            "categories": Category.objects.all(),
            "statuses": Status.objects.all().order_by("order"),
        },
    )


@login_required
def complaint_detail(request, complaint_id):
    complaint = get_object_or_404(
        Complaint.objects.select_related("status", "category", "user"),
        id=complaint_id,
    )
    is_admin = request.user.role == "admin"
    is_owner = complaint.user_id == request.user.id

    if not is_admin and not is_owner:
        messages.error(request, "You do not have access to that complaint.")
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "comment":
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.complaint = complaint
                comment.user = request.user
                comment.is_internal = bool(request.POST.get("is_internal")) and is_admin
                comment.save()
                if not comment.is_internal and comment.user_id != complaint.user_id:
                    Notification.objects.create(
                        user=complaint.user,
                        complaint=complaint,
                        message=f"New comment on: {complaint.title}",
                    )
                messages.success(request, "Comment added.")
                return redirect("complaint_detail", complaint_id=complaint.id)
        elif action == "update" and is_admin:
            update_form = ComplaintUpdateForm(request.POST, instance=complaint)
            if update_form.is_valid():
                old_status = complaint.status
                updated = update_form.save(commit=False)
                old_assignee = complaint.assigned_to
                old_team = complaint.assigned_team
                if updated.status and updated.status.slug == "resolved":
                    updated.resolved_at = updated.resolved_at or timezone.now()
                else:
                    updated.resolved_at = None
                updated.save()
                remark = update_form.cleaned_data.get("remark", "")
                if old_status != updated.status:
                    ComplaintStatusHistory.objects.create(
                        complaint=updated,
                        old_status=old_status,
                        new_status=updated.status,
                        changed_by=request.user,
                        remark=remark or "Status updated",
                    )
                    Notification.objects.create(
                        user=updated.user,
                        complaint=updated,
                        message=f"Status updated to {updated.status.name}",
                    )
                    log_action(
                        request.user,
                        "status",
                        "Complaint",
                        updated.id,
                        f"{old_status} -> {updated.status}",
                    )
                if old_assignee != updated.assigned_to and updated.assigned_to:
                    Notification.objects.create(
                        user=updated.assigned_to,
                        complaint=updated,
                        message=f"You were assigned: {updated.title}",
                    )
                    log_action(
                        request.user,
                        "assign",
                        "Complaint",
                        updated.id,
                        f"Assigned to {updated.assigned_to}",
                    )
                if old_team != updated.assigned_team and updated.assigned_team:
                    Notification.objects.create(
                        user=updated.user,
                        complaint=updated,
                        message=f"Your complaint was assigned to {updated.get_assigned_team_display()}",
                    )
                    log_action(
                        request.user,
                        "assign",
                        "Complaint",
                        updated.id,
                        f"Assigned to {updated.get_assigned_team_display()}",
                    )
                if remark:
                    Comment.objects.create(
                        complaint=updated,
                        user=request.user,
                        remark=remark,
                        is_internal=True,
                    )
                messages.success(request, "Complaint updated.")
                log_action(
                    request.user,
                    "update",
                    "Complaint",
                    updated.id,
                    "Admin updated complaint details",
                )
                return redirect("complaint_detail", complaint_id=complaint.id)
    else:
        comment_form = CommentForm()
        update_form = ComplaintUpdateForm(instance=complaint)

    if request.method == "POST":
        if "comment_form" not in locals():
            comment_form = CommentForm()
        if "update_form" not in locals():
            update_form = ComplaintUpdateForm(instance=complaint)

    comments = Comment.objects.filter(complaint=complaint).select_related("user")
    if not is_admin:
        comments = comments.filter(is_internal=False)

    history = ComplaintStatusHistory.objects.filter(complaint=complaint).select_related(
        "old_status", "new_status", "changed_by"
    )

    if request.user.is_authenticated:
        Notification.objects.filter(
            user=request.user, complaint=complaint, is_read=False
        ).update(is_read=True)

    return render(
        request,
        "complaint_detail.html",
        {
            "complaint": complaint,
            "is_admin": is_admin,
            "is_owner": is_owner,
            "comment_form": comment_form,
            "update_form": update_form,
            "comments": comments.order_by("-created_at"),
            "history": history.order_by("-created_at"),
        },
    )


@role_required("user")
def edit_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id, user=request.user)
    if complaint.is_resolved:
        messages.error(request, "Resolved complaints cannot be edited.")
        return redirect("complaint_detail", complaint_id=complaint.id)

    if request.method == "POST":
        form = ComplaintEditForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            form.save()
            messages.success(request, "Complaint updated.")
            return redirect("complaint_detail", complaint_id=complaint.id)
    else:
        form = ComplaintEditForm(instance=complaint)

    return render(request, "edit_complaint.html", {"form": form, "complaint": complaint})


@role_required("user")
def withdraw_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id, user=request.user)
    if complaint.is_resolved:
        messages.error(request, "Resolved complaints cannot be withdrawn.")
        return redirect("complaint_detail", complaint_id=complaint.id)

    if request.method == "POST":
        old_status = complaint.status
        withdrawn_status = get_or_create_status("withdrawn", "Withdrawn", 4)
        if old_status != withdrawn_status:
            complaint.status = withdrawn_status
            complaint.resolved_at = None
            complaint.save()
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                old_status=old_status,
                new_status=withdrawn_status,
                changed_by=request.user,
                remark="Complaint withdrawn by user",
            )
            Notification.objects.create(
                user=request.user,
                complaint=complaint,
                message="You withdrew your complaint.",
            )
            messages.success(request, "Complaint withdrawn.")
        return redirect("my_complaints")

    return redirect("complaint_detail", complaint_id=complaint.id)


@role_required("admin", "staff")
def admin_complaints(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "delete":
            complaint_id = request.POST.get("complaint_id")
            complaint = get_object_or_404(Complaint, id=complaint_id)
            complaint.delete()
            messages.success(request, "Complaint deleted.")
            log_action(request.user, "delete", "Complaint", complaint_id, "Deleted")
        elif action == "update_status":
            complaint_id = request.POST.get("complaint_id")
            complaint = get_object_or_404(Complaint, id=complaint_id)
            status_id = request.POST.get("status_id")
            remark = request.POST.get("remark", "").strip()
            if status_id:
                new_status = get_object_or_404(Status, id=status_id)
                old_status = complaint.status
                if old_status != new_status:
                    complaint.status = new_status
                    if new_status.slug == "resolved":
                        complaint.resolved_at = complaint.resolved_at or timezone.now()
                    else:
                        complaint.resolved_at = None
                    complaint.save()
                    ComplaintStatusHistory.objects.create(
                        complaint=complaint,
                        old_status=old_status,
                        new_status=new_status,
                        changed_by=request.user,
                        remark=remark or "Status updated",
                    )
                    Notification.objects.create(
                        user=complaint.user,
                        complaint=complaint,
                        message=f"Status updated to {new_status.name}",
                    )
                    if remark:
                        Comment.objects.create(
                            complaint=complaint,
                            user=request.user,
                            remark=remark,
                            is_internal=True,
                        )
                    messages.success(request, "Status updated.")
                    log_action(
                        request.user,
                        "status",
                        "Complaint",
                        complaint.id,
                        f"{old_status} -> {new_status}",
                    )
                else:
                    messages.info(request, "Status unchanged.")
        elif action == "bulk_update":
            ids = request.POST.getlist("complaint_ids")
            status_id = request.POST.get("bulk_status_id")
            if ids and status_id:
                new_status = get_object_or_404(Status, id=status_id)
                complaints = Complaint.objects.filter(id__in=ids)
                for complaint in complaints:
                    old_status = complaint.status
                    if old_status != new_status:
                        complaint.status = new_status
                        complaint.resolved_at = (
                            timezone.now() if new_status.slug == "resolved" else None
                        )
                        complaint.save()
                        ComplaintStatusHistory.objects.create(
                            complaint=complaint,
                            old_status=old_status,
                            new_status=new_status,
                            changed_by=request.user,
                            remark="Bulk status update",
                        )
                        Notification.objects.create(
                            user=complaint.user,
                            complaint=complaint,
                            message=f"Status updated to {new_status.name}",
                        )
                        log_action(
                            request.user,
                            "status",
                            "Complaint",
                            complaint.id,
                            f"{old_status} -> {new_status} (bulk)",
                        )
                messages.success(request, "Bulk status update completed.")
        next_url = request.POST.get("next") or "admin_complaints"
        return redirect(next_url)

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "-created_at")
    assigned_to = request.GET.get("assigned_to", "")
    assigned_team = request.GET.get("assigned_team", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    overdue = request.GET.get("overdue", "")

    complaints = Complaint.objects.select_related("status", "category", "user")

    if q:
        complaints = complaints.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(user__username__icontains=q)
        )
    if status:
        complaints = complaints.filter(status__slug=status)
    if priority:
        complaints = complaints.filter(priority=priority)
    if category:
        complaints = complaints.filter(category__id=category)
    if assigned_to:
        complaints = complaints.filter(assigned_to__id=assigned_to)
    if assigned_team:
        complaints = complaints.filter(assigned_team=assigned_team)
    if date_from:
        complaints = complaints.filter(created_at__date__gte=date_from)
    if date_to:
        complaints = complaints.filter(created_at__date__lte=date_to)
    if overdue == "1":
        complaints = complaints.filter(due_at__lt=timezone.now()).exclude(
            status__slug="resolved"
        )

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=complaints.csv"
        writer = csv.writer(response)
        writer.writerow(
            ["Title", "User", "Status", "Priority", "Category", "Assigned", "Created"]
        )
        for c in complaints.order_by("-created_at"):
            writer.writerow(
                [
                    c.title,
                    c.user.username,
                    c.status.name,
                    c.priority,
                    c.category.name if c.category else "",
                    c.assigned_to.username
                    if c.assigned_to
                    else (c.get_assigned_team_display() if c.assigned_team else ""),
                    c.created_at.strftime("%Y-%m-%d"),
                ]
            )
        return response

    allowed_sorts = {"created_at", "-created_at", "priority", "-priority"}
    if sort not in allowed_sorts:
        sort = "-created_at"
    complaints = complaints.order_by(sort)

    paginator = Paginator(complaints, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "admin_complaints.html",
        {
            "page_obj": page_obj,
            "q": q,
            "status": status,
            "priority": priority,
            "category": category,
            "sort": sort,
            "assigned_to": assigned_to,
            "assigned_team": assigned_team,
            "date_from": date_from,
            "date_to": date_to,
            "overdue": overdue,
            "categories": Category.objects.all(),
            "statuses": Status.objects.all().order_by("order"),
            "admins": User.objects.filter(role__in=["admin", "staff"]).order_by(
                "username"
            ),
        },
    )


@role_required("admin")
def manage_users(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update":
            user_id = request.POST.get("user_id")
            target = get_object_or_404(User, id=user_id)
            form = UserUpdateForm(request.POST, instance=target)
            if form.is_valid():
                updated = form.save(commit=False)
                if target.id == request.user.id and (
                    updated.role != "admin" or not updated.is_active
                ):
                    messages.error(
                        request,
                        "You cannot remove your own admin role or deactivate your account.",
                    )
                else:
                    updated.save()
                    messages.success(request, "User updated.")
                    log_action(
                        request.user,
                        "update",
                        "User",
                        target.id,
                        f"Role={updated.role}, active={updated.is_active}",
                    )
            else:
                messages.error(request, "Please correct the errors in the form.")
        next_url = request.POST.get("next") or "admin_users"
        return redirect(next_url)

    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")

    users = User.objects.order_by("-date_joined")
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    if role:
        users = users.filter(role=role)

    return render(
        request,
        "admin_users.html",
        {
            "users": users,
            "q": q,
            "role": role,
        },
    )


@role_required("admin")
def manage_categories(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            form = CategoryForm(request.POST)
            if form.is_valid():
                category = form.save()
                messages.success(request, "Category added.")
                log_action(request.user, "create", "Category", category.id, category.name)
            else:
                messages.error(request, "Please correct the errors in the form.")
        elif action == "update":
            category_id = request.POST.get("category_id")
            category = get_object_or_404(Category, id=category_id)
            form = CategoryForm(request.POST, instance=category)
            if form.is_valid():
                category = form.save()
                messages.success(request, "Category updated.")
                log_action(request.user, "update", "Category", category.id, category.name)
            else:
                messages.error(request, "Please correct the errors in the form.")
        elif action == "delete":
            category_id = request.POST.get("category_id")
            category = get_object_or_404(Category, id=category_id)
            category.delete()
            messages.success(request, "Category deleted.")
            log_action(request.user, "delete", "Category", category_id, "Deleted")

        next_url = request.POST.get("next") or "admin_categories"
        return redirect(next_url)

    categories = Category.objects.annotate(
        complaint_count=Count("complaint")
    ).order_by("name")

    return render(
        request,
        "admin_categories.html",
        {
            "categories": categories,
            "form": CategoryForm(),
        },
    )


@role_required("admin")
def manage_statuses(request):
    ensure_default_statuses()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            form = StatusForm(request.POST)
            if form.is_valid():
                status_obj = form.save()
                messages.success(request, "Status added.")
                log_action(request.user, "create", "Status", status_obj.id, status_obj.name)
            else:
                messages.error(request, "Please correct the errors in the form.")
        elif action == "update":
            status_id = request.POST.get("status_id")
            status_obj = get_object_or_404(Status, id=status_id)
            form = StatusForm(request.POST, instance=status_obj)
            if form.is_valid():
                status_obj = form.save()
                messages.success(request, "Status updated.")
                log_action(request.user, "update", "Status", status_obj.id, status_obj.name)
            else:
                messages.error(request, "Please correct the errors in the form.")
        elif action == "delete":
            status_id = request.POST.get("status_id")
            status_obj = get_object_or_404(Status, id=status_id)
            try:
                status_obj.delete()
                messages.success(request, "Status deleted.")
                log_action(request.user, "delete", "Status", status_id, "Deleted")
            except ProtectedError:
                messages.error(
                    request,
                    "This status is in use and cannot be deleted.",
                )

        next_url = request.POST.get("next") or "admin_statuses"
        return redirect(next_url)

    statuses = Status.objects.annotate(
        complaint_count=Count("complaint")
    ).order_by("order", "name")

    return render(
        request,
        "admin_statuses.html",
        {
            "statuses": statuses,
            "form": StatusForm(),
        },
    )


@login_required
def notifications(request):
    items = Notification.objects.filter(user=request.user).order_by("-created_at")
    if request.method == "POST":
        if request.POST.get("action") == "mark_all_read":
            items.update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        return redirect("notifications")
    return render(request, "notifications.html", {"notifications": items})


@role_required("admin")
def admin_audit_logs(request):
    q = request.GET.get("q", "").strip()
    action = request.GET.get("action", "")
    logs = AuditLog.objects.select_related("actor").order_by("-created_at")
    if q:
        logs = logs.filter(
            Q(entity__icontains=q)
            | Q(entity_id__icontains=q)
            | Q(detail__icontains=q)
            | Q(actor__username__icontains=q)
        )
    if action:
        logs = logs.filter(action=action)
    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "admin_audit_logs.html",
        {"page_obj": page_obj, "q": q, "action": action},
    )


def public_track(request):
    ticket = request.GET.get("ticket", "").strip().upper()
    complaint = None
    if ticket:
        complaint = Complaint.objects.filter(ticket_id=ticket).select_related("status").first()
    return render(
        request,
        "public_track.html",
        {"ticket": ticket, "complaint": complaint},
    )


@login_required
def complaint_pdf(request, complaint_id):
    complaint = get_object_or_404(
        Complaint.objects.select_related("status", "category", "user"),
        id=complaint_id,
    )
    is_admin = request.user.role in ["admin", "staff"]
    is_owner = complaint.user_id == request.user.id
    if not is_admin and not is_owner:
        messages.error(request, "You do not have access to that complaint.")
        return redirect("dashboard")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        messages.error(request, "PDF export library not installed.")
        return redirect("complaint_detail", complaint_id=complaint.id)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="complaint_{complaint.ticket_id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Complaint Report")
    y -= 30
    p.setFont("Helvetica", 11)
    lines = [
        f"Ticket ID: {complaint.ticket_id}",
        f"Title: {complaint.title}",
        f"User: {complaint.user.username}",
        f"Status: {complaint.status.name}",
        f"Priority: {complaint.priority}",
        f"Category: {complaint.category.name if complaint.category else '-'}",
        f"Created: {complaint.created_at.strftime('%Y-%m-%d %H:%M')}",
        f"Due: {complaint.due_at.strftime('%Y-%m-%d %H:%M') if complaint.due_at else '-'}",
    ]
    for line in lines:
        p.drawString(50, y, line)
        y -= 18

    y -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Description")
    y -= 18
    p.setFont("Helvetica", 11)
    for chunk in complaint.description.split("\n"):
        p.drawString(50, y, chunk[:100])
        y -= 16
        if y < 60:
            p.showPage()
            y = height - 50
    p.showPage()
    p.save()
    return response
