from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from catalog.models import Book, Category, BookCopy
from circulation.models import Loan, Fine
from datetime import timedelta

class LibrarianDashboardTests(TestCase):
    def setUp(self):
        # Create Category
        self.category = Category.objects.create(name="Computer Science", icon_name="bi-code-slash")
        
        # Create Librarian User
        self.librarian = User.objects.create_user(
            username='lib_admin',
            email='admin@library.edu',
            password='password123',
            role='LIBRARIAN',
            is_staff=True
        )
        
        # Create Student User
        self.student = User.objects.create_user(
            username='student1',
            email='student1@library.edu',
            password='password123',
            role='STUDENT',
            student_id='STU1001',
            department='Computer Engineering'
        )

        # Create Book
        self.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            isbn="978-0132350884",
            category=self.category,
            total_copies=3,
            available_copies=2
        )
        self.copy = BookCopy.objects.create(book=self.book, accession_number="978-0132350884-001", status="BORROWED")

        # Create Loan for activity display
        self.loan = Loan.objects.create(
            borrower=self.student,
            book_copy=self.copy,
            issue_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=14),
            status='ACTIVE'
        )

        self.client = Client()

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated user accessing librarian dashboard is redirected to login"""
        response = self.client.get(reverse('librarian:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_student_access_denied(self):
        """Student role attempting to access librarian dashboard sees student notice page"""
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('librarian:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Access Notice")

    def test_librarian_dashboard_overview_accessible(self):
        """Librarian can view dashboard overview with metrics"""
        self.client.login(username='lib_admin', password='password123')
        response = self.client.get(reverse('librarian:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Library Management Dashboard")
        self.assertContains(response, "Clean Code")

    def test_catalog_book_list(self):
        """Librarian can list and search books"""
        self.client.login(username='lib_admin', password='password123')
        response = self.client.get(reverse('librarian:book_list') + '?q=Clean')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clean Code")

    def test_book_creation(self):
        """Librarian can add a new book"""
        self.client.login(username='lib_admin', password='password123')
        response = self.client.post(reverse('librarian:book_create'), {
            'title': 'Design Patterns',
            'author': 'Erich Gamma',
            'isbn': '978-0201633610',
            'category': self.category.pk,
            'publisher': 'Addison-Wesley',
            'publication_year': 1994,
            'total_copies': 2,
            'available_copies': 2,
            'description': 'Elements of Reusable Object-Oriented Software',
        })
        self.assertEqual(Book.objects.filter(isbn='978-0201633610').exists(), True)
        book = Book.objects.get(isbn='978-0201633610')
        self.assertEqual(BookCopy.objects.filter(book=book).count(), 2)

    def test_user_list_and_detail(self):
        """Librarian can view student list and individual detail profile"""
        self.client.login(username='lib_admin', password='password123')
        response = self.client.get(reverse('librarian:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "STU1001")

        detail_response = self.client.get(reverse('librarian:user_detail', kwargs={'pk': self.student.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Computer Engineering")

    def test_user_toggle_status(self):
        """Librarian can suspend and reactivate student access"""
        self.client.login(username='lib_admin', password='password123')
        response = self.client.post(reverse('librarian:user_toggle_status', kwargs={'pk': self.student.pk}))
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
