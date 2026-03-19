from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Complaint, Comment, Category, Status


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "priority", "attachment"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }


class ComplaintEditForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "priority", "attachment"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }


class ComplaintUpdateForm(forms.ModelForm):
    remark = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    due_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
    )

    class Meta:
        model = Complaint
        fields = ["status", "priority", "category", "assigned_to", "assigned_team", "due_at"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "assigned_team": forms.Select(attrs={"class": "form-select"}),
            "due_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["remark"]
        widgets = {
            "remark": forms.Textarea(attrs={"class": "form-control", "rows": 3})
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"class": "form-control"})}


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ["name", "order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class UserUpdateForm(forms.ModelForm):
    is_active = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["role", "is_active"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
