# Database Documentation
## Automated University Library Management System
### Group 4 — Django + PostgreSQL Backend

---

## 1. Overview

The system uses **PostgreSQL** as its primary data store. Django's ORM layer
translates Python model classes into SQL queries and manages migrations. Each
Django model maps 1-to-1 with a PostgreSQL table.

The database enforces data integrity at two levels:
- **Database level** — foreign keys, UNIQUE constraints, CHECK constraints,
  and indexes defined in the original SQL schema.
- **Application level** — Django model validators, form validators,
  and business logic methods in model/service classes.

---

## 2. Database Tables

### 2.1 `library_users`

**Django Model:** `apps.users.models.LibraryUser`

| Column | PostgreSQL Type | Django Field | Notes |
|--------|----------------|--------------|-------|
| `id` | `SERIAL PRIMARY KEY` | `BigAutoField` (auto) | |
| `username` | `VARCHAR(150) UNIQUE NOT NULL` | `CharField(unique=True)` | Used for login |
| `email` | `VARCHAR(255) UNIQUE NOT NULL` | `EmailField(unique=True)` | |
| `first_name` | `VARCHAR(150) NOT NULL` | `CharField` | |
| `other_names` | `VARCHAR(150)` | `CharField(blank=True)` | Middle names |
| `surname` | `VARCHAR(150) NOT NULL` | `CharField` | |
| `role` | `VARCHAR(20)` CHECK | `CharField(choices=Role)` | STUDENT / LECTURER / OUTSIDER / STAFF |
| `phone_number` | `VARCHAR(25)` | `CharField(blank=True)` | |
| `identification_number` | `VARCHAR(50) UNIQUE NOT NULL` | `CharField(unique=True)` | Student ID / Staff ID / National ID |
| `is_active` | `BOOLEAN DEFAULT TRUE` | `BooleanField` | Deactivation instead of deletion |
| `date_joined` | `TIMESTAMPTZ DEFAULT NOW()` | `DateTimeField(default=timezone.now)` | |
| `password` | *(hashed — not in schema)* | `AbstractBaseUser` managed | PBKDF2-SHA256 via Django's auth |

**Indexes:**
```sql
CREATE INDEX idx_users_role ON library_users(role);
```

**Design Notes:**
- Extends `AbstractBaseUser` + `PermissionsMixin` to retain Django's session auth,
  permission groups, and the built-in admin.
- `is_staff=True` gives access to `/admin/`; `role='STAFF'` marks someone as
  a librarian in app logic (checked via `user.is_librarian`).

---

### 2.2 `books`

**Django Model:** `apps.catalog.models.Book`

| Column | PostgreSQL Type | Django Field | Notes |
|--------|----------------|--------------|-------|
| `id` | `SERIAL PRIMARY KEY` | `BigAutoField` (auto) | |
| `title` | `VARCHAR(255) NOT NULL` | `CharField(max_length=255)` | |
| `author` | `VARCHAR(255) NOT NULL` | `CharField(max_length=255)` | |
| `isbn` | `VARCHAR(13) UNIQUE NOT NULL` | `CharField(max_length=13, unique=True)` | ISBN-13 |
| `category` | `VARCHAR(100) NOT NULL` | `CharField(max_length=100)` | e.g. "Computer Science" |
| `publication_year` | `INT CHECK (> 0)` | `PositiveIntegerField` | |
| `created_at` | `TIMESTAMPTZ DEFAULT NOW()` | `DateTimeField(auto_now_add=True)` | |

**Indexes:**
```sql
CREATE INDEX idx_books_isbn ON books(isbn);
```

**Design Notes:**
- Stores bibliographic **metadata** only — one row per unique work.
- Physical copies are tracked in `book_copies`.
- `available_copies_count` is a Python property that issues a COUNT query.

---

### 2.3 `book_copies`

**Django Model:** `apps.catalog.models.BookCopy`

| Column | PostgreSQL Type | Django Field | Notes |
|--------|----------------|--------------|-------|
| `id` | `SERIAL PRIMARY KEY` | `BigAutoField` (auto) | |
| `book_id` | `INT FK → books(id) ON DELETE CASCADE` | `ForeignKey(Book, CASCADE)` | Deleting a book removes all copies |
| `accession_number` | `VARCHAR(50) UNIQUE NOT NULL` | `CharField(max_length=50, unique=True)` | Barcode / RFID tag |
| `status` | `VARCHAR(20)` CHECK | `CharField(choices=Status)` | AVAILABLE / BORROWED / MAINTENANCE |

**Indexes:**
```sql
CREATE INDEX idx_copies_accession ON book_copies(accession_number);
```

**Status Transitions:**
```
AVAILABLE ──[Issue Loan]────► BORROWED
BORROWED  ──[Return Book]───► AVAILABLE
AVAILABLE ──[Send for Repair]► MAINTENANCE
MAINTENANCE ──[Repaired]────► AVAILABLE
```

**Design Notes:**
- `select_for_update()` is used inside `IssueLoanView` to prevent two
  concurrent requests issuing the same copy (race condition protection).

---

### 2.4 `loans`

**Django Model:** `apps.circulation.models.Loan`

| Column | PostgreSQL Type | Django Field | Notes |
|--------|----------------|--------------|-------|
| `id` | `SERIAL PRIMARY KEY` | `BigAutoField` (auto) | |
| `user_id` | `INT FK → library_users(id) ON DELETE RESTRICT` | `ForeignKey(LibraryUser, RESTRICT)` | Cannot delete user with active loans |
| `book_copy_id` | `INT FK → book_copies(id) ON DELETE RESTRICT` | `ForeignKey(BookCopy, RESTRICT)` | Cannot delete copy with active loans |
| `borrow_date` | `TIMESTAMPTZ DEFAULT NOW()` | `DateTimeField(default=timezone.now)` | |
| `due_date` | `TIMESTAMPTZ NOT NULL` | `DateTimeField(default=default_due_date)` | Default = now + 14 days |
| `return_date` | `TIMESTAMPTZ` (nullable) | `DateTimeField(null=True, blank=True)` | Set on return |
| `status` | `VARCHAR(20)` CHECK | `CharField(choices=Status)` | ACTIVE / RETURNED / OVERDUE |

**Indexes:**
```sql
CREATE INDEX idx_loans_user   ON loans(user_id);
CREATE INDEX idx_loans_status ON loans(status);
```

**Status Transitions:**
```
ACTIVE ──[mark_overdue_loans command]──► OVERDUE
ACTIVE ──[return_book()]──────────────► RETURNED
OVERDUE ──[return_book()]─────────────► RETURNED
ACTIVE ──[renew()]────────────────────► ACTIVE (extended due_date)
```

**Business Logic Methods:**

| Method / Property | Description |
|-------------------|-------------|
| `loan.is_overdue` | `True` if ACTIVE and `now > due_date` |
| `loan.days_overdue` | Full calendar days past due |
| `loan.calculated_fine` | `days_overdue × FINE_PER_DAY` |
| `loan.return_book()` | Sets `return_date`, status → RETURNED, copy → AVAILABLE |
| `loan.renew(days)` | Extends `due_date`; raises `ValueError` if overdue |

---

### 2.5 `fines`

**Django Model:** `apps.circulation.models.Fine`

| Column | PostgreSQL Type | Django Field | Notes |
|--------|----------------|--------------|-------|
| `id` | `SERIAL PRIMARY KEY` | `BigAutoField` (auto) | |
| `loan_id` | `INT UNIQUE FK → loans(id) ON DELETE CASCADE` | `OneToOneField(Loan, CASCADE)` | One fine per loan |
| `user_id` | `INT FK → library_users(id) ON DELETE CASCADE` | `ForeignKey(LibraryUser, CASCADE)` | Denormalised for fast user queries |
| `amount` | `DECIMAL(10,2) CHECK (>= 0)` | `DecimalField(max_digits=10, decimal_places=2)` | Recalculated daily |
| `status` | `VARCHAR(20)` CHECK | `CharField(choices=Status)` | UNPAID / PAID |
| `created_at` | `TIMESTAMPTZ DEFAULT NOW()` | `DateTimeField(auto_now_add=True)` | |
| `paid_at` | `TIMESTAMPTZ` (nullable) | `DateTimeField(null=True, blank=True)` | Set by `fine.mark_paid()` |

**Indexes:**
```sql
CREATE INDEX idx_fines_user ON fines(user_id);
```

**Design Notes:**
- `loan_id UNIQUE` → `OneToOneField` in Django (exactly one fine per loan).
- Fine creation is **fully automated via a Django signal** — saving a Loan
  with `status='OVERDUE'` triggers `create_or_update_fine_on_overdue`.
- `amount` grows each day the `mark_overdue_loans` command runs.

---

## 3. Entity-Relationship Diagram

```
┌─────────────────────┐        ┌─────────────────────┐
│   library_users     │        │       books          │
│─────────────────────│        │─────────────────────-│
│ id (PK)             │        │ id (PK)              │
│ username            │        │ title                │
│ email               │        │ author               │
│ first_name          │        │ isbn (UNIQUE)        │
│ surname             │        │ category             │
│ role                │        │ publication_year     │
│ identification_no   │        └──────────┬──────────-┘
│ is_active           │                   │ 1
└──────┬──────────────┘                   │
       │ 1                                │ has many
       │ borrows                          ▼
       │ many             ┌──────────────────────────┐
       ▼                  │      book_copies          │
┌──────────────────┐      │──────────────────────────│
│     loans        │◄─────│ id (PK)                  │
│──────────────────│ many │ book_id (FK)             │
│ id (PK)          │      │ accession_number (UNIQUE) │
│ user_id (FK)     │      │ status                   │
│ book_copy_id (FK)│      └──────────────────────────┘
│ borrow_date      │
│ due_date         │
│ return_date      │
│ status           │
└────────┬─────────┘
         │ 1
         │ triggers
         ▼
┌──────────────────┐
│     fines        │
│──────────────────│
│ id (PK)          │
│ loan_id (FK,UNIQ)│
│ user_id (FK)     │
│ amount           │
│ status           │
│ created_at       │
│ paid_at          │
└──────────────────┘
```

---

## 4. Data Flow

### 4.1 Borrowing a Book

```
Librarian → IssueLoanView POST
  └─ select_for_update() locks the BookCopy row
  └─ BookCopy.status = 'BORROWED' → SAVE
  └─ Loan.create(user, copy, due_date) → SAVE
  └─ Response: redirect to all-loans list
```

### 4.2 Returning a Book

```
Librarian → return_book view POST
  └─ Loan.return_book()
       ├─ loan.return_date = now()
       ├─ loan.status = 'RETURNED' → SAVE
       └─ book_copy.status = 'AVAILABLE' → SAVE
  └─ Any existing UNPAID fine remains (user still owes it)
```

### 4.3 Overdue Detection (Automated — runs every hour)

```
Cron → python manage.py mark_overdue_loans
  └─ SELECT loans WHERE status='ACTIVE' AND due_date < NOW()
  └─ For each loan:
       └─ loan.status = 'OVERDUE' → SAVE
       └─ post_save signal fires →
              create_or_update_fine_on_overdue()
                └─ Fine exists? → UPDATE amount (recalculate)
                └─ Fine not yet? → CREATE Fine(loan, user, amount)
```

### 4.4 Daily Alert (Automated — runs at 8 AM)

```
Cron → python manage.py send_overdue_alerts
  └─ SELECT loans WHERE status IN ('OVERDUE', 'ACTIVE') AND due_date < NOW()
  └─ Group by user
  └─ For each user → log alert (or send email when SMTP is configured)
```

### 4.5 Fine Payment

```
Librarian → pay_fine view POST
  └─ fine.mark_paid()
       ├─ fine.status = 'PAID'
       └─ fine.paid_at = now() → SAVE
```

---

## 5. Indexes Summary

| Index Name | Table | Column | Purpose |
|-----------|-------|--------|---------|
| `idx_users_role` | `library_users` | `role` | Filter members by role |
| `idx_books_isbn` | `books` | `isbn` | ISBN lookup |
| `idx_copies_accession` | `book_copies` | `accession_number` | Barcode scan |
| `idx_loans_user` | `loans` | `user_id` | My Loans, member history |
| `idx_loans_status` | `loans` | `status` | Overdue scan, status filters |
| `idx_fines_user` | `fines` | `user_id` | Fine summary per user |

---

## 6. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Django secret key |
| `DEBUG` | `True` | Set to `False` in production |
| `DB_NAME` | `university_library` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | *(required)* | PostgreSQL password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port (18→5432, 17→5433) |
| `FINE_PER_DAY` | `0.50` | Fine per overdue day (GHS) |
| `DEFAULT_LOAN_DAYS` | `14` | Standard loan duration |

---

## 7. Management Commands

| Command | Schedule | Description |
|---------|----------|-------------|
| `python manage.py migrate` | Deploy | Apply migrations |
| `python manage.py createsuperuser` | Deploy | Create librarian |
| `python manage.py seed_data` | Dev only | Demo data |
| `python manage.py mark_overdue_loans` | Hourly | Mark overdue + create fines |
| `python manage.py send_overdue_alerts` | Daily 8 AM | Notify borrowers |

**Crontab:**
```cron
0 * * * * /venv/bin/python /app/manage.py mark_overdue_loans
0 8 * * * /venv/bin/python /app/manage.py send_overdue_alerts
```

---

## 8. First-Time Setup

```bash
# 1. Create virtual environment
python3 -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DB_PASSWORD at minimum

# 4. Create the PostgreSQL database
# In psql: CREATE DATABASE university_library;

# 5. Apply migrations (creates all 5 tables + indexes)
python manage.py migrate

# 6. Create a superuser
python manage.py createsuperuser

# 7. Load sample data (optional)
python manage.py seed_data

# 8. Start server
python manage.py runserver
# → http://127.0.0.1:8000/
# → Admin: http://127.0.0.1:8000/admin/
```

---

## 9. Django Admin Quick Reference

| URL | Access | Purpose |
|-----|--------|---------|
| `/admin/` | Superuser | Full Django admin |
| `/accounts/login/` | Public | Login |
| `/accounts/register/` | Public | Self-register |
| `/catalog/` | Authenticated | Browse books |
| `/catalog/add/` | Staff | Add book |
| `/circulation/my-loans/` | Authenticated | Own loan history |
| `/circulation/loans/` | Staff | All loans |
| `/circulation/loans/issue/` | Staff | Issue a loan |
| `/circulation/fines/` | Staff | Fine management |
| `/reports/overdue/` | Staff | Overdue report |
| `/reports/stats/` | Staff | Borrowing statistics |
| `/reports/inventory/` | Staff | Inventory report |
| `/reports/fines/` | Staff | Fine summary |
