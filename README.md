# Sweet Bites - Updated Admin Edition

## Stack
Frontend: HTML, CSS
Backend: Python + Flask
Database: MySQL

## Admin features
- Admin dashboard
- Total users
- Total products
- Total orders
- Total revenue
- View all users
- Delete users (except current admin)
- Product CRUD
- View all orders
- View complete order details
- See customer name/email and ordered products
- Update order status: Placed, Processing, Shipped, Delivered, Cancelled
- Recent orders dashboard

## Run
1. Make sure MySQL80 is running.
2. MySQL port in this project is configured as 3307.
3. Open app.py and replace YOUR_MYSQL_PASSWORD with your MySQL root password.
4. If database/tables are not already created, run database.sql in MySQL Workbench.
5. Activate your virtual environment:
   venv\Scripts\activate
6. Install:
   pip install -r requirements.txt
7. Run:
   python app.py
8. Open:
   http://127.0.0.1:5000

## Make your registered account an admin
After registering:
UPDATE users SET is_admin = TRUE WHERE email = 'your_email@example.com';

Then logout and login again.

## Important
This is a portfolio/learning project. For production, add CSRF protection, environment variables for secrets, stricter authorization, audit logging, secure deployment, payment integration and image upload validation.
