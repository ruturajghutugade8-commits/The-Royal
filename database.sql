CREATE DATABASE IF NOT EXISTS sweet_bites;
USE sweet_bites;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    image VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'Placed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

INSERT INTO products (name, description, price, image) VALUES
('Chocolate Truffle Cake', 'Rich chocolate cake with smooth truffle frosting.', 599.00, 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800'),
('Red Velvet Cake', 'Soft red velvet sponge with cream cheese frosting.', 649.00, 'https://images.unsplash.com/photo-1586788224331-947f68671cf1?w=800'),
('Black Forest Cake', 'Classic chocolate sponge with cherries and cream.', 549.00, 'https://images.unsplash.com/photo-1606890737304-57a1ca8a5b62?w=800'),
('Butterscotch Cake', 'Creamy butterscotch cake with caramel crunch.', 499.00, 'https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800');
