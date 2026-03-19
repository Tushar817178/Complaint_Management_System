# Online Complaint Management System

A production‑ready Complaint Management System built with Django and MySQL.  
It provides role‑based access, SLA tracking, audit logs, notifications, and a clean admin workflow.

## Highlights

- Role-based access: Admin, Staff, User
- Complaint lifecycle with timeline and comments
- SLA tracking with overdue flags
- Admin dashboard with advanced filters and bulk actions
- Audit log for all admin/staff changes
- PDF and CSV exports
- Public tracking by ticket ID
- REST API endpoints
- Responsive UI with modern theming

## Tech Stack

- Backend: Django 6.0.3, Django REST Framework
- Database: MySQL
- Frontend: HTML, CSS, Bootstrap 5, JavaScript

## Features

### User
- Register, login, logout
- Submit complaints with attachments
- Track status and timeline
- Edit complaints before resolution
- View notifications
- Download PDF report

### Admin / Staff
- Manage complaints, categories, statuses
- Assign to staff or teams
- Update status with remarks
- Bulk update status
- Advanced filters (date range, assigned, overdue)
- Audit log of all actions
- CSV export from list

### Public
- Track complaint using ticket ID

## Getting Started

### 1) Install Dependencies
```bash
pip install -r requirements.txt
```

### 2) Configure MySQL
Create a database named `complaint_db` and set:

```bash
DB_NAME=complaint_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

Or update `complaint_system/settings.py` directly.

### 3) Migrate
```bash
python manage.py migrate
```

### 4) (Optional) Seed Data
```bash
python manage.py seed_data
```

### 5) Create Superuser
```bash
python manage.py createsuperuser
```

### 6) Run
```bash
python manage.py runserver
```



## Role Setup

- Promote a user to Admin/Staff via Django Admin or the Users page.
- Admin has full access; Staff can manage complaints only.


```

## Notes

- Attachments are stored in `media/`
- PDF export uses `reportlab`
- CSV export available from admin list
