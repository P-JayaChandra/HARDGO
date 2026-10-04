import math
from database import get_db_connection

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate Haversine distance in kilometers between two geo points.
    """
    R = 6371.0  # Earth's radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return round(distance, 2)

def calculate_estimated_delivery_time(distance_km, shop_prep_time_mins=10):
    """
    Delivery time estimation logic:
    Prep time (mins) + (Distance * 3 mins/km)
    """
    travel_time = math.ceil(distance_km * 3)
    total_time = shop_prep_time_mins + travel_time
    min_time = max(5, total_time - 2)
    max_time = total_time + 4
    return min_time, max_time, total_time

def calculate_delivery_fee(distance_km):
    """
    Flat ₹20 for first 2 km, ₹10/km for distance beyond 2 km.
    """
    if distance_km <= 2.0:
        return 20.0
    return round(20.0 + (distance_km - 2.0) * 10.0, 1)

# --- User & Auth Operations ---
def create_user(name, email, phone, role, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, phone, role, password) VALUES (?, ?, ?, ?, ?)",
            (name, email, phone, role, password)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

# --- Product & Search Operations ---
def search_nearby_products(query="", category_id=None, customer_lat=16.5062, customer_lng=80.6480, max_distance=15.0):
    """
    Core Search logic:
    Finds products available at nearby shops based on customer lat/lng.
    Groups results by shop + product, prioritizes availability, distance, delivery time, and shop rating.
    """
    conn = get_db_connection()

    sql = """
        SELECT
            sp.id AS shop_product_id,
            sp.price,
            sp.stock,
            sp.is_available,
            p.id AS product_id,
            p.name AS product_name,
            p.description,
            p.image_url,
            p.unit,
            c.id AS category_id,
            c.name AS category_name,
            c.icon AS category_icon,
            s.id AS shop_id,
            s.name AS shop_name,
            s.phone AS shop_phone,
            s.address AS shop_address,
            s.locality AS shop_locality,
            s.lat AS shop_lat,
            s.lng AS shop_lng,
            s.rating AS shop_rating,
            s.prep_time_mins AS shop_prep_time
        FROM shop_products sp
        JOIN products p ON sp.product_id = p.id
        JOIN categories c ON p.category_id = c.id
        JOIN shops s ON sp.shop_id = s.id
        WHERE s.is_active = 1 AND sp.is_available = 1 AND sp.stock > 0
    """

    params = []
    if query:
        sql += " AND (p.name LIKE ? OR p.description LIKE ? OR p.tags LIKE ? OR c.name LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern, pattern])

    if category_id:
        sql += " AND p.category_id = ?"
        params.append(category_id)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        distance = calculate_haversine_distance(customer_lat, customer_lng, item['shop_lat'], item['shop_lng'])

        if distance <= max_distance:
            min_t, max_t, est_t = calculate_estimated_delivery_time(distance, item['shop_prep_time'])
            delivery_fee = calculate_delivery_fee(distance)

            item['distance_km'] = distance
            item['est_delivery_mins'] = est_t
            item['est_delivery_text'] = f"⚡ {min_t}–{max_t} min"
            item['delivery_fee'] = delivery_fee
            results.append(item)

    # Sort priority: 1) Availability (stock > 0), 2) Distance (km), 3) Delivery Time, 4) Shop Rating desc
    results.sort(key=lambda x: (x['distance_km'], x['est_delivery_mins'], -x['shop_rating']))
    return results

def get_product_details_across_shops(product_id, customer_lat=16.5062, customer_lng=80.6480):
    """
    Compares availability of a specific product across all nearby shops.
    Example: 12W LED Bulb across Shop A, Shop B, Shop C
    """
    conn = get_db_connection()

    sql = """
        SELECT
            sp.id AS shop_product_id,
            sp.price,
            sp.stock,
            sp.is_available,
            p.id AS product_id,
            p.name AS product_name,
            p.description,
            p.image_url,
            p.unit,
            s.id AS shop_id,
            s.name AS shop_name,
            s.locality AS shop_locality,
            s.lat AS shop_lat,
            s.lng AS shop_lng,
            s.rating AS shop_rating,
            s.prep_time_mins AS shop_prep_time
        FROM shop_products sp
        JOIN products p ON sp.product_id = p.id
        JOIN shops s ON sp.shop_id = s.id
        WHERE p.id = ? AND s.is_active = 1
    """

    rows = conn.execute(sql, (product_id,)).fetchall()
    conn.close()

    shops_list = []
    for r in rows:
        item = dict(r)
        distance = calculate_haversine_distance(customer_lat, customer_lng, item['shop_lat'], item['shop_lng'])
        min_t, max_t, est_t = calculate_estimated_delivery_time(distance, item['shop_prep_time'])

        item['distance_km'] = distance
        item['est_delivery_text'] = f"⚡ {min_t}–{max_t} min"
        item['est_delivery_mins'] = est_t
        item['is_in_stock'] = item['stock'] > 0 and item['is_available'] == 1
        shops_list.append(item)

    # Sort: in stock first, then by distance
    shops_list.sort(key=lambda x: (not x['is_in_stock'], x['distance_km']))
    return shops_list

# --- Order & Inventory Operations ---
def place_order(customer_id, shop_id, items, delivery_address, customer_lat, customer_lng, payment_method="COD"):
    """
    Places order:
    1. Validates stock for each product at shop.
    2. Decrements shop product stock.
    3. If stock drops to 0, updates stock status.
    4. Calculates total amount, delivery fee, distance.
    5. Assigns an initial status of 'Order Placed'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get shop details
        shop = cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()
        if not shop:
            raise ValueError("Invalid shop selected.")

        distance_km = calculate_haversine_distance(customer_lat, customer_lng, shop['lat'], shop['lng'])
        min_t, max_t, est_mins = calculate_estimated_delivery_time(distance_km, shop['prep_time_mins'])
        delivery_fee = calculate_delivery_fee(distance_km)

        subtotal_sum = 0.0
        validated_items = []

        # Validate stock & calculate totals
        for item in items:
            product_id = item['product_id']
            qty = int(item['quantity'])

            sp = cursor.execute(
                "SELECT sp.*, p.name FROM shop_products sp JOIN products p ON sp.product_id = p.id WHERE sp.shop_id = ? AND sp.product_id = ?",
                (shop_id, product_id)
            ).fetchone()

            if not sp:
                raise ValueError(f"Product ID {product_id} not offered by this shop.")
            if sp['stock'] < qty:
                raise ValueError(f"Insufficient stock for '{sp['name']}'. Only {sp['stock']} available.")

            item_subtotal = sp['price'] * qty
            subtotal_sum += item_subtotal

            validated_items.append({
                'shop_product_id': sp['id'],
                'product_id': product_id,
                'name': sp['name'],
                'price': sp['price'],
                'quantity': qty,
                'subtotal': item_subtotal,
                'current_stock': sp['stock']
            })

        total_amount = round(subtotal_sum + delivery_fee, 2)

        # Generate order number
        import random, time
        order_number = f"HG-{int(time.time())}-{random.randint(100, 999)}"

        # Delivery is intentionally NOT auto-assigned here.
        # The shop accepts/prepares the order first, then an available delivery
        # partner explicitly accepts it from the Delivery dashboard.
        delivery_partner_id = None

        cursor.execute("""
            INSERT INTO orders (
                order_number, customer_id, shop_id, delivery_partner_id, status,
                total_amount, delivery_fee, distance_km, estimated_delivery_mins,
                payment_method, payment_status, delivery_address, customer_lat, customer_lng
            ) VALUES (?, ?, ?, ?, 'Order Placed', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number, customer_id, shop_id, delivery_partner_id,
            total_amount, delivery_fee, distance_km, est_mins,
            payment_method, 'Pending' if payment_method == 'COD' else 'Paid',
            delivery_address, customer_lat, customer_lng
        ))

        order_id = cursor.lastrowid

        # Insert order items & decrement shop stock
        for v in validated_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, v['product_id'], v['name'], v['price'], v['quantity'], v['subtotal']))

            new_stock = v['current_stock'] - v['quantity']
            is_avail = 1 if new_stock > 0 else 0

            cursor.execute("""
                UPDATE shop_products SET stock = ?, is_available = ? WHERE id = ?
            """, (new_stock, is_avail, v['shop_product_id']))

            # Log to sales history for AI demand prediction
            cursor.execute("""
                INSERT INTO sales_history (shop_id, product_id, quantity_sold, sale_date)
                VALUES (?, ?, ?, DATE('now'))
            """, (shop_id, v['product_id'], v['quantity']))

        conn.commit()
        return order_id, order_number
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_order_status(order_id, new_status, rejection_reason=None):
    """
    Handles state transition:
    Order Placed -> Shop Accepted -> Preparing -> Ready for Pickup -> Picked Up -> On the Way -> Delivered / Rejected.
    If rejected by shop, refunds stock back to inventory.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        order = cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            raise ValueError("Order not found.")

        current_status = order['status']

        if new_status == 'Rejected' and current_status != 'Rejected':
            # Refund stock back to shop_products
            items = cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
            for item in items:
                cursor.execute("""
                    UPDATE shop_products
                    SET stock = stock + ?, is_available = 1
                    WHERE shop_id = ? AND product_id = ?
                """, (item['quantity'], order['shop_id'], item['product_id']))

            cursor.execute("""
                UPDATE orders SET status = 'Rejected', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (rejection_reason or 'Shop unavailable', order_id))

        else:
            cursor.execute("""
                UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (new_status, order_id))

            # Update delivery table if applicable
            if new_status == 'Picked Up':
                cursor.execute("UPDATE deliveries SET status = 'Picked Up', picked_at = CURRENT_TIMESTAMP WHERE order_id = ?", (order_id,))
            elif new_status == 'Delivered':
                cursor.execute("UPDATE deliveries SET status = 'Delivered', delivered_at = CURRENT_TIMESTAMP WHERE order_id = ?", (order_id,))
                cursor.execute("UPDATE orders SET payment_status = 'Paid' WHERE id = ?", (order_id,))
                # Add earnings and make the partner available for another delivery.
                if order['delivery_partner_id']:
                    cursor.execute("UPDATE delivery_partners SET total_earnings = total_earnings + ?, is_available = 1 WHERE id = ?", (order['delivery_fee'], order['delivery_partner_id']))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_order_details(order_id):
    conn = get_db_connection()

    order = conn.execute("""
        SELECT o.*, s.name AS shop_name, s.phone AS shop_phone, s.address AS shop_address,
               s.lat AS shop_lat, s.lng AS shop_lng,
               u.name AS customer_name, u.phone AS customer_phone,
               dp.name AS partner_name, dp.phone AS partner_phone
        FROM orders o
        JOIN shops s ON o.shop_id = s.id
        JOIN users u ON o.customer_id = u.id
        LEFT JOIN delivery_partners dp ON o.delivery_partner_id = dp.id
        WHERE o.id = ?
    """, (order_id,)).fetchone()

    if not order:
        conn.close()
        return None

    items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    delivery = conn.execute("SELECT * FROM deliveries WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()

    res = dict(order)
    res['items'] = [dict(i) for i in items]
    res['delivery'] = dict(delivery) if delivery else None
    return res
