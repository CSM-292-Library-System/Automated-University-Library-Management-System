# Admin/Librarian Dashboard Module (Catalog & User Management)

**Module Developer**: Ekuman Frederick Okai Mensah  
**Team**: Team C — Django Application Development  
**Role**: Admin/librarian dashboard — views and templates for catalog and user management  
**System**: Automated University Library Management System (Group 4 Project)

---

## 📌 Module Overview

This module provides the complete **Admin/Librarian Interface** for managing book catalog entries, student/staff user profiles, inventory status, active circulation, and overdue fine collections.

### Features Included:
1. **Librarian Overview Dashboard**:
   - High-level metric widgets (Total Books, Physical Copies, Active Loans, Overdue Books, Registered Students, Outstanding Fines).
   - Automatic low inventory warnings ($\le 1$ available copies).
   - Recent circulation activity feeds.
2. **Book Catalog Management**:
   - Catalog browsing table with search by title, author, or ISBN.
   - Filtering by category and stock availability.
   - Add new book form (automatically creates physical copy accession numbers).
   - Edit book metadata & stock quantities.
   - Delete book confirmation view.
   - Book detail page with physical copy breakdown and active borrower list.
3. **User & Student Management**:
   - Member directory with search by Student ID, name, email, department.
   - Role filters (Student vs. Librarian) and Account status filters (Active vs. Suspended).
   - Detailed user profile view showing active loans, past loan history, and unpaid fines.
   - Student account status toggle (suspend/reinstate library access).
   - Fine management actions (mark fine as paid or waive fine).
4. **Circulation Register View**:
   - Librarian register showing active book issues, due dates, and 1-click return processing with automatic overdue fine calculation ($0.50/day).
5. **Role Security**:
   - Strict `@librarian_access_required` view decorator ensuring non-librarians/students see a friendly student notice page without redirect loops.

---

## 📂 File Directory Structure

```text
ekuman_librarian_dashboard_module/
├── README.md                      <-- This integration guide
└── librarian_dashboard/           <-- Django App Folder
    ├── __init__.py
    ├── apps.py
    ├── forms.py
    ├── models.py                  <-- (Empty/Uses central catalog/accounts/circulation models)
    ├── tests.py                   <-- 7 automated unit tests
    ├── urls.py                    <-- App URL patterns
    └── views.py                   <-- All dashboard, catalog & user management views
```

Templates included (in your shared `templates/` folder):
```text
templates/
└── librarian/
    ├── dashboard.html             <-- Overview dashboard
    ├── access_denied.html         <-- Student access notice page
    ├── catalog/
    │   ├── book_list.html         <-- Catalog table view
    │   ├── book_form.html         <-- Add & Edit book form
    │   ├── book_detail.html       <-- Book & copy details
    │   └── book_confirm_delete.html <-- Delete confirmation
    ├── users/
    │   ├── user_list.html         <-- Student & user directory
    │   ├── user_detail.html       <-- Student profile & fine collection
    │   └── user_confirm_status.html <-- Suspend/Activate confirm
    └── circulation/
        └── loan_list.html         <-- Circulation register
```

---

## 🛠️ Step-by-Step Integration Instructions

For the Integration Lead (**Asiedu Maxwell Kwame Sarpong** / **Darrel Amoah-Duah**):

### Step 1: Copy Module Files into the Main Django Project
1. Copy the `librarian_dashboard/` directory into your main Django project root (alongside `manage.py`).
2. Copy the `templates/librarian/` directory into your shared `templates/` directory (e.g., `templates/librarian/`).

### Step 2: Register App in `settings.py`
Add `'librarian_dashboard.apps.LibrarianDashboardConfig'` (or `'librarian_dashboard'`) to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'accounts',
    'catalog',
    'circulation',
    'librarian_dashboard',
]
```

### Step 3: Include URL Patterns in Root `urls.py`
In your root `urls.py`, include the librarian dashboard URLs:

```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # ...
    path('librarian/', include('librarian_dashboard.urls', namespace='librarian')),
]
```

### Step 4: Model Dependencies Required
The views in this module query the following models (defined by Team D / Catalog & Circulation module leads):
- **`accounts.User`**: Must have `role` (`'STUDENT'` or `'LIBRARIAN'`), `student_id`, `department`, `phone`, `is_active`, and a helper method `is_librarian()`.
- **`catalog.Book`**: Must have `title`, `author`, `isbn`, `category`, `publisher`, `publication_year`, `total_copies`, `available_copies`, `cover_url`, `description`.
- **`catalog.BookCopy`**: Must have `book`, `accession_number`, `status` (`'AVAILABLE'` / `'BORROWED'`).
- **`catalog.Category`**: Must have `name`, `description`, `icon_name`.
- **`circulation.Loan`**: Must have `borrower`, `book_copy`, `issue_date`, `due_date`, `return_date`, `status` (`'ACTIVE'`, `'RETURNED'`, `'OVERDUE'`), and property `is_overdue`.
- **`circulation.Fine`**: Must have `loan`, `amount`, `is_paid`, `paid_at`.

---

## 🔗 Canonical Schema Alignment (Team C naming convention)

Aligned with Team D's SQL schema (`Library_management_system.sql`) and the coordinator's Section 1.2 decision — this module's field names are the Team C reference convention:

| Concept          | Canonical (SQL / Django)                  |
|------------------|-------------------------------------------|
| Loan → Book copy | `Loan.book_copy` → `book_copies`          |
| Loan → User      | `Loan.borrower` (maps to `loans.user_id`) |
| Issue date       | `Loan.issue_date` (timestamp)             |
| Return date      | `Loan.return_date` (timestamp)            |
| Loan statuses    | `'ACTIVE'` / `'RETURNED'` / `'OVERDUE'`   |
| Fines            | Separate `Fine` model (`is_paid`, `paid_at`) |
| Book copies      | `BookCopy.accession_number`, `status`     |

Status note: loans are created `'ACTIVE'`, flagged `'OVERDUE'` (by the notifications module or when past `due_date`), and set to `'RETURNED'` on return. The dashboard treats every loan not `'RETURNED'` as outstanding and detects overdue via `due_date < today`.

---

## 🧪 Verification & Testing

To run the automated tests for this module in the unified codebase:
```bash
python manage.py test librarian_dashboard
```
All 7 unit tests should pass with `OK`.
