import os
import time
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection, init_db
from models import (
    get_user_by_email, get_user_by_id, create_user,
    search_nearby_products, get_product_details_across_shops,
    place_order, update_order_status, get_order_details,
    calculate_haversine_distance, calculate_estimated_delivery_time, calculate_delivery_fee
)
from ai_engine import analyze_image_and_find_product, get_ai_recommendations, predict_shop_demand

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hardgo_electrical_secret_key_2026')
app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY', '')

@app.context_processor
def inject_config():
    return {'google_maps_api_key': app.config['GOOGLE_MAPS_API_KEY']}

# Initialize database schema on start if needed
init_db()

# --- Session auth / role protection ---
def get_current_user():
    user_id = session.get('user_id')
    return get_user_by_id(user_id) if user_id else None

def role_required(*roles):
    def decorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Login required'}), 401
                return redirect(url_for('login_page'))
            if user['role'] not in roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Access denied'}), 403
                return redirect(url_for('dashboard'))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

def dashboard_for_role(role):
    return {'customer':'index','shop_owner':'owner_dashboard','delivery_partner':'delivery_dashboard','admin':'admin_dashboard'}.get(role,'index')

@app.route('/login')
def login_page():
    if get_current_user():
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@role_required('customer','shop_owner','delivery_partner','admin')
def dashboard():
    return redirect(url_for(dashboard_for_role(get_current_user()['role'])))

@app.route('/')
@role_required('customer')
def index():
    return render_template('index.html', current_user=get_current_user())

@app.route('/owner')
@role_required('shop_owner')
def owner_dashboard():
    return render_template('index.html', current_user=get_current_user(), forced_role='shop_owner')

@app.route('/delivery')
@role_required('delivery_partner')
def delivery_dashboard():
    return render_template('index.html', current_user=get_current_user(), forced_role='delivery_partner')

@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    return render_template('index.html', current_user=get_current_user(), forced_role='admin')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    user = get_user_by_email(email)
    if not user or user['password'] != password:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    session.clear()
    session['user_id'] = user['id']
    session['role'] = user['role']
    return jsonify({'success': True, 'user': user, 'redirect': url_for(dashboard_for_role(user['role']))})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    name, email, phone, password = data.get('name'), data.get('email'), data.get('phone'), data.get('password')
    if not name or not email or not password or not phone:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    if get_user_by_email(email.strip().lower()):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    try:
        user_id = create_user(name, email.strip().lower(), phone, 'customer', password)
        session.clear(); session['user_id']=user_id; session['role']='customer'
        return jsonify({'success': True, 'user': get_user_by_id(user_id), 'redirect': '/'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'redirect': '/login'})

@app.route('/api/auth/session')
def get_session():
    user = get_current_user()
    return jsonify({'user': user})

# --- Customer & Search APIs ---
@app.route('/api/categories')
@role_required('customer')
def get_categories():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify({'categories': [dict(c) for c in categories]})

@app.route('/api/search')
@role_required('customer')
def search():
    query = request.args.get('q', '')
    cat_id = request.args.get('category_id', type=int)
    lat = request.args.get('lat', type=float, default=16.5062) # Benz Circle Vijayawada
    lng = request.args.get('lng', type=float, default=80.6480)

    # Log search query
    if query:
        conn = get_db_connection()
        conn.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (session.get('user_id'), query))
        conn.commit()
        conn.close()

    results = search_nearby_products(query=query, category_id=cat_id, customer_lat=lat, customer_lng=lng)
    public_results = []
    for item in results:
        item = dict(item)
        item.pop('shop_name', None); item.pop('shop_locality', None)
        item['shop_label'] = 'Nearby verified store'
        public_results.append(item)
    return jsonify({'query': query, 'customer_lat': lat, 'customer_lng': lng, 'total_results': len(public_results), 'products': public_results})

@app.route('/api/products/<int:product_id>/shops')
@role_required('customer')
def product_shops_comparison(product_id):
    lat = request.args.get('lat', type=float, default=16.5062)
    lng = request.args.get('lng', type=float, default=80.6480)

    shops = get_product_details_across_shops(product_id, customer_lat=lat, customer_lng=lng)
    return jsonify({
        'product_id': product_id,
        'available_shops': shops
    })

# --- Orders & Cart APIs ---
@app.route('/api/orders/place', methods=['POST'])
@role_required('customer')
def place_new_order():
    data = request.json or {}
    user = get_current_user()

    if not user:
        return jsonify({'success': False, 'message': 'Customer authentication required'}), 401

    shop_id = data.get('shop_id')
    items = data.get('items', [])
    delivery_address = data.get('delivery_address', 'Benz Circle, Vijayawada')
    lat = data.get('lat', 16.5062)
    lng = data.get('lng', 80.6480)
    payment_method = data.get('payment_method', 'COD')

    if not shop_id or not items:
        return jsonify({'success': False, 'message': 'Cart items and shop selection required'}), 400

    try:
        order_id, order_number = place_order(
            customer_id=user['id'],
            shop_id=shop_id,
            items=items,
            delivery_address=delivery_address,
            customer_lat=lat,
            customer_lng=lng,
            payment_method=payment_method
        )
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order_number,
            'message': 'Order placed successfully!'
        })
    except ValueError as ve:
        return jsonify({'success': False, 'message': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f"Order placement failed: {str(e)}"}), 500

@app.route('/api/orders/my-orders')
@role_required('customer')
def my_orders():
    user = get_current_user()
    if not user:
        return jsonify({'orders': []})

    conn = get_db_connection()
    orders = conn.execute("""
        SELECT o.*, s.name AS shop_name, s.locality AS shop_locality
        FROM orders o
        JOIN shops s ON o.shop_id = s.id
        WHERE o.customer_id = ?
        ORDER BY o.created_at DESC
    """, (user['id'],)).fetchall()
    conn.close()

    result = []
    for o in orders:
        od = dict(o)
        details = get_order_details(od['id'])
        if details:
            od['items'] = details['items']
        od.pop('shop_name', None); od.pop('shop_locality', None)
        od['shop_label'] = 'Nearby verified store'
        result.append(od)

    return jsonify({'orders': result})

@app.route('/api/orders/<int:order_id>/track')
@role_required('customer')
def track_order(order_id):
    details = get_order_details(order_id)
    if not details or details.get('customer_id') != get_current_user()['id']:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    details.pop('shop_name', None); details.pop('shop_phone', None); details.pop('shop_address', None); details.pop('partner_name', None); details.pop('partner_phone', None)
    details['shop_label'] = 'Nearby verified store'
    return jsonify({'success': True, 'order': details})

# --- Shop Owner APIs ---
@app.route('/api/shop/details')
@role_required('shop_owner')
def shop_details():
    user = get_current_user()
    conn = get_db_connection()

    shop = conn.execute("SELECT * FROM shops WHERE owner_id = ?", (user['id'],)).fetchone()
    if not shop:
        conn.close(); return jsonify({'success': False, 'message': 'No shop assigned to this owner'}), 404

    conn.close()
    return jsonify({'shop': dict(shop)})

@app.route('/api/shop/inventory')
@role_required('shop_owner')
def shop_inventory():
    user = get_current_user()
    conn = get_db_connection()

    shop = conn.execute("SELECT id FROM shops WHERE owner_id = ?", (user['id'],)).fetchone()
    if not shop:
        conn.close(); return jsonify({'success': False, 'message': 'No shop assigned to this owner'}), 404
    shop_id = shop['id']

    inventory = conn.execute("""
        SELECT sp.*, p.name AS product_name, p.description, p.image_url, p.unit, c.name AS category_name
        FROM shop_products sp
        JOIN products p ON sp.product_id = p.id
        JOIN categories c ON p.category_id = c.id
        WHERE sp.shop_id = ?
        ORDER BY sp.stock ASC
    """, (shop_id,)).fetchall()

    all_master_products = conn.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
    """).fetchall()

    conn.close()
    return jsonify({
        'shop_id': shop_id,
        'inventory': [dict(i) for i in inventory],
        'master_catalog': [dict(m) for m in all_master_products]
    })

@app.route('/api/shop/stock/update', methods=['POST'])
@role_required('shop_owner')
def update_stock():
    data = request.json or {}
    shop_product_id = data.get('shop_product_id')
    new_stock = data.get('stock')
    new_price = data.get('price')

    if shop_product_id is None or new_stock is None:
        return jsonify({'success': False, 'message': 'Stock parameter required'}), 400

    conn = get_db_connection()
    owner_shop = conn.execute("SELECT id FROM shops WHERE owner_id = ?", (get_current_user()['id'],)).fetchone()
    if not owner_shop:
        conn.close(); return jsonify({'success': False, 'message': 'No shop assigned'}), 403
    allowed = conn.execute("SELECT id FROM shop_products WHERE id = ? AND shop_id = ?", (shop_product_id, owner_shop['id'])).fetchone()
    if not allowed:
        conn.close(); return jsonify({'success': False, 'message': 'This inventory item is not yours'}), 403
    is_available = 1 if int(new_stock) > 0 else 0

    if new_price is not None:
        conn.execute("""
            UPDATE shop_products SET stock = ?, price = ?, is_available = ? WHERE id = ?
        """, (int(new_stock), float(new_price), is_available, shop_product_id))
    else:
        conn.execute("""
            UPDATE shop_products SET stock = ?, is_available = ? WHERE id = ?
        """, (int(new_stock), is_available, shop_product_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Stock updated successfully!'})

@app.route('/api/shop/products/add', methods=['POST'])
@role_required('shop_owner')
def add_product_to_shop():
    data = request.json or {}
    user = get_current_user()

    conn = get_db_connection()
    shop = conn.execute("SELECT id FROM shops WHERE owner_id = ?", (user['id'],)).fetchone()
    if not shop:
        conn.close(); return jsonify({'success': False, 'message': 'No shop assigned to this owner'}), 404
    shop_id = shop['id']

    product_id = data.get('product_id')
    price = data.get('price')
    stock = data.get('stock', 10)

    try:
        conn.execute("""
            INSERT INTO shop_products (shop_id, product_id, price, stock, is_available)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(shop_id, product_id) DO UPDATE SET price=excluded.price, stock=excluded.stock, is_available=1
        """, (shop_id, product_id, float(price), int(stock), 1 if int(stock) > 0 else 0))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Product added to shop inventory!'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/shop/orders')
@role_required('shop_owner')
def shop_orders():
    user = get_current_user()
    conn = get_db_connection()

    shop = conn.execute("SELECT id FROM shops WHERE owner_id = ?", (user['id'],)).fetchone()
    if not shop:
        conn.close(); return jsonify({'success': False, 'message': 'No shop assigned to this owner'}), 404
    shop_id = shop['id']

    orders = conn.execute("""
        SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        WHERE o.shop_id = ?
        ORDER BY o.created_at DESC
    """, (shop_id,)).fetchall()
    conn.close()

    result = []
    for o in orders:
        od = dict(o)
        details = get_order_details(od['id'])
        if details:
            od['items'] = details['items']
        result.append(od)

    return jsonify({'shop_id': shop_id, 'orders': result})

@app.route('/api/shop/orders/<int:order_id>/status', methods=['POST'])
@role_required('shop_owner')
def update_shop_order_status(order_id):
    data = request.json or {}
    new_status = data.get('status')
    reason = data.get('reason')

    try:
        conn = get_db_connection()
        allowed = conn.execute("SELECT o.id FROM orders o JOIN shops s ON o.shop_id=s.id WHERE o.id=? AND s.owner_id=?", (order_id, get_current_user()['id'])).fetchone()
        conn.close()
        if not allowed: return jsonify({'success': False, 'message': 'Order does not belong to your shop'}), 403
        update_order_status(order_id, new_status, rejection_reason=reason)
        return jsonify({'success': True, 'message': f"Order updated to '{new_status}'"})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# --- Delivery Partner APIs ---
@app.route('/api/delivery/requests')
@role_required('delivery_partner')
def get_delivery_requests():
    conn = get_db_connection()
    # Available orders needing pickup
    orders = conn.execute("""
        SELECT o.*, s.name AS shop_name, s.address AS shop_address, s.lat AS shop_lat, s.lng AS shop_lng,
               u.name AS customer_name, u.phone AS customer_phone
        FROM orders o
        JOIN shops s ON o.shop_id = s.id
        JOIN users u ON o.customer_id = u.id
        WHERE o.delivery_partner_id IS NULL
          AND o.status IN ('Shop Accepted', 'Preparing', 'Ready for Pickup')
        ORDER BY o.created_at DESC
    """).fetchall()

    dp = conn.execute("SELECT id FROM delivery_partners WHERE user_id = ?", (get_current_user()['id'],)).fetchone()
    dp_id = dp['id'] if dp else -1
    my_deliveries = conn.execute("""
        SELECT o.*, s.name AS shop_name, s.address AS shop_address, s.lat AS shop_lat, s.lng AS shop_lng,
               u.name AS customer_name, u.phone AS customer_phone
        FROM orders o
        JOIN shops s ON o.shop_id = s.id
        JOIN users u ON o.customer_id = u.id
        WHERE o.delivery_partner_id = ?
          AND o.status IN ('Ready for Pickup', 'Picked Up', 'On the Way')
        ORDER BY o.created_at DESC
    """, (dp_id,)).fetchall()

    conn.close()

    return jsonify({
        'available_orders': [dict(o) for o in orders],
        'active_deliveries': [dict(m) for m in my_deliveries]
    })

@app.route('/api/delivery/accept', methods=['POST'])
@role_required('delivery_partner')
def accept_delivery():
    data = request.json or {}
    order_id = data.get('order_id')
    user = get_current_user()

    conn = get_db_connection()
    dp = conn.execute("SELECT id FROM delivery_partners WHERE user_id = ?", (user['id'],)).fetchone()
    if not dp: conn.close(); return jsonify({'success': False, 'message': 'Delivery partner profile not found'}), 403
    dp_id = dp['id']
    target = conn.execute("SELECT * FROM orders WHERE id=? AND delivery_partner_id IS NULL AND status IN ('Shop Accepted','Preparing','Ready for Pickup')", (order_id,)).fetchone()
    if not target: conn.close(); return jsonify({'success': False, 'message': 'Delivery request is no longer available. Refresh the dashboard.'}), 409

    # Atomically claim the order so two delivery partners cannot accept it together.
    claimed = conn.execute("UPDATE orders SET delivery_partner_id = ?, status = 'Ready for Pickup', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND delivery_partner_id IS NULL", (dp_id, order_id))
    if claimed.rowcount != 1:
        conn.rollback(); conn.close(); return jsonify({'success': False, 'message': 'Someone else accepted this delivery first. Refresh the dashboard.'}), 409
    conn.execute("UPDATE delivery_partners SET is_available = 0 WHERE id = ?", (dp_id,))

    # Insert delivery record if not exists
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    shop = conn.execute("SELECT * FROM shops WHERE id = ?", (order['shop_id'],)).fetchone()

    conn.execute("""
        INSERT OR REPLACE INTO deliveries (order_id, partner_id, pickup_lat, pickup_lng, drop_lat, drop_lng, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Accepted')
    """, (order_id, dp_id, shop['lat'], shop['lng'], order['customer_lat'], order['customer_lng']))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Delivery request accepted!'})

@app.route('/api/delivery/status', methods=['POST'])
@role_required('delivery_partner')
def update_delivery_status():
    data = request.json or {}
    order_id = data.get('order_id')
    status = data.get('status') # 'Picked Up', 'On the Way', 'Delivered'

    try:
        conn=get_db_connection(); dp=conn.execute("SELECT id FROM delivery_partners WHERE user_id=?",(get_current_user()['id'],)).fetchone(); allowed=conn.execute("SELECT id FROM orders WHERE id=? AND delivery_partner_id=?",(order_id, dp['id'] if dp else -1)).fetchone(); conn.close()
        if not allowed: return jsonify({'success': False, 'message': 'This delivery is not assigned to you'}), 403
        update_order_status(order_id, status)
        return jsonify({'success': True, 'message': f"Delivery status set to {status}"})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# --- Admin APIs ---
@app.route('/api/admin/stats')
@role_required('admin')
def admin_stats():
    conn = get_db_connection()

    total_customers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'").fetchone()[0]
    total_shops = conn.execute("SELECT COUNT(*) FROM shops WHERE is_active = 1").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    delivered_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'Delivered'").fetchone()[0]
    total_revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'Delivered'").fetchone()[0]

    recent_orders = conn.execute("""
        SELECT o.*, u.name as customer_name, s.name as shop_name
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        JOIN shops s ON o.shop_id = s.id
        ORDER BY o.created_at DESC LIMIT 10
    """).fetchall()

    conn.close()

    return jsonify({
        'total_customers': total_customers,
        'active_shops': total_shops,
        'total_orders': total_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': round(total_revenue, 2),
        'recent_orders': [dict(r) for r in recent_orders]
    })

# --- AI APIs ---
@app.route('/api/ai/visual-search', methods=['POST'])
@role_required('customer')
def ai_visual_search():
    file = request.files.get('image')
    sample_name = request.form.get('sample_name', '')

    if file:
        img_bytes = file.read()
        res = analyze_image_and_find_product(image_bytes=img_bytes, filename=file.filename)
    elif sample_name:
        res = analyze_image_and_find_product(filename=sample_name)
    else:
        res = analyze_image_and_find_product(filename='led_bulb')

    for item in res.get('nearby_in_stock_products', []):
        item.pop('shop_name', None); item.pop('shop_locality', None)
        item['shop_label'] = 'Nearby verified store'
    return jsonify(res)

@app.route('/api/ai/recommendations')
@role_required('customer')
def ai_recommendations():
    prod_id = request.args.get('product_id', type=int)
    recs = get_ai_recommendations(current_product_id=prod_id)
    return jsonify({'recommendations': recs})

@app.route('/api/ai/demand-prediction')
@role_required('shop_owner')
def ai_demand_prediction():
    user = get_current_user()
    conn = get_db_connection()
    shop = conn.execute("SELECT id FROM shops WHERE owner_id = ?", (user['id'],)).fetchone()
    if not shop:
        conn.close(); return jsonify({'success': False, 'message': 'No shop assigned to this owner'}), 404
    shop_id = shop['id']
    conn.close()

    predictions = predict_shop_demand(shop_id)
    return jsonify({'shop_id': shop_id, 'predictions': predictions})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
