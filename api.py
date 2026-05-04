from flask import Flask, request, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import traceback

app = Flask(__name__)

# ==========================================
# DOMAIN: CORE CONFIG & UTILS
# ==========================================

# -------------------------------
# CONFIG: Database Connection
# -------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="api",
        password="strongpassword",
        database="scholarbridge_db"
    )

# -------------------------------
# CONFIG: Helper Functions
# -------------------------------
def format_user(row):
    return {"id": row["id"], "full_name": row["full_name"], "email": row["email"]}

def time_ago(dt):
    if not dt: return "Just now"
    diff = datetime.now() - dt
    if diff.days > 0: return f"{diff.days}d ago"
    if diff.seconds >= 3600: return f"{diff.seconds // 3600}h ago"
    if diff.seconds >= 60: return f"{diff.seconds // 60}m ago"
    return "Just now"

# -------------------------------
# GET: Root Status
# -------------------------------
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "API is running"})


# ==========================================
# DOMAIN: USERS & AUTHENTICATION
# ==========================================

# -------------------------------
# POST: Create User (Sign Up)
# -------------------------------
@app.route('/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body must be JSON"}), 400

        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')

        if not full_name or not email or not password:
            return jsonify({"error": "full_name, email, and password are required"}), 400

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, full_name, password) VALUES (%s, %s, %s)",
            (email, full_name, hashed_password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "User created"}), 201

    except Exception as e:
        print("🔥 SIGNUP FAILED")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "type": str(type(e))}), 500

# -------------------------------
# POST: Login User
# -------------------------------
@app.route('/login', methods=['POST'])
def log_user():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body must be JSON"}), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid email or password"}), 401

        return jsonify({"message": "Login successful", "user": format_user(user)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# POST: Request Password Reset
# -------------------------------
@app.route('/request_reset', methods=['POST'])
def request_reset():
    try:
        data = request.json
        email = data.get('email')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "No account found with this email"}), 404

        otp = f"{random.randint(100000, 999999)}"
        expiry = datetime.now() + timedelta(minutes=10)

        cursor.execute("UPDATE users SET reset_otp = %s, otp_expiry = %s WHERE email = %s", (otp, expiry, email))
        conn.commit()

        print(f"\nDEBUG: 2FA CODE FOR {email} IS: {otp}\n")

        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "OTP Generated", "debug_otp": otp}), 200

    except Exception as e:
        print(f"🚨 SERVER ERROR: {e}")
        return jsonify({"error": "Database error or missing columns"}), 500

# -------------------------------
# POST: Verify Reset OTP
# -------------------------------
@app.route('/verify_reset', methods=['POST'])
def verify_reset():
    try:
        data = request.json
        email = data.get('email')
        user_otp = data.get('otp')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT reset_otp, otp_expiry FROM users WHERE email = %s", (email,))
        record = cursor.fetchone()

        if record and str(record['reset_otp']) == str(user_otp):
            if datetime.now() < record['otp_expiry']:
                return jsonify({"success": True, "message": "OTP Verified"}), 200
            else:
                return jsonify({"error": "This code has expired"}), 400
        
        return jsonify({"error": "The code you entered is incorrect"}), 400

    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# -------------------------------
# POST: Reset Password
# -------------------------------
@app.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.json
        email = data.get('email')
        new_password = data.get('password')
        hashed_password = generate_password_hash(new_password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET password = %s, reset_otp = NULL, otp_expiry = NULL 
            WHERE email = %s
        """, (hashed_password, email))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to update password"}), 500

# -------------------------------
# GET: All Users
# -------------------------------
@app.route('/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        users = [format_user(row) for row in rows]
        cursor.close()
        conn.close()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# PUT: Update Profile (Cascading)
# -------------------------------
@app.route('/update_profile', methods=['PUT'])
def update_profile():
    data = request.json
    email = data.get('email')
    old_name = data.get('old_name')
    new_name = data.get('full_name')
    new_password = data.get('password') 
    
    new_role = data.get('role', 'Not set')
    new_age = data.get('age', 'Not set')
    new_birthday = data.get('birthday', 'Not set')
    new_location = data.get('location', 'Not set')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if new_password:
            hashed = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))

        if new_name and new_name != old_name:
            cursor.execute("UPDATE users SET full_name=%s WHERE email=%s", (new_name, email))
            cursor.execute("UPDATE products SET full_name=%s WHERE full_name=%s", (new_name, old_name))
            cursor.execute("UPDATE messages SET sender_name=%s WHERE sender_name=%s", (new_name, old_name))
            cursor.execute("UPDATE messages SET receiver_name=%s WHERE receiver_name=%s", (new_name, old_name))
            cursor.execute("UPDATE reviews SET seller_name=%s WHERE seller_name=%s", (new_name, old_name))

        cursor.execute("""
            UPDATE users 
            SET role=%s, age=%s, birthday=%s, location=%s 
            WHERE email=%s
        """, (new_role, new_age, new_birthday, new_location, email))

        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Profile safely updated everywhere!"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to update database."}), 500

# -------------------------------
# DELETE: Delete User
# -------------------------------
@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE Id=%s", (user_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "User not found"}), 404

        cursor.close()
        conn.close()
        return jsonify({"message": "User deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# DOMAIN: PROFILES & DASHBOARD
# ==========================================

# -------------------------------
# GET: Public Profile
# -------------------------------
@app.route('/profile/<string:fullname>', methods=['GET'])
def get_user_profile(fullname):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query_products = """
            SELECT p.*, COALESCE((SELECT AVG(rating) FROM reviews r WHERE r.seller_name = p.full_name), 0) AS seller_rating 
            FROM products p WHERE p.full_name=%s AND p.satisfied=0
        """
        cursor.execute(query_products, (fullname,))
        products = cursor.fetchall()
        
        query_rating = "SELECT AVG(rating) as avg_rating FROM reviews WHERE seller_name=%s"
        cursor.execute(query_rating, (fullname,))
        rating_row = cursor.fetchone()
        
        cursor.close()
        conn.close()

        avg_rating = 0.0
        if rating_row and rating_row['avg_rating'] is not None:
            avg_rating = round(float(rating_row['avg_rating']), 1)

        return jsonify({"rating": avg_rating, "products": products}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET: User Stats (Dashboard)
# -------------------------------
@app.route('/stats/<string:full_name>', methods=['GET'])
def get_user_stats(full_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT SUM(price) as total FROM products WHERE full_name=%s AND satisfied=1", (full_name,))
        total_earnings = cursor.fetchone()['total'] or 0
        
        cursor.execute("""
            SELECT SUM(amount) as val FROM activity_logs 
            WHERE email = (SELECT email FROM users WHERE full_name=%s LIMIT 1) 
            AND type='Sold' AND date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (full_name,))
        earnings_this_week = cursor.fetchone()['val'] or 0
        
        cursor.execute("""
            SELECT SUM(amount) as val FROM activity_logs 
            WHERE email = (SELECT email FROM users WHERE full_name=%s LIMIT 1) 
            AND type='Sold' AND date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND date < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (full_name,))
        earnings_last_week = cursor.fetchone()['val'] or 0

        cursor.execute("SELECT COUNT(id) as total FROM products WHERE full_name=%s AND satisfied=1", (full_name,))
        items_sold = cursor.fetchone()['total'] or 0
        
        cursor.execute("""
            SELECT COUNT(id) as val FROM activity_logs 
            WHERE email = (SELECT email FROM users WHERE full_name=%s LIMIT 1) 
            AND type='Sold' AND date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (full_name,))
        sold_this_week = cursor.fetchone()['val'] or 0
        
        cursor.execute("""
            SELECT COUNT(id) as val FROM activity_logs 
            WHERE email = (SELECT email FROM users WHERE full_name=%s LIMIT 1) 
            AND type='Sold' AND date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND date < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (full_name,))
        sold_last_week = cursor.fetchone()['val'] or 0

        cursor.execute("SELECT COUNT(id) as total FROM products WHERE full_name=%s AND satisfied=0", (full_name,))
        active_products = cursor.fetchone()['total'] or 0
        
        cursor.execute("SELECT COUNT(id) as total FROM services WHERE full_name=%s AND active=1", (full_name,))
        active_services = cursor.fetchone()['total'] or 0
        
        active_listings = active_products + active_services

        cursor.execute("""
            SELECT COUNT(id) as val FROM activity_logs 
            WHERE email = (SELECT email FROM users WHERE full_name=%s LIMIT 1) 
            AND type='Listed' AND date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (full_name,))
        listed_this_week = cursor.fetchone()['val'] or 0

        cursor.execute("""
            SELECT COUNT(id) as val FROM activity_logs 
            WHERE email = (SELECT email FROM users WHERE full_name=%s LIMIT 1) 
            AND type='Listed' AND date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND date < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (full_name,))
        listed_last_week = cursor.fetchone()['val'] or 0

        def calc_pct(curr, prev):
            if prev == 0: return 100 if curr > 0 else 0
            return round(((curr - prev) / prev) * 100)

        cursor.execute("SELECT seller_name, AVG(rating) as avg_r FROM reviews GROUP BY seller_name")
        all_sellers = cursor.fetchall()
        
        my_rating = 0.0
        for s in all_sellers:
            if s['seller_name'] == full_name:
                my_rating = float(s['avg_r'])
                break
        
        better_sellers = sum(1 for s in all_sellers if float(s['avg_r']) > my_rating)
        total_sellers = len(all_sellers) if len(all_sellers) > 0 else 1
        
        percentile = (better_sellers / total_sellers) * 100
        if percentile < 1: top_pct = "Top 1%"
        elif percentile <= 5: top_pct = "Top 5%"
        elif percentile <= 10: top_pct = "Top 10%"
        elif percentile <= 25: top_pct = "Top 25%"
        else: top_pct = "Top 50%"
        
        if total_sellers < 3: top_pct = "Top 1%" 

        cursor.execute("SELECT price FROM products WHERE full_name=%s AND satisfied=1 ORDER BY id DESC LIMIT 15", (full_name,))
        recent_sales = cursor.fetchall()
        graph_data = [float(row['price']) for row in recent_sales]
        graph_data.reverse() 

        cursor.close()
        conn.close()

        return jsonify({
            "total_earnings": float(total_earnings),
            "earnings_pct": calc_pct(earnings_this_week, earnings_last_week),
            "items_sold": int(items_sold),
            "sold_pct": calc_pct(sold_this_week, sold_last_week),
            "active_listings": int(active_listings),
            "listings_pct": calc_pct(listed_this_week, listed_last_week), 
            "top_percentage": top_pct,
            "graph_data": graph_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET: Dashboard Recent Activity
# -------------------------------
@app.route('/recent_activity/<string:email>', methods=['GET'])
def get_recent_activity(email):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT type, title, amount, date 
            FROM activity_logs 
            WHERE email=%s 
            ORDER BY date DESC LIMIT 5
        """
        cursor.execute(query, (email,))
        records = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        activity_list = []
        for row in records:
            activity_list.append({
                "type": row['type'],
                "title": row['title'],
                "amount": f"{float(row['amount']):,.2f}",
                "time": time_ago(row['date'])
            })
            
        return jsonify(activity_list), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch activity"}), 500


# ==========================================
# DOMAIN: MARKETPLACE (PRODUCTS)
# ==========================================

# -------------------------------
# POST: Add Product
# -------------------------------
@app.route("/products", methods=["POST"])
def add_product():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO products 
            (initial, full_name, title, subject, product_type, rate, price, review, condition_status, escrow, satisfied)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get("initial"),
            data.get("full_name"),
            data.get("title"),
            data.get("subject"),
            data.get("product_type", "Textbook"),
            data.get("rate", 0),
            data.get("price"),
            data.get("review"),
            data.get("condition_status"),
            data.get("escrow", True),
            data.get("satisfied", False)
        )

        cursor.execute(query, values)
        
        email = data.get("email")
        if email:
            cursor.execute("INSERT INTO activity_logs (email, type, title, amount) VALUES (%s, %s, %s, %s)", 
                           (email, 'Listed', data.get("title"), data.get("price")))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Product added"}), 201
        
    except Exception as e:
        return jsonify({"error": "Failed to add product"}), 500

# -------------------------------
# GET: Fetch All Products
# -------------------------------
@app.route("/products", methods=["GET"])
def get_products():
    satisfied = request.args.get("satisfied")
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if satisfied is not None:
            cursor.execute("SELECT * FROM products WHERE satisfied = %s", (int(satisfied),))
        else:
            cursor.execute("SELECT * FROM products")
            
        products = cursor.fetchall()
        
        cursor.execute("SELECT seller_name, AVG(rating) as avg_r FROM reviews GROUP BY seller_name")
        ratings_dict = {row['seller_name']: row['avg_r'] for row in cursor.fetchall()}
        
        for prod in products:
            seller = prod.get('full_name')
            prod['seller_rating'] = float(ratings_dict.get(seller) or 0.0)

        cursor.close()
        conn.close()
        return jsonify(products), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# PUT: Update Product
# -------------------------------
@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE products SET
        initial=%s, full_name=%s, title=%s, subject=%s, rate=%s, price=%s, review=%s, condition_status=%s, escrow=%s, satisfied=%s
        WHERE id=%s
    """
    values = (
        data.get("initial"), data.get("full_name"), data.get("title"), data.get("subject"),
        data.get("rate"), data.get("price"), data.get("review"), data.get("condition_status"),
        data.get("escrow"), data.get("satisfied"), id
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Product updated"})

# -------------------------------
# DELETE: Delete Satisfied Products
# -------------------------------
@app.route("/products/satisfied", methods=["DELETE"])
def delete_product():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE satisfied = 1")
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Deleted all satisfied products"})


# ==========================================
# DOMAIN: FREELANCE (SERVICES)
# ==========================================

# -------------------------------
# POST: Add Service
# -------------------------------
@app.route("/services", methods=["POST"])
def add_service():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO services 
            (initial, full_name, title, subject, category, rate, rate_format, description, schedule, escrow, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get("initial"), data.get("full_name"), data.get("title"), data.get("subject"),
            data.get("category"), data.get("rate"), data.get("rate_format"), data.get("description"),
            data.get("schedule", "Flexible"), data.get("escrow", True), True
        )

        cursor.execute(query, values)
        
        email = data.get("email")
        if email:
            cursor.execute("INSERT INTO activity_logs (email, type, title, amount) VALUES (%s, %s, %s, %s)", 
                           (email, 'Listed', data.get("title"), data.get("rate")))
                           
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Service successfully listed"}), 201
        
    except Exception as e:
        return jsonify({"error": "Failed to add service"}), 500

# -------------------------------
# GET: Fetch All Services
# -------------------------------
@app.route("/services", methods=["GET"])
def get_services():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM services WHERE active = 1")
        services = cursor.fetchall()
        
        cursor.execute("SELECT seller_name, AVG(rating) as avg_r FROM reviews GROUP BY seller_name")
        ratings_dict = {row['seller_name']: row['avg_r'] for row in cursor.fetchall()}
        
        for srv in services:
            seller = srv.get('full_name')
            srv['seller_rating'] = float(ratings_dict.get(seller) or 0.0)
            
        cursor.close()
        conn.close()
        return jsonify(services), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch services"}), 500

# -------------------------------
# POST: Subscribe to Service
# -------------------------------
@app.route('/subscribe', methods=['POST'])
def subscribe_service():
    data = request.json
    service_id = data.get('service_id')
    buyer_email = data.get('buyer_email')
    schedule = data.get('schedule')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM services WHERE id=%s", (service_id,))
        srv = cursor.fetchone()
        
        if not srv or not srv['active']:
            return jsonify({"error": "Service unavailable"}), 400
            
        cursor.execute("""
            UPDATE services 
            SET active=0, buyer_email=%s, booked_schedule=%s 
            WHERE id=%s
        """, (buyer_email, schedule, service_id))
        
        cursor.execute("INSERT INTO activity_logs (email, type, title, amount) VALUES (%s, %s, %s, %s)", 
                       (buyer_email, 'Subscribed', srv['title'], srv['rate']))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Subscribed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# POST: Unsubscribe
# -------------------------------
@app.route('/unsubscribe/<int:service_id>', methods=['POST'])
def unsubscribe_service(service_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT title, rate, buyer_email FROM services WHERE id=%s", (service_id,))
        srv = cursor.fetchone()
        
        cursor.execute("UPDATE services SET active=1, buyer_email=NULL, booked_schedule=NULL WHERE id=%s", (service_id,))
        
        if srv and srv['buyer_email']:
            cursor.execute("INSERT INTO activity_logs (email, type, title, amount) VALUES (%s, %s, %s, %s)", 
                           (srv['buyer_email'], 'Unsubscribed', srv['title'], srv['rate']))
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Unsubscribed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# DOMAIN: ESCROW & TRANSACTIONS
# ==========================================

# -------------------------------
# POST: Buy/Escrow Product
# -------------------------------
@app.route('/buy', methods=['POST'])
def buy_product():
    try:
        data = request.json
        product_id = data.get('product_id')
        buyer_email = data.get('buyer_email')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT full_name, title, price, satisfied FROM products WHERE id=%s", (product_id,))
        product = cursor.fetchone()
        if not product or product['satisfied']:
            cursor.close()
            conn.close()
            return jsonify({"error": "Product unavailable or already sold"}), 400
        price = float(product['price'] or 0)
        title = product['title']
        seller_fullname = product['full_name']

        cursor.execute("SELECT id, balance FROM users WHERE email=%s", (buyer_email,))
        buyer = cursor.fetchone()
        buyer_balance = float(buyer['balance'] or 0) if buyer else 0.0
        if not buyer or buyer_balance < price:
            cursor.close()
            conn.close()
            return jsonify({"error": "Insufficient funds in Wallet"}), 400
        cursor.execute("SELECT email FROM users WHERE full_name=%s", (seller_fullname,))
        seller = cursor.fetchone()
        seller_email = seller['email'] if seller else None
        new_balance = buyer_balance - price
        cursor.execute("UPDATE users SET balance=%s WHERE email=%s", (new_balance, buyer_email))
        cursor.execute("UPDATE products SET satisfied=1, buyer_email=%s WHERE id=%s", (buyer_email, product_id))
        cursor.execute("INSERT INTO activity_logs (email, type, title, amount) VALUES (%s, %s, %s, %s)", 
                       (buyer_email, 'Purchased', title, price))
        if seller_email:
            cursor.execute("INSERT INTO activity_logs (email, type, title, amount) VALUES (%s, %s, %s, %s)", 
                           (seller_email, 'Sold', title, price))
        cursor.execute("INSERT INTO transactions (email, type, amount, description) VALUES (%s, %s, %s, %s)", 
                       (buyer_email, 'Withdraw', price, f"Escrow Payment: {title}"))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Purchase successful, funds in escrow"}), 200

    except Exception as e:
        print("\n🚨 /buy CRASH:")
        print(traceback.format_exc())
        return jsonify({"error": f"Server crash: {str(e)}"}), 500

# -------------------------------
# POST: Submit Review
# -------------------------------
@app.route('/review', methods=['POST'])
def submit_review():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO reviews (reviewer_email, seller_name, rating, comment) VALUES (%s, %s, %s, %s)"
        values = (data.get('reviewer_email'), data.get('seller_name'), data.get('rating'), data.get('comment'))
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Review submitted successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# DOMAIN: WALLET
# ==========================================

# -------------------------------
# GET: Wallet Balance
# -------------------------------
@app.route('/wallet/<string:email>', methods=['GET'])
def get_balance(email):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT balance FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user: return jsonify({"balance": float(user['balance'])}), 200
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# -------------------------------
# POST: Process Wallet Transaction
# -------------------------------
@app.route('/wallet/transaction', methods=['POST'])
def handle_transaction():
    data = request.json
    email = data.get('email')
    amount = float(data.get('amount', 0))
    action = data.get('action') 

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT balance FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        
        if not user: return jsonify({"error": "User not found"}), 404

        current_balance = float(user['balance'])
        
        if action == 'deposit':
            new_balance = current_balance + amount
        elif action == 'withdraw':
            if current_balance < amount:
                return jsonify({"error": "Insufficient funds"}), 400
            new_balance = current_balance - amount
        else:
            return jsonify({"error": "Invalid action"}), 400

        cursor.execute("UPDATE users SET balance=%s WHERE email=%s", (new_balance, email))
        cursor.execute("INSERT INTO transactions (email, type, amount, description) VALUES (%s, %s, %s, %s)", 
                       (email, action.capitalize(), amount, f"Wallet {action}"))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Transaction successful", "new_balance": new_balance}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET: Transaction History
# -------------------------------
@app.route('/wallet/history/<string:email>', methods=['GET'])
def get_wallet_history(email):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM transactions WHERE email=%s ORDER BY date DESC", (email,))
        history = cursor.fetchall()
        cursor.close()
        conn.close()

        for row in history:
            if row.get('date'):
                row['date'] = row['date'].strftime('%b %d, %I:%M %p')
                
        return jsonify(history), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# DOMAIN: INBOX & MESSAGING
# ==========================================

# -------------------------------
# POST: Send Message
# -------------------------------
@app.route('/messages', methods=['POST'])
def send_message():
    data = request.json
    sender = data.get('sender_name')
    receiver = data.get('receiver_name')
    text = data.get('message_text')
    
    if not sender or not receiver or not text:
        return jsonify({"error": "Missing data"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender_name, receiver_name, message_text) VALUES (%s, %s, %s)", 
                   (sender, receiver, text))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Message sent"}), 201

# -------------------------------
# GET: Chat Messages
# -------------------------------
@app.route('/messages/<string:user1>/<string:user2>', methods=['GET'])
def get_messages(user1, user2):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("UPDATE messages SET is_read = 1 WHERE receiver_name = %s AND sender_name = %s AND is_read = 0", 
                   (user1, user2))
    conn.commit()

    query = """
        SELECT * FROM messages 
        WHERE (sender_name = %s AND receiver_name = %s) 
           OR (sender_name = %s AND receiver_name = %s)
        ORDER BY timestamp ASC
    """
    cursor.execute(query, (user1, user2, user2, user1))
    messages = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    for msg in messages:
        msg['timestamp'] = msg['timestamp'].strftime("%I:%M %p") 
        
    return jsonify(messages), 200

# -------------------------------
# GET: User Inbox
# -------------------------------
@app.route('/inbox/<string:username>', methods=['GET'])
def get_inbox(username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM messages 
            WHERE sender_name = %s OR receiver_name = %s 
            ORDER BY timestamp DESC
        """
        cursor.execute(query, (username, username))
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()

        conversations = {}
        for msg in messages:
            partner = msg['receiver_name'] if msg['sender_name'] == username else msg['sender_name']
            if partner not in conversations:
                conversations[partner] = {
                    "partner_name": partner,
                    "last_message": msg['message_text'],
                    "timestamp": msg['timestamp'].strftime("%I:%M %p")
                }

        return jsonify(list(conversations.values())), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET: Unread Notifications
# -------------------------------
@app.route('/inbox/unread/<string:username>', methods=['GET'])
def get_unread_count(username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(id) as unread FROM messages WHERE receiver_name = %s AND is_read = 0", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"unread_count": result['unread'] if result else 0}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET: My Hub (Products & Subs)
# -------------------------------
@app.route('/my_hub/<string:email>', methods=['GET'])
def get_my_hub(email):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get Escrowed Products
        cursor.execute("SELECT * FROM products WHERE buyer_email = %s AND satisfied = 1", (email,))
        purchased_products = cursor.fetchall()
        
        # 2. Get Active Subscriptions
        cursor.execute("SELECT * FROM services WHERE buyer_email = %s AND active = 0", (email,))
        subscriptions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify({"products": purchased_products, "subscriptions": subscriptions}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
