
# E-Commerce Inventory Management System

A Django-based E-Commerce Inventory Management System designed to manage products, inventory, suppliers, purchases, customer orders, and business operations through a centralized platform.

## Project Overview

The **E-Commerce Inventory Management System** is a web-based application developed using Python and Django. It provides an organized platform for managing e-commerce activities, inventory operations, and administrative tasks.

The project aims to simplify product management, inventory tracking, purchasing, order processing, and business reporting.

## Technologies Used

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Database:** SQLite
- **Version Control:** Git & GitHub

## Project Modules

| Module | Description |
|---|---|
| Accounts | User registration, authentication, and user management |
| Products | Product information and management |
| Categories | Product category management |
| Inventory | Inventory and stock management |
| Suppliers | Supplier information management |
| Purchases | Purchase record management |
| Cart | Shopping cart functionality |
| Orders | Customer order management |
| Reviews | Product review management |
| Dashboard | Dashboard and management overview |
| Reports | Business and inventory reports |
| Audit | Activity and audit record management |
| Home | Application homepage |

## Key Features

- User authentication and account management
- Product and category management
- Inventory and stock management
- Supplier management
- Purchase management
- Shopping cart functionality
- Order management
- Product reviews
- Dashboard for administrative operations
- Business and inventory reporting
- Audit record management

## Project Structure

```text
E_comerce_Website/
│
├── E_comerce_Website/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
├── audit/
├── cart/
├── categories/
├── dashboard/
├── home/
├── inventory/
├── orders/
├── products/
├── purchases/
├── reports/
├── reviews/
├── suppliers/
│
├── media/
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation and Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/EngineerHabib/DOKKHO-E_Commerce-Porject-SICIP.git
```

### 2. Navigate to the Project Directory

```bash
cd DOKKHO-E_Commerce-Porject-SICIP
```

### 3. Create a Virtual Environment

```bash
python -m venv Env
```

### 4. Activate the Virtual Environment

**Windows PowerShell:**

```powershell
Env\Scripts\Activate
```

### 5. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 6. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create an Admin Account

```bash
python manage.py createsuperuser
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open your browser and visit:

```text
http://127.0.0.1:8000/
```

## Database

The project uses SQLite as its development database.

Django ORM is used for database operations and model management.

## Version Control

This project is maintained using Git and hosted on GitHub.

**Repository:**  
https://github.com/EngineerHabib/DOKKHO-E_Commerce-Porject-SICIP

## Developer

**Md. Habibur Rahman**  
BSc in Computer Science and Engineering

- GitHub: [EngineerHabib](https://github.com/EngineerHabib)
- LinkedIn: [Habibur Rahman](https://www.linkedin.com/in/habiburrahman2001/)

---

**Developed as an E-Commerce Inventory Management Project under SICIP.**
