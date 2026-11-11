-- ============================================================
-- BOOKSHOP DATABASE
-- DDL + INSERTS + VERIFICATION + QUERIES
-- ============================================================

DROP DATABASE IF EXISTS BookShop;
CREATE DATABASE BookShop;
USE BookShop;

-- ============================================================
-- 1) DDL - CREATE TABLES
-- ============================================================

CREATE TABLE Publisher (
    Publisherid VARCHAR(10) PRIMARY KEY,
    PublisherName VARCHAR(120) NOT NULL,
    PublisherAddress VARCHAR(255),
    PublisherPhone VARCHAR(40),
    URL VARCHAR(255)
);

CREATE TABLE Author (
    Authorid VARCHAR(10) PRIMARY KEY,
    AuthorName VARCHAR(120) NOT NULL,
    AuthorAddress VARCHAR(255)
);

CREATE TABLE Customer (
    emailCustomer VARCHAR(120) PRIMARY KEY,
    CustomerName VARCHAR(120) NOT NULL,
    CustomerPhone VARCHAR(40),
    CustomerAddress VARCHAR(255)
);

CREATE TABLE Warehouse (
    code VARCHAR(10) PRIMARY KEY,
    WarehousePhone VARCHAR(40),
    WarehouseAddress VARCHAR(255)
);

CREATE TABLE Book (
    isbn VARCHAR(20) PRIMARY KEY,
    year INT,
    title VARCHAR(200) NOT NULL,
    price DECIMAL(10,2),
    Publisherid VARCHAR(10) NOT NULL,
    Authorid VARCHAR(10) NOT NULL,

    CONSTRAINT fk_book_publisher
        FOREIGN KEY (Publisherid)
        REFERENCES Publisher(Publisherid),

    CONSTRAINT fk_book_author
        FOREIGN KEY (Authorid)
        REFERENCES Author(Authorid)
);

CREATE TABLE ShoppingBasket (
    ShoppingBasketid INT PRIMARY KEY,
    CustomerEmail VARCHAR(120) NOT NULL,

    CONSTRAINT fk_basket_customer
        FOREIGN KEY (CustomerEmail)
        REFERENCES Customer(emailCustomer)
);

CREATE TABLE ShoppingBaskets_have_Books (
    ShoppingBasketid INT NOT NULL,
    Book_ISBN VARCHAR(20) NOT NULL,
    `count` INT NOT NULL DEFAULT 1,

    PRIMARY KEY (ShoppingBasketid, Book_ISBN),

    CONSTRAINT fk_basketbook_basket
        FOREIGN KEY (ShoppingBasketid)
        REFERENCES ShoppingBasket(ShoppingBasketid),

    CONSTRAINT fk_basketbook_book
        FOREIGN KEY (Book_ISBN)
        REFERENCES Book(isbn)
);

CREATE TABLE Warehouses_have_Books (
    Warehousecode VARCHAR(10) NOT NULL,
    Book_ISBN VARCHAR(20) NOT NULL,
    `count` INT NOT NULL,

    PRIMARY KEY (Warehousecode, Book_ISBN),

    CONSTRAINT fk_warehousebook_warehouse
        FOREIGN KEY (Warehousecode)
        REFERENCES Warehouse(code),

    CONSTRAINT fk_warehousebook_book
        FOREIGN KEY (Book_ISBN)
        REFERENCES Book(isbn)
);

-- ============================================================
-- 2) INSERTS
-- ============================================================

-- a) Publisher
INSERT INTO Publisher
(Publisherid, PublisherName, PublisherAddress, PublisherPhone, URL)
VALUES
('P01', 'Penguin Random House', 'Luchana 23 Madrid Spain',
 '+34915358190', 'http://www.penguinrandomhouse.com/'),
('P02', 'Hachette Livre', '50 Victoria Embankment',
 '+4402031227000', 'https://www.hachette.com'),
('P03', 'HarperCollins',
 'The News Building London Bridge Street London United Kingdom',
 '1-800-242-7737', 'https://www.harpercollins.com/');

-- b) Author
INSERT INTO Author
(Authorid, AuthorName, AuthorAddress)
VALUES
('A01', 'Cat Sebastian', '9296 Henry St. Auburndale, FL 33823'),
('A02', 'Lorraine Heath', '974 Broad Dr. Marcus Hook, PA 19061'),
('A03', 'Jill Shalvis', '187 Cherry Rd. Reston, VA 20191'),
('A04', 'Kevin Kwan', '13 Locust St. Round Lake, IL 60073'),
('A05', 'Elisabeth Noreback', '26 Rock Creek Dr. Tuscaloosa, AL 35405'),
('A06', 'Pamela Brown', '409 Santa Clara Ave. Cedar Rapids, IA 52402');

-- c) HarperCollins = P03
INSERT INTO Book
(isbn, title, year, price, Publisherid, Authorid)
VALUES
('9706279318', 'A Gentleman Never Keeps Score', 2018, 384.00, 'P03', 'A01'),
('9728304828', 'Texas Glory', 2015, 94.00, 'P03', 'A02'),
('9702833373', 'Rainy day friends', 2017, 45.00, 'P03', 'A03');

-- d) Penguin Random House = P01
-- The exercise does not provide year or price for these three records.
INSERT INTO Book
(isbn, title, year, price, Publisherid, Authorid)
VALUES
('9703859383', 'Crazy Rich Asians', NULL, NULL, 'P01', 'A04'),
('9793937483', 'Tell me you''re mine', NULL, NULL, 'P01', 'A05'),
('9729473047', 'The spy and the traitor', NULL, NULL, 'P01', 'A05');

-- e) Hachette Livre = P02
INSERT INTO Book
(isbn, title, year, price, Publisherid, Authorid)
VALUES
('9703746264', 'Paradise Sky by Joe Lansdale: The Illustrated Edition',
 2016, 145.00, 'P02', 'A06'),
('9739482733', 'Meet Camaro from The Night Charter',
 2010, 165.00, 'P02', 'A06');

-- f) Customer
INSERT INTO Customer
(emailCustomer, CustomerName, CustomerPhone, CustomerAddress)
VALUES
('emkw@mail.com', 'Karol Wilson', '+5552115099561',
 '75 Poplar Court Eugene OR 97402'),
('rior@mail.com', 'Richard Orson', '+550445528305',
 '33 Richardson Dr. Chandler AZ 85224'),
('lowi@mail.com', 'Loraine Williams', '+440102211600',
 '8 Market St. Portsmouth VA 23703'),
('sclu@mail.com', 'Scott Luka', '+44193649373',
 '412 Pawnee Lane Kenosha, WI 53140');

-- g) Warehouse
INSERT INTO Warehouse
(code, WarehousePhone, WarehouseAddress)
VALUES
('WA01', '+555215393544',
 '530 Roosevelt Lane Hopewell Junction NY 12533'),
('WA02', '+443939759583',
 '9592 Applegate Road Bedford OH 44146'),
('WA03', '+349385958484',
 '21 Arch Ave. Grand Haven MI 49417');

-- h) Shopping baskets
INSERT INTO ShoppingBasket
(ShoppingBasketid, CustomerEmail)
VALUES
(1, 'emkw@mail.com'),
(2, 'rior@mail.com'),
(3, 'lowi@mail.com'),
(4, 'sclu@mail.com');

-- Karol Wilson
INSERT INTO ShoppingBaskets_have_Books
(ShoppingBasketid, Book_ISBN, `count`)
VALUES
(1, '9706279318', 1),
(1, '9703746264', 1),
(1, '9729473047', 1);

-- Richard Orson
INSERT INTO ShoppingBaskets_have_Books
(ShoppingBasketid, Book_ISBN, `count`)
VALUES
(2, '9739482733', 1),
(2, '9728304828', 1),
(2, '9702833373', 1),
(2, '9703859383', 1);

-- Loraine Williams
INSERT INTO ShoppingBaskets_have_Books
(ShoppingBasketid, Book_ISBN, `count`)
VALUES
(3, '9793937483', 1),
(3, '9703859383', 1),
(3, '9702833373', 1);

-- Scott Luka
INSERT INTO ShoppingBaskets_have_Books
(ShoppingBasketid, Book_ISBN, `count`)
VALUES
(4, '9739482733', 1),
(4, '9702833373', 1),
(4, '9729473047', 1),
(4, '9793937483', 1);

-- i) Warehouse stock
INSERT INTO Warehouses_have_Books
(Warehousecode, Book_ISBN, `count`)
VALUES
('WA01', '9728304828', 15),
('WA01', '9739482733', 29),
('WA01', '9729473047', 151),
('WA02', '9703859383', 20),
('WA02', '9793937483', 383),
('WA02', '9706279318', 293),
('WA03', '9702833373', 393),
('WA03', '9729473047', 38),
('WA03', '9706279318', 48),
('WA03', '9739482733', 29);

-- ============================================================
-- 3) INSERT VERIFICATION
-- Execute these and take screenshots for the rubric.
-- ============================================================

SELECT * FROM Publisher;
SELECT * FROM Author;
SELECT * FROM Book;
SELECT * FROM Customer;
SELECT * FROM Warehouse;
SELECT * FROM ShoppingBasket;
SELECT * FROM ShoppingBaskets_have_Books;
SELECT * FROM Warehouses_have_Books;

-- Compact count verification:
SELECT 'Publisher' AS table_name, COUNT(*) AS rows_inserted FROM Publisher
UNION ALL
SELECT 'Author', COUNT(*) FROM Author
UNION ALL
SELECT 'Book', COUNT(*) FROM Book
UNION ALL
SELECT 'Customer', COUNT(*) FROM Customer
UNION ALL
SELECT 'Warehouse', COUNT(*) FROM Warehouse
UNION ALL
SELECT 'ShoppingBasket', COUNT(*) FROM ShoppingBasket
UNION ALL
SELECT 'ShoppingBaskets_have_Books', COUNT(*) FROM ShoppingBaskets_have_Books
UNION ALL
SELECT 'Warehouses_have_Books', COUNT(*) FROM Warehouses_have_Books;

-- Expected counts:
-- Publisher = 3
-- Author = 6
-- Book = 8
-- Customer = 4
-- Warehouse = 3
-- ShoppingBasket = 4
-- ShoppingBaskets_have_Books = 14
-- Warehouses_have_Books = 10

-- ============================================================
-- 4) REQUIRED QUERIES
-- ============================================================

-- 1) Which book is being sold more right now?
SELECT
    b.title,
    SUM(sbb.`count`) AS quantity_in_baskets
FROM ShoppingBaskets_have_Books sbb
JOIN Book b
    ON b.isbn = sbb.Book_ISBN
GROUP BY b.isbn, b.title
ORDER BY quantity_in_baskets DESC
LIMIT 1;

-- Expected: Rainy day friends | 3


-- 2) Which customer is buying more books?
WITH customer_totals AS (
    SELECT
        c.emailCustomer,
        c.CustomerName,
        SUM(sbb.`count`) AS total_books
    FROM Customer c
    JOIN ShoppingBasket sb
        ON sb.CustomerEmail = c.emailCustomer
    JOIN ShoppingBaskets_have_Books sbb
        ON sbb.ShoppingBasketid = sb.ShoppingBasketid
    GROUP BY c.emailCustomer, c.CustomerName
)
SELECT
    CustomerName,
    total_books
FROM customer_totals
WHERE total_books = (
    SELECT MAX(total_books)
    FROM customer_totals
);

-- Expected:
-- Richard Orson | 4
-- Scott Luka    | 4


-- 3) Which warehouse has Texas Glory in stock?
SELECT
    w.code AS WarehouseCode,
    w.WarehouseAddress,
    whb.`count` AS Stock
FROM Warehouse w
JOIN Warehouses_have_Books whb
    ON whb.Warehousecode = w.code
JOIN Book b
    ON b.isbn = whb.Book_ISBN
WHERE b.title = 'Texas Glory'
  AND whb.`count` > 0;

-- Expected: WA01 | ... | 15


-- 4) Which author has more books on sale?
-- Here "books on sale" is interpreted as distinct book titles offered by the BookShop.
WITH author_totals AS (
    SELECT
        a.Authorid,
        a.AuthorName,
        COUNT(b.isbn) AS total_books
    FROM Author a
    LEFT JOIN Book b
        ON b.Authorid = a.Authorid
    GROUP BY a.Authorid, a.AuthorName
)
SELECT
    AuthorName,
    total_books
FROM author_totals
WHERE total_books = (
    SELECT MAX(total_books)
    FROM author_totals
);

-- Expected:
-- Elisabeth Noreback | 2
-- Pamela Brown       | 2


-- 5) Which publisher offers less books?
WITH publisher_totals AS (
    SELECT
        p.Publisherid,
        p.PublisherName,
        COUNT(b.isbn) AS total_books
    FROM Publisher p
    LEFT JOIN Book b
        ON b.Publisherid = p.Publisherid
    GROUP BY p.Publisherid, p.PublisherName
)
SELECT
    PublisherName,
    total_books
FROM publisher_totals
WHERE total_books = (
    SELECT MIN(total_books)
    FROM publisher_totals
);

-- Expected: Hachette Livre | 2
