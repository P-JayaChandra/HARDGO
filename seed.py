import datetime
import random
from database import init_db, get_db_connection

def seed_database():
    print("Initializing Database...")
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data cleanly
    tables = ['search_history', 'sales_history', 'deliveries', 'order_items', 'orders',
              'delivery_partners', 'addresses', 'shop_products', 'products', 'categories', 'shops', 'users']
    for t in tables:
        cursor.execute(f"DELETE FROM {t};")
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}';")

    print("Seeding Users...")
    # Users
    users_data = [
        ('Ravi Kumar', 'customer@hardgo.com', '9848022338', 'customer', 'pass123'),
        ('Anitha Reddy', 'anitha@hardgo.com', '9848011223', 'customer', 'pass123'),
        ('Srinivas Rao (Sri Sai)', 'srisai@hardgo.com', '9440188776', 'shop_owner', 'pass123'),
        ('K. V. Lakshmi', 'lakshmi@hardgo.com', '9440299887', 'shop_owner', 'pass123'),
        ('Venkateswarlu M.', 'swathi@hardgo.com', '9440377665', 'shop_owner', 'pass123'),
        ('Raju Express', 'raju@hardgo.com', '9701144556', 'delivery_partner', 'pass123'),
        ('Suresh Speed Delivery', 'suresh@hardgo.com', '9701166778', 'delivery_partner', 'pass123'),
        ('HardGo Admin', 'admin@hardgo.com', '9999999999', 'admin', 'admin123')
    ]
    cursor.executemany(
        "INSERT INTO users (name, email, phone, role, password) VALUES (?, ?, ?, ?, ?)",
        users_data
    )

    # Fetch User IDs
    cursor.execute("SELECT id, email FROM users")
    user_map = {row['email']: row['id'] for row in cursor.fetchall()}

    print("Seeding Shops in Vijayawada...")
    # Vijayawada Center coordinates: Benz Circle ~ (16.5062, 80.6480)
    shops_data = [
        (user_map['srisai@hardgo.com'], 'Sri Sai Electricals', '9440188776',
         'Shop #12, M.G. Road, Near Executive Club', 'M.G. Road', 16.5020, 80.6430, 4.8, 1, 8,
         '/static/images/products/product_1.svg'),

        (user_map['lakshmi@hardgo.com'], 'Lakshmi Electricals & Hardware', '9440299887',
         'Door #40-1-5, Benz Circle Main Road', 'Benz Circle', 16.5090, 80.6550, 4.6, 1, 12,
         '/static/images/products/product_1.svg'),

        (user_map['swathi@hardgo.com'], 'Swathi Electronics & Components', '9440377665',
         'Opp. City Bus Port, Governorpet', 'Governorpet', 16.5160, 80.6280, 4.7, 1, 10,
         '/static/images/products/product_1.svg')
    ]
    cursor.executemany("""
        INSERT INTO shops (owner_id, name, phone, address, locality, lat, lng, rating, is_active, prep_time_mins, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, shops_data)

    print("Seeding Categories...")
    categories_data = [
        ('LED Bulbs', 'fa-lightbulb', 'led-bulbs'),
        ('Switches', 'fa-toggle-on', 'switches'),
        ('Sockets', 'fa-plug', 'sockets'),
        ('Wires & Cables', 'fa-network-wired', 'wires-cables'),
        ('Chargers', 'fa-battery-charging', 'chargers'),
        ('Adapters', 'fa-charging-station', 'adapters'),
        ('Extension Boards', 'fa-sliders-h', 'extension-boards'),
        ('Batteries', 'fa-battery-full', 'batteries'),
        ('Plugs', 'fa-power-off', 'plugs'),
        ('Electrical Tools', 'fa-tools', 'electrical-tools'),
        ('Sensors', 'fa-microchip', 'sensors'),
        ('Electronic Components', 'fa-memory', 'electronic-components'),
        ('Fans & Accessories', 'fa-fan', 'fans-accessories'),
        ('Smart Home Devices', 'fa-wifi', 'smart-home')
    ]
    cursor.executemany(
        "INSERT INTO categories (name, icon, slug) VALUES (?, ?, ?)",
        categories_data
    )

    print("Seeding Master Products Catalog...")
    products_data = [
        # LED Bulbs (cat_id: 1)
        ('12W LED Bulb B22 Cool Day White', 1, 'Energy efficient 12 Watt LED bulb with 1200 lumens output and 2-year warranty.',
         '/static/images/products/product_1.svg', 120.0, 'unit', 'led bulb 12w 12 watt light b22'),

        ('9W Smart Color RGB LED Bulb', 1, 'Wi-Fi enabled 9W RGB smart bulb compatible with Alexa and Google Assistant.',
         '/static/images/products/product_1.svg', 399.0, 'unit', 'smart bulb rgb led wifi alexa'),

        # Switches (cat_id: 2)
        ('6A 1-Way Modular Switch White', 2, 'Sleek fire-retardant polycarbonate 6 Amp modular switch.',
         '/static/images/products/product_1.svg', 35.0, 'unit', 'switch 6a modular white board'),

        ('16A Heavy Duty Appliance Switch', 2, 'High current 16 Amp switch designed for geysers, ACs and heavy appliances.',
         '/static/images/products/product_1.svg', 95.0, 'unit', 'switch 16a heavy ac geyser'),

        # Sockets (cat_id: 3)
        ('6A/16A Universal Modular Socket', 3, 'Combined 3-pin universal socket with safety shutter.',
         '/static/images/products/product_1.svg', 110.0, 'unit', 'socket 6a 16a modular 3pin'),

        # Wires & Cables (cat_id: 4)
        ('2.5 sq mm Copper Wire Roll (90m)', 4, '90 Meter flame retardant PVC insulated 100% pure copper electrical wire.',
         '/static/images/products/product_1.svg', 1450.0, 'roll', 'wire cable copper 2.5mm red blue'),

        ('1.5 sq mm Copper Wire Roll (90m)', 4, 'Flexible multi-strand copper wire ideal for lighting circuits.',
         '/static/images/products/product_1.svg', 980.0, 'roll', 'wire 1.5mm copper cable roll'),

        # Chargers & Adapters (cat_id: 5, 6)
        ('65W GaN Dual Port Fast Wall Charger', 5, 'Compact Type-C and USB-A ultra-fast charger for laptops and smartphones.',
         '/static/images/products/product_1.svg', 1299.0, 'unit', 'charger fast type-c 65w phone laptop adapter'),

        ('Multi-Plug Universal Travel Adapter', 6, 'Worldwide plug converter with built-in surge protection.',
         '/static/images/products/product_1.svg', 250.0, 'unit', 'adapter plug universal multi travel'),

        # Extension Boards (cat_id: 7)
        ('4-Socket Spike Guard Extension Board', 7, 'Heavy-duty 2-meter extension cord with overload protector switch.',
         '/static/images/products/product_1.svg', 450.0, 'unit', 'extension board spike guard box socket cable'),

        # Batteries (cat_id: 8)
        ('9V HW Transistor Battery Pack (Set of 2)', 8, 'High performance 9 volt alkaline batteries for multimeters & electronic kits.',
         '/static/images/products/product_1.svg', 70.0, 'pack', 'battery 9v cell hw battery pack'),

        # Tools & Testers (cat_id: 10)
        ('60W Temperature Controlled Soldering Iron Kit', 10, 'Complete soldering iron kit with stand, solder wire, flux, and wire stripper.',
         '/static/images/products/product_1.svg', 499.0, 'kit', 'soldering iron tool kit solder flux wire'),

        ('Digital Multimeter DT830D with Probes', 10, 'Handheld AC/DC voltage, current, resistance and continuity circuit tester.',
         '/static/images/products/product_1.svg', 280.0, 'unit', 'multimeter tester voltage current digital meter'),

        # Sensors & Microcontrollers (cat_id: 11, 12)
        ('DHT11 Temperature & Humidity Sensor Module', 11, 'Digital sensor module compatible with Arduino and NodeMCU ESP8266.',
         '/static/images/products/product_1.svg', 120.0, 'unit', 'dht11 sensor temperature humidity module'),

        ('NodeMCU ESP8266 Wi-Fi Development Board', 12, 'Open-source IoT microcontroller board with integrated Wi-Fi chip.',
         '/static/images/products/product_1.svg', 260.0, 'unit', 'nodemcu esp8266 wifi dev board electronic component')
    ]
    cursor.executemany("""
        INSERT INTO products (name, category_id, description, image_url, base_price, unit, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, products_data)
    # Real-world product photos from Wikimedia Commons.
    # These URLs are intentionally product/category specific instead of one generic image.
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

    print("Seeding Shop Inventories (Direct Shop Stock)...")
    # Shop 1: Sri Sai Electricals (Shop ID: 1)
    # Shop 2: Lakshmi Electricals (Shop ID: 2)
    # Shop 3: Swathi Electronics (Shop ID: 3)

    shop_inventory_data = [
        # shop 1
        (1,1,120.0,12,1),(1,3,35.0,25,1),(1,5,110.0,15,1),(1,6,1450.0,6,1),(1,7,980.0,10,1),(1,8,1250.0,8,1),(1,10,450.0,14,1),(1,11,70.0,30,1),(1,12,480.0,7,1),
        # shop 2
        (2,1,115.0,5,1),(2,3,32.0,18,1),(2,5,105.0,8,1),(2,6,1420.0,4,1),(2,9,240.0,12,1),(2,10,430.0,9,1),(2,11,65.0,15,1),(2,13,270.0,11,1),
        # shop 3
        (3,1,122.0,8,1),(3,8,1299.0,15,1),(3,11,70.0,40,1),(3,12,499.0,12,1),(3,13,280.0,20,1),(3,14,120.0,35,1),(3,15,260.0,25,1)
    ]
    cursor.executemany("""
        INSERT INTO shop_products (shop_id, product_id, price, stock, is_available)
        VALUES (?, ?, ?, ?, ?)
    """, shop_inventory_data)

    print("Seeding Customer Address...")
    cursor.execute("""
        INSERT INTO addresses (user_id, title, address_line, locality, lat, lng, is_default)
        VALUES (?, 'Home', 'Flat #302, Sai Apartments, Benz Circle', 'Benz Circle, Vijayawada', 16.5062, 80.6480, 1)
    """, (user_map['customer@hardgo.com'],))

    print("Seeding Delivery Partners...")
    delivery_partners_data = [
        (user_map['raju@hardgo.com'], 'Raju Express', '9701144556', 'TVS XL Super (AP 16 AB 4589)', 16.5070, 80.6460, 1, 1, 4.9, 1250.0),
        (user_map['suresh@hardgo.com'], 'Suresh Speed Delivery', '9701166778', 'Hero Splendor (AP 16 CK 8821)', 16.5120, 80.6350, 1, 1, 4.7, 890.0)
    ]
    cursor.executemany("""
        INSERT INTO delivery_partners (user_id, name, phone, vehicle_type, lat, lng, is_online, is_available, rating, total_earnings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, delivery_partners_data)

    print("Seeding 30-Day Historical Sales for AI Demand Forecasting...")
    sales_records = []
    today = datetime.date.today()

    for day_offset in range(30):
        sale_date = today - datetime.timedelta(days=day_offset)
        # Shop 1 LED Bulbs high sales velocity
        sales_records.append((1, 1, random.randint(3, 8), str(sale_date)))
        sales_records.append((1, 3, random.randint(2, 6), str(sale_date)))
        sales_records.append((1, 8, random.randint(1, 4), str(sale_date)))

        # Shop 2 sales
        sales_records.append((2, 1, random.randint(2, 5), str(sale_date)))
        sales_records.append((2, 10, random.randint(1, 3), str(sale_date)))

        # Shop 3 sensors and tools sales
        sales_records.append((3, 12, random.randint(2, 6), str(sale_date)))
        sales_records.append((3, 14, random.randint(4, 10), str(sale_date)))

    cursor.executemany("""
        INSERT INTO sales_history (shop_id, product_id, quantity_sold, sale_date)
        VALUES (?, ?, ?, ?)
    """, sales_records)

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
