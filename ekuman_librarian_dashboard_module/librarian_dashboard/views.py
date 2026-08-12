from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from functools import wraps

from catalog.models import Book, Category, BookCopy
from accounts.models import User
from circulation.models import Loan, Fine
from .forms import BookForm, CategoryForm, UserManagementForm, FinePaymentForm

def librarian_access_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_librarian():
            return render(request, 'librarian/access_denied.html', {
                'member': request.user,
                'active_nav': 'none'
            })
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@librarian_access_required
def dashboard_overview(request):
    """Admin / Librarian Overview Dashboard"""
    total_books = Book.objects.count()
    total_copies = BookCopy.objects.count()
    total_available_copies = BookCopy.objects.filter(status='AVAILABLE').count()
    active_loans = Loan.objects.exclude(status='RETURNED').count()
    
    today = timezone.now().date()
    overdue_loans_count = Loan.objects.exclude(status='RETURNED').filter(due_date__lt=today).count()
    
    total_students = User.objects.filter(role='STUDENT').count()
    total_librarians = User.objects.filter(role='LIBRARIAN').count()
    
    unpaid_fines = Fine.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0.00
    
    low_stock_books = Book.objects.filter(available_copies__lte=1).order_by('available_copies')[:5]
    recent_loans = Loan.objects.select_related('borrower', 'book_copy__book').order_by('-issue_date')[:6]
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    context = {
        'total_books': total_books,
        'total_copies': total_copies,
        'total_available_copies': total_available_copies,
        'active_loans': active_loans,
        'overdue_loans_count': overdue_loans_count,
        'total_students': total_students,
        'total_librarians': total_librarians,
        'unpaid_fines': unpaid_fines,
        'low_stock_books': low_stock_books,
        'recent_loans': recent_loans,
        'recent_users': recent_users,
        'active_nav': 'dashboard',
    }
    return render(request, 'librarian/dashboard.html', context)


# ==========================================
# CATALOG MANAGEMENT VIEWS
# ==========================================

@login_required
@librarian_access_required
def book_list(request):
    """View and search book catalog"""
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    stock_status = request.GET.get('stock', '')

    books = Book.objects.select_related('category').all()

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(isbn__icontains=query) |
            Q(publisher__icontains=query)
        )

    if category_id:
        books = books.filter(category_id=category_id)

    if stock_status == 'available':
        books = books.filter(available_copies__gt=0)
    elif stock_status == 'out_of_stock':
        books = books.filter(available_copies=0)

    paginator = Paginator(books, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'selected_stock': stock_status,
        'total_count': books.count(),
        'active_nav': 'catalog',
    }
    return render(request, 'librarian/catalog/book_list.html', context)


@login_required
@librarian_access_required
def book_create(request):
    """Add a new book to the catalog"""
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            for i in range(1, book.total_copies + 1):
                accession_number = f"{book.isbn}-{i:03d}"
                BookCopy.objects.create(
                    book=book,
                    accession_number=accession_number,
                    status='AVAILABLE'
                )
            messages.success(request, f'Book "{book.title}" added successfully with {book.total_copies} copy(ies).')
            return redirect('librarian:book_detail', pk=book.pk)
    else:
        form = BookForm()

    return render(request, 'librarian/catalog/book_form.html', {
        'form': form,
        'title': 'Add New Book to Catalog',
        'active_nav': 'catalog',
    })


@login_required
@librarian_access_required
def book_update(request, pk):
    """Edit existing book details"""
    book = get_object_or_404(Book, pk=pk)
    old_copies = book.total_copies

    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            updated_book = form.save()
            if updated_book.total_copies > old_copies:
                for i in range(old_copies + 1, updated_book.total_copies + 1):
                    accession_number = f"{updated_book.isbn}-{i:03d}"
                    BookCopy.objects.create(
                        book=updated_book,
                        accession_number=accession_number,
                        status='AVAILABLE'
                    )
            messages.success(request, f'Book "{updated_book.title}" updated successfully.')
            return redirect('librarian:book_detail', pk=updated_book.pk)
    else:
        form = BookForm(instance=book)

    return render(request, 'librarian/catalog/book_form.html', {
        'form': form,
        'book': book,
        'title': f'Edit Book: {book.title}',
        'active_nav': 'catalog',
    })


@login_required
@librarian_access_required
def book_detail(request, pk):
    """View book details and copy inventory"""
    book = get_object_or_404(Book.objects.select_related('category'), pk=pk)
    copies = book.copies.all()
    active_loans = Loan.objects.filter(book_copy__book=book).exclude(status='RETURNED').select_related('borrower', 'book_copy')

    context = {
        'book': book,
        'copies': copies,
        'active_loans': active_loans,
        'active_nav': 'catalog',
    }
    return render(request, 'librarian/catalog/book_detail.html', context)


@login_required
@librarian_access_required
def book_delete(request, pk):
    """Delete a book from catalog"""
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'Book "{title}" deleted from catalog.')
        return redirect('librarian:book_list')

    return render(request, 'librarian/catalog/book_confirm_delete.html', {
        'book': book,
        'active_nav': 'catalog',
    })


# ==========================================
# USER MANAGEMENT VIEWS
# ==========================================

@login_required
@librarian_access_required
def user_list(request):
    """View and manage system users (Students and Librarians)"""
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    users = User.objects.all().order_by('-date_joined')

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(student_id__icontains=query) |
            Q(department__icontains=query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'suspended':
        users = users.filter(is_active=False)

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'total_users': users.count(),
        'active_nav': 'users',
    }
    return render(request, 'librarian/users/user_list.html', context)


@login_required
@librarian_access_required
def user_detail(request, pk):
    """Detailed view of user profile, loan history, and fines"""
    user_obj = get_object_or_404(User, pk=pk)
    
    current_loans = Loan.objects.filter(borrower=user_obj).exclude(status='RETURNED').select_related('book_copy__book')
    past_loans = Loan.objects.filter(borrower=user_obj, status='RETURNED').select_related('book_copy__book').order_by('-return_date')[:10]
    
    fines = Fine.objects.filter(loan__borrower=user_obj).select_related('loan__book_copy__book')
    total_unpaid_fine = fines.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0.00

    context = {
        'member': user_obj,
        'current_loans': current_loans,
        'past_loans': past_loans,
        'fines': fines,
        'total_unpaid_fine': total_unpaid_fine,
        'active_nav': 'users',
    }
    return render(request, 'librarian/users/user_detail.html', context)


@login_required
@librarian_access_required
def user_toggle_status(request, pk):
    """Toggle user active status (Activate / Suspend)"""
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        status_str = "activated" if user_obj.is_active else "suspended"
        messages.success(request, f'User account for {user_obj.username} has been {status_str}.')
        return redirect('librarian:user_detail', pk=user_obj.pk)

    return render(request, 'librarian/users/user_confirm_status.html', {
        'member': user_obj,
        'active_nav': 'users',
    })


@login_required
@librarian_access_required
def user_pay_fine(request, fine_id):
    """Mark a fine as paid or waived"""
    fine = get_object_or_404(Fine, pk=fine_id)
    if request.method == 'POST':
        form = FinePaymentForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action_type']
            if action == 'PAY':
                fine.is_paid = True
                fine.paid_at = timezone.now()
                fine.save()
                messages.success(request, f'Fine of ${fine.amount} paid successfully for {fine.loan.borrower.username}.')
            elif action == 'WAIVE':
                fine.is_paid = True
                fine.amount = 0.00
                fine.paid_at = timezone.now()
                fine.save()
                messages.info(request, f'Fine waived for {fine.loan.borrower.username}.')
            return redirect('librarian:user_detail', pk=fine.loan.borrower.pk)
    return redirect('librarian:user_list')


# ==========================================
# CIRCULATION & LOAN MANAGEMENT VIEWS
# ==========================================

@login_required
@librarian_access_required
def loan_list(request):
    """View all current active loans and process returns"""
    filter_type = request.GET.get('filter', 'all')
    loans = Loan.objects.select_related('borrower', 'book_copy__book').all().order_by('-issue_date')
    
    today = timezone.now().date()
    if filter_type == 'overdue':
        loans = loans.exclude(status='RETURNED').filter(due_date__lt=today)
    elif filter_type == 'active':
        loans = loans.exclude(status='RETURNED')
    elif filter_type == 'returned':
        loans = loans.filter(status='RETURNED')

    paginator = Paginator(loans, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'today': today,
        'active_nav': 'circulation',
    }
    return render(request, 'librarian/circulation/loan_list.html', context)


@login_required
@librarian_access_required
def loan_return(request, loan_id):
    """Mark a borrowed book as returned by librarian"""
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        if loan.status != 'RETURNED':
            loan.status = 'RETURNED'
            loan.return_date = timezone.now()
            loan.save()

            copy = loan.book_copy
            copy.status = 'AVAILABLE'
            copy.save()

            book = copy.book
            book.available_copies += 1
            book.save()

            if loan.return_date > loan.due_date:
                overdue_days = (loan.return_date - loan.due_date).days
                fine_amount = overdue_days * 0.50
                Fine.objects.create(loan=loan, amount=fine_amount, is_paid=False)
                messages.warning(request, f'Book returned. Generated overdue fine of ${fine_amount:.2f} ({overdue_days} days overdue).')
            else:
                messages.success(request, f'Book "{book.title}" marked as returned successfully.')

    return redirect('librarian:loan_list')
