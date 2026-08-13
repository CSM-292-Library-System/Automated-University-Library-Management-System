-- =============================================================================
-- LIBRARY MANAGEMENT SYSTEM - DATABASE SCHEMA (PostgreSQL)
-- Entities: Users, Books, Book Copies, Loans, Fines
-- =============================================================================

-- 1. USERS TABLE
CREATE TABLE library_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL,
    other_names VARCHAR(150),
    surname VARCHAR(150) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'STUDENT' 
        CHECK (role IN ('STUDENT', 'LECTURER', 'OUTSIDER', 'STAFF')),
    phone_number VARCHAR(25),
    identification_number VARCHAR(50) UNIQUE NOT NULL, -- Student ID, Staff ID, or National ID
    is_active BOOLEAN DEFAULT TRUE,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- 2. BOOKS TABLE (Catalog Metadata)
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(13) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    publication_year INT CHECK (publication_year > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- 3. BOOK COPIES TABLE (Physical Inventory)
CREATE TABLE book_copies (
    id SERIAL PRIMARY KEY,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    accession_number VARCHAR(50) UNIQUE NOT NULL, -- Barcode/Tag
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE' 
        CHECK (status IN ('AVAILABLE', 'BORROWED', 'MAINTENANCE'))
);


-- 4. LOANS TABLE
CREATE TABLE loans (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES library_users(id) ON DELETE RESTRICT,
    book_copy_id INT NOT NULL REFERENCES book_copies(id) ON DELETE RESTRICT,
    borrow_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    return_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' 
        CHECK (status IN ('ACTIVE', 'RETURNED', 'OVERDUE'))
);



-- 5. FINES TABLE
CREATE TABLE fines (
    id SERIAL PRIMARY KEY,
    loan_id INT UNIQUE NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES library_users(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'UNPAID' 
        CHECK (status IN ('UNPAID', 'PAID')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP WITH TIME ZONE
);



-- INDEXES FOR OPTIMIZED QUERYING
CREATE INDEX idx_users_role ON library_users(role);
CREATE INDEX idx_books_isbn ON books(isbn);
CREATE INDEX idx_copies_accession ON book_copies(accession_number);
CREATE INDEX idx_loans_user ON loans(user_id);
CREATE INDEX idx_loans_status ON loans(status);
CREATE INDEX idx_fines_user ON fines(user_id);