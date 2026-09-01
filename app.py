from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


# ================= DATABASE CONFIG =================

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "dbname": os.getenv("DB_NAME")
}


def get_db():
    return psycopg2.connect(**DB_CONFIG)


def query_db(query, params=(), fetch=False):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(query, params)

        if fetch:
            return cursor.fetchall()

        conn.commit()

        if cursor.description:
            result = cursor.fetchone()
            return result["id"] if result and "id" in result else None

        return None

    finally:
        cursor.close()
        conn.close()


# ================= ADMIN CHECK =================

def admin_required():
    return "user_id" in session and session.get("is_admin") is True


# ================= HOME =================

@app.route("/")
def home():
    products = query_db(
        "SELECT * FROM products ORDER BY id DESC",
        fetch=True
    )

    return render_template("index.html", products=products)


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            flash("Enter valid details. Password must be at least 6 characters.")
            return redirect(url_for("register"))

        if query_db(
            "SELECT id FROM users WHERE email=%s",
            (email,),
            fetch=True
        ):
            flash("Email already registered.")
            return redirect(url_for("register"))

        query_db(
            """
            INSERT INTO users(name, email, password_hash)
            VALUES(%s, %s, %s)
            """,
            (
                name,
                email,
                generate_password_hash(password)
            )
        )

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        users = query_db(
            "SELECT * FROM users WHERE email=%s",
            (email,),
            fetch=True
        )

        if users and check_password_hash(
            users[0]["password_hash"],
            password
        ):

            session["user_id"] = users[0]["id"]
            session["user_name"] = users[0]["name"]
            session["is_admin"] = bool(users[0]["is_admin"])

            return redirect(
                url_for("admin_dashboard")
                if session["is_admin"]
                else url_for("home")
            )

        flash("Invalid email or password.")

    return render_template("login.html")


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ================= CART =================

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):

    product = query_db(
        "SELECT * FROM products WHERE id=%s",
        (product_id,),
        fetch=True
    )

    if not product:
        flash("Product not found.")
        return redirect(url_for("home"))

    cart = session.get("cart", {})

    key = str(product_id)

    cart[key] = cart.get(key, 0) + 1

    session["cart"] = cart

    flash("Added to cart.")

    return redirect(url_for("cart"))


@app.route("/cart")
def cart():

    cart_data = session.get("cart", {})

    items = []
    total = 0

    for product_id, quantity in cart_data.items():

        products = query_db(
            "SELECT * FROM products WHERE id=%s",
            (int(product_id),),
            fetch=True
        )

        if products:

            product = products[0]

            subtotal = float(product["price"]) * quantity

            product["quantity"] = quantity
            product["subtotal"] = subtotal

            items.append(product)

            total += subtotal

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


@app.route("/remove-from-cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):

    cart = session.get("cart", {})

    cart.pop(str(product_id), None)

    session["cart"] = cart

    return redirect(url_for("cart"))


# ================= CHECKOUT =================

@app.route("/checkout", methods=["POST"])
def checkout():

    if "user_id" not in session:
        flash("Please login before checkout.")
        return redirect(url_for("login"))

    cart_data = session.get("cart", {})

    if not cart_data:
        flash("Your cart is empty.")
        return redirect(url_for("cart"))

    total = 0

    order_items = []

    for product_id, quantity in cart_data.items():

        products = query_db(
            "SELECT * FROM products WHERE id=%s",
            (int(product_id),),
            fetch=True
        )

        if products:

            product = products[0]

            subtotal = float(product["price"]) * quantity

            total += subtotal

            order_items.append(
                (
                    product["id"],
                    quantity,
                    subtotal
                )
            )

    # PostgreSQL uses RETURNING id instead of MySQL lastrowid
    order_id = query_db(
        """
        INSERT INTO orders(user_id, total_amount, status)
        VALUES(%s, %s, %s)
        RETURNING id
        """,
        (
            session["user_id"],
            total,
            "Placed"
        )
    )

    for product_id, quantity, subtotal in order_items:

        query_db(
            """
            INSERT INTO order_items(
                order_id,
                product_id,
                quantity,
                subtotal
            )
            VALUES(%s, %s, %s, %s)
            """,
            (
                order_id,
                product_id,
                quantity,
                subtotal
            )
        )

    session["cart"] = {}

    flash(f"Order #{order_id} placed successfully.")

    return redirect(url_for("orders"))


# ================= USER ORDERS =================

@app.route("/orders")
def orders():

    if "user_id" not in session:
        return redirect(url_for("login"))

    orders_list = query_db(
        """
        SELECT *
        FROM orders
        WHERE user_id=%s
        ORDER BY created_at DESC
        """,
        (session["user_id"],),
        fetch=True
    )

    return render_template(
        "orders.html",
        orders=orders_list
    )


# ============================================================
#                         ADMIN
# ============================================================

@app.route("/admin")
def admin_dashboard():

    if not admin_required():
        flash("Admin access required.")
        return redirect(url_for("home"))

    stats = {

        "users": query_db(
            "SELECT COUNT(*) AS total FROM users",
            fetch=True
        )[0]["total"],

        "products": query_db(
            "SELECT COUNT(*) AS total FROM products",
            fetch=True
        )[0]["total"],

        "orders": query_db(
            "SELECT COUNT(*) AS total FROM orders",
            fetch=True
        )[0]["total"],

        "revenue": query_db(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE status NOT IN ('Cancelled')
            """,
            fetch=True
        )[0]["total"]
    }

    recent_orders = query_db(
        """
        SELECT
            o.id,
            u.name AS customer_name,
            o.total_amount,
            o.status,
            o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 10
        """,
        fetch=True
    )

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        recent_orders=recent_orders
    )


# ================= ADMIN USERS =================

@app.route("/admin/users")
def admin_users():

    if not admin_required():
        flash("Admin access required.")
        return redirect(url_for("home"))

    users = query_db(
        """
        SELECT
            id,
            name,
            email,
            is_admin,
            created_at
        FROM users
        ORDER BY created_at DESC
        """,
        fetch=True
    )

    return render_template(
        "admin_users.html",
        users=users
    )


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id):

    if not admin_required():
        return redirect(url_for("home"))

    if user_id == session.get("user_id"):

        flash("You cannot delete your own admin account.")

        return redirect(url_for("admin_users"))

    query_db(
        "DELETE FROM users WHERE id=%s",
        (user_id,)
    )

    flash("User deleted.")

    return redirect(url_for("admin_users"))


# ================= ADMIN PRODUCTS =================

@app.route("/admin/products")
def admin_products():

    if not admin_required():
        flash("Admin access required.")
        return redirect(url_for("home"))

    products = query_db(
        "SELECT * FROM products ORDER BY id DESC",
        fetch=True
    )

    return render_template(
        "admin_products.html",
        products=products
    )


@app.route("/admin/products/add", methods=["GET", "POST"])
def add_product():

    if not admin_required():
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "")
        image = request.form.get("image", "").strip()

        try:

            price = float(price)

            if not name or price <= 0:
                raise ValueError

        except ValueError:

            flash("Enter a valid product name and positive price.")

            return redirect(url_for("add_product"))

        query_db(
            """
            INSERT INTO products(
                name,
                description,
                price,
                image
            )
            VALUES(%s, %s, %s, %s)
            """,
            (
                name,
                description,
                price,
                image
            )
        )

        flash("Product added.")

        return redirect(url_for("admin_products"))

    return render_template(
        "product_form.html",
        product=None
    )


@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    if not admin_required():
        return redirect(url_for("home"))

    products = query_db(
        "SELECT * FROM products WHERE id=%s",
        (product_id,),
        fetch=True
    )

    if not products:

        flash("Product not found.")

        return redirect(url_for("admin_products"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "")
        image = request.form.get("image", "").strip()

        try:

            price = float(price)

            if not name or price <= 0:
                raise ValueError

        except ValueError:

            flash("Enter valid product details.")

            return redirect(
                url_for(
                    "edit_product",
                    product_id=product_id
                )
            )

        query_db(
            """
            UPDATE products
            SET
                name=%s,
                description=%s,
                price=%s,
                image=%s
            WHERE id=%s
            """,
            (
                name,
                description,
                price,
                image,
                product_id
            )
        )

        flash("Product updated.")

        return redirect(url_for("admin_products"))

    return render_template(
        "product_form.html",
        product=products[0]
    )


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):

    if not admin_required():
        return redirect(url_for("home"))

    query_db(
        "DELETE FROM products WHERE id=%s",
        (product_id,)
    )

    flash("Product deleted.")

    return redirect(url_for("admin_products"))


# ================= ADMIN ORDERS =================

@app.route("/admin/orders")
def admin_orders():

    if not admin_required():
        return redirect(url_for("home"))

    orders = query_db(
        """
        SELECT
            o.id,
            u.name AS customer_name,
            u.email AS customer_email,
            o.total_amount,
            o.status,
            o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        """,
        fetch=True
    )

    return render_template(
        "admin_orders.html",
        orders=orders
    )


@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):

    if not admin_required():
        return redirect(url_for("home"))

    orders = query_db(
        """
        SELECT
            o.id,
            o.total_amount,
            o.status,
            o.created_at,
            u.name AS customer_name,
            u.email AS customer_email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id=%s
        """,
        (order_id,),
        fetch=True
    )

    if not orders:

        flash("Order not found.")

        return redirect(url_for("admin_orders"))

    items = query_db(
        """
        SELECT
            p.name AS product_name,
            oi.quantity,
            oi.subtotal
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id=%s
        """,
        (order_id,),
        fetch=True
    )

    return render_template(
        "admin_order_detail.html",
        order=orders[0],
        items=items
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
def admin_update_order_status(order_id):

    if not admin_required():
        return redirect(url_for("home"))

    status = request.form.get("status", "")

    allowed = {
        "Placed",
        "Processing",
        "Shipped",
        "Delivered",
        "Cancelled"
    }

    if status not in allowed:

        flash("Invalid order status.")

        return redirect(
            url_for(
                "admin_order_detail",
                order_id=order_id
            )
        )

    query_db(
        "UPDATE orders SET status=%s WHERE id=%s",
        (status, order_id)
    )

    flash("Order status updated.")

    return redirect(
        url_for(
            "admin_order_detail",
            order_id=order_id
        )
    )


# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)