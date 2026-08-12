from django.urls import path
from . import views

app_name = 'librarian'

urlpatterns = [
    # Dashboard Overview
    path('', views.dashboard_overview, name='dashboard'),

    # Catalog Management
    path('books/', views.book_list, name='book_list'),
    path('books/add/', views.book_create, name='book_create'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),
    path('books/<int:pk>/edit/', views.book_update, name='book_update'),
    path('books/<int:pk>/delete/', views.book_delete, name='book_delete'),

    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    path('fines/<int:fine_id>/pay/', views.user_pay_fine, name='user_pay_fine'),

    # Circulation Management
    path('circulation/', views.loan_list, name='loan_list'),
    path('circulation/<int:loan_id>/return/', views.loan_return, name='loan_return'),
]
