import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hardgo.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            role TEXT CHECK(role IN ('customer', 'shop_owner', 'delivery_partner', 'admin')) NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # 2. Shops table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            locality TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            rating REAL DEFAULT 4.5,
            is_active INTEGER DEFAULT 1,
            prep_time_mins INTEGER DEFAULT 10,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    # 3. Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL
        );
    ''')

    # 4. Products master catalog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            image_url TEXT,
            base_price REAL NOT NULL,
            unit TEXT DEFAULT 'unit',
            tags TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
    ''')

    # 5. Shop Products (Inventory per shop)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            is_available INTEGER DEFAULT 1,
            UNIQUE(shop_id, product_id),
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        );
    ''')

    # 6. Customer Addresses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'Home',
            address_line TEXT NOT NULL,
            locality TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            is_default INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    # 7. Delivery Partners table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS delivery_partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle_type TEXT DEFAULT 'Bike',
            vehicle_number TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            is_online INTEGER DEFAULT 1,
            is_available INTEGER DEFAULT 1,
            rating REAL DEFAULT 4.8,
            total_earnings REAL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    # 8. Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            shop_id INTEGER NOT NULL,
            delivery_partner_id INTEGER,
            status TEXT CHECK(status IN (
                'Order Placed',
                'Shop Accepted',
                'Preparing',
                'Ready for Pickup',
                'Picked Up',
                'On the Way',
                'Delivered',
                'Rejected'
            )) DEFAULT 'Order Placed',
            total_amount REAL NOT NULL,
            delivery_fee REAL DEFAULT 20.0,
            distance_km REAL NOT NULL,
            estimated_delivery_mins INTEGER NOT NULL,
            payment_method TEXT DEFAULT 'COD',
            payment_status TEXT DEFAULT 'Pending',
            delivery_address TEXT NOT NULL,
            customer_lat REAL NOT NULL,
            customer_lng REAL NOT NULL,
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (shop_id) REFERENCES shops(id),
            FOREIGN KEY (delivery_partner_id) REFERENCES delivery_partners(id)
        );
    ''')

    # 9. Order Items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')

    # 10. Deliveries tracking log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER UNIQUE NOT NULL,
            partner_id INTEGER NOT NULL,
            pickup_lat REAL NOT NULL,
            pickup_lng REAL NOT NULL,
            drop_lat REAL NOT NULL,
            drop_lng REAL NOT NULL,
            status TEXT DEFAULT 'Assigned',
            accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            picked_at TIMESTAMP,
            delivered_at TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (partner_id) REFERENCES delivery_partners(id)
        );
    ''')

    # 11. Sales History for AI Demand Prediction
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            sale_date DATE NOT NULL,
            FOREIGN KEY (shop_id) REFERENCES shops(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')

    # 12. Search History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Keep existing databases in sync with the real product photos too.
    product_image_urls = {
        1: 'https://commons.wikimedia.org/wiki/Special:FilePath/LED%20bulbs.jpg',
        2: 'https://commons.wikimedia.org/wiki/Special:FilePath/LED%20bulbs.jpg',
        3: 'https://commons.wikimedia.org/wiki/Special:FilePath/A%20socket%20switch.jpg',
        4: 'https://commons.wikimedia.org/wiki/Special:FilePath/A%20socket%20switch.jpg',
        5: 'https://commons.wikimedia.org/wiki/Special:FilePath/Electric%20Socket.jpeg',
        6: 'https://commons.wikimedia.org/wiki/Special:FilePath/Copper%20wires.JPG',
        7: 'https://commons.wikimedia.org/wiki/Special:FilePath/Copper%20wires.JPG',
        8: 'https://commons.wikimedia.org/wiki/Special:FilePath/Charger%20image.jpg',
        9: 'https://commons.wikimedia.org/wiki/Special:FilePath/Samsung%20Travel%20Adapter.jpg',
        10: 'https://commons.wikimedia.org/wiki/Special:FilePath/Extensioncord.jpg',
        11: 'https://commons.wikimedia.org/wiki/Special:FilePath/9v%20battery%20and%20led%20circuit%20components%20%28wires%2C%20battery%2C%20LED%2C%20resistor%29.jpg',
        12: 'https://commons.wikimedia.org/wiki/Special:FilePath/Soldering%20iron%20and%20accessories.jpg',
        13: 'https://commons.wikimedia.org/wiki/Special:FilePath/Multimetr.jpg',
        14: 'https://commons.wikimedia.org/wiki/Special:FilePath/Dht11.jpg',
        15: 'https://commons.wikimedia.org/wiki/Special:FilePath/NodeMCU%20DEVKIT%201.0%20BETA%20back.JPG',
    }
    for product_id, image_url in product_image_urls.items():
        cursor.execute('UPDATE products SET image_url = ? WHERE id = ?', (image_url, product_id))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database schema initialized successfully.")
