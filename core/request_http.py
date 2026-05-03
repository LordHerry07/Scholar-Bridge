import requests
from requests.exceptions import RequestException
from kivy.clock import Clock
import os

CONFIG_FILE = 'server_config.txt'
TIMEOUT = 5  # Seconds before giving up on the server

# ==========================================
# DOMAIN: NETWORK ARMOR & UTILS
# ==========================================

# -------------------------------
# CONFIG: Server IP Management
# -------------------------------
def load_base_url():
    """Loads the saved server IP, defaulting to localhost if none exists."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return f.read().strip()
    return "http://127.0.0.1:5000"

BASE_URL = load_base_url()

def set_base_url(new_url):
    """Updates the global API bridge and saves it locally."""
    global BASE_URL
    if not new_url.startswith("http"):
        new_url = "http://" + new_url
    BASE_URL = new_url
    with open(CONFIG_FILE, 'w') as f:
        f.write(BASE_URL)

# -------------------------------
# CONFIG: Safety Wrappers
# -------------------------------
def show_network_error():
    """Safely triggers the UI Notification Modal from outside the main thread."""
    from core.main_interface import NotificationModal
    Clock.schedule_once(lambda dt: NotificationModal().show(
        "Network Error", 
        "Cannot reach ScholarBridge servers. Please check your connection.", 
        is_error=True
    ), 0)

def safe_request(method, url, **kwargs):
    """Wraps API calls to prevent Kivy freezes and handle timeouts."""
    try:
        kwargs['timeout'] = TIMEOUT
        response = method(url, **kwargs)
        return response
    except RequestException as e:
        print(f"🚨 API CONNECTION FAILED: {e}")
        show_network_error()
        return None

class FailedResponse:
    status_code = 500
    def json(self): return {"error": "Connection failed"}


# ==========================================
# DOMAIN: USERS & AUTHENTICATION
# ==========================================

# -------------------------------
# POST: Auth (Signup & Login)
# -------------------------------
def add_user(full_name, email, password):
    url = f"{BASE_URL}/users"
    payload = {"full_name": full_name, "email": email, "password": password}
    response = safe_request(requests.post, url, json=payload)
    return response.json() if response else {"error": "Failed"}

def log_user(email, password):
    url = f"{BASE_URL}/login"
    payload = {"email": email, "password": password}
    response = safe_request(requests.post, url, json=payload)
    return response if response else FailedResponse()

# -------------------------------
# POST: Password Reset
# -------------------------------
def request_password_reset(email):
    url = f"{BASE_URL}/request_reset"
    payload = {"email": email}
    response = safe_request(requests.post, url, json=payload)
    if response is None: return {"success": False, "error": "Server connection failed"}
    if response.status_code == 200:
        data = response.json()
        return {"success": True, "debug_otp": data.get("debug_otp")}
    try: error_msg = response.json().get("error", "Error requesting OTP")
    except: error_msg = f"Server Error ({response.status_code})"
    return {"success": False, "error": error_msg}

def verify_reset_otp(email, otp):
    url = f"{BASE_URL}/verify_reset"
    payload = {"email": email, "otp": otp}
    response = safe_request(requests.post, url, json=payload)
    if response is None: return {"success": False, "error": "Server is offline"}
    if response.status_code == 200: return {"success": True}
    try: error_msg = response.json().get("error", "Invalid or expired code")
    except Exception: error_msg = f"Server Error ({response.status_code})"
    return {"success": False, "error": error_msg}

def finalize_password_reset(email, new_password):
    url = f"{BASE_URL}/reset_password"
    payload = {"email": email, "password": new_password}
    response = safe_request(requests.post, url, json=payload)
    if response is None: return {"success": False, "error": "Server is offline"}
    if response.status_code == 200: return {"success": True}
    try: error_msg = response.json().get("error", "Could not update password")
    except Exception: error_msg = f"Server Error ({response.status_code})"
    return {"success": False, "error": error_msg}

# -------------------------------
# CRUD: User Management
# -------------------------------
def get_users():
    url = f"{BASE_URL}/users"
    response = safe_request(requests.get, url)
    return response.json() if response else []

def update_user(user_id, full_name, email, password):
    url = f"{BASE_URL}/users/{user_id}"
    payload = {"full_name": full_name, "email": email, "password": password}
    response = safe_request(requests.put, url, json=payload)
    return response.json() if response else {"error": "Failed"}

def delete_user(user_id):
    url = f"{BASE_URL}/users/{user_id}"
    response = safe_request(requests.delete, url)
    return response.json() if response else {"error": "Failed"}


# ==========================================
# DOMAIN: PROFILES & DASHBOARD
# ==========================================

# -------------------------------
# GET: Profile Data
# -------------------------------
def get_user_profile(fullname):
    url = f"{BASE_URL}/profile/{fullname}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return {"full_name": fullname, "rating": 0.0, "products": []}

def get_user_stats(full_name):
    url = f"{BASE_URL}/stats/{full_name}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return {
        "total_earnings": 0.00, "active_listings": 0, "items_sold": 0,
        "rating": 0.0, "graph_data": [0] * 15
    }

def get_recent_activity(email):
    url = f"{BASE_URL}/recent_activity/{email}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return []

# -------------------------------
# PUT: Update Profile
# -------------------------------
def update_profile(email, old_name, new_name, new_password, role, age, birthday, location):
    url = f"{BASE_URL}/update_profile"
    payload = {
        "email": email, "old_name": old_name, "full_name": new_name, "password": new_password,
        "role": role, "age": age, "birthday": birthday, "location": location
    }
    response = safe_request(requests.put, url, json=payload)
    if response is None: return {"success": False, "error": "Could not connect to server."}
    if response.status_code == 200: return {"success": True, "message": "Updated successfully!"}
    try: error_msg = response.json().get("error", "Update failed.")
    except: error_msg = "Unknown error occurred."
    return {"success": False, "error": error_msg}


# ==========================================
# DOMAIN: MARKETPLACE (PRODUCTS)
# ==========================================

# -------------------------------
# CRUD: Products
# -------------------------------
def add_product(data):
    response = safe_request(requests.post, f"{BASE_URL}/products", json=data)
    return response.json() if response and response.status_code == 201 else None

def get_products(satisfied=None):
    params = {}
    if satisfied is not None: params["satisfied"] = int(satisfied)
    response = safe_request(requests.get, f"{BASE_URL}/products", params=params)
    return response.json() if response and response.status_code == 200 else []

def update_product(product_id, data):
    response = safe_request(requests.put, f"{BASE_URL}/products/{product_id}", json=data)
    return response.json() if response and response.status_code == 200 else None

def delete_satisfied_products():
    response = safe_request(requests.delete, f"{BASE_URL}/products/satisfied")
    return response.json() if response and response.status_code == 200 else None


# ==========================================
# DOMAIN: FREELANCE (SERVICES)
# ==========================================

# -------------------------------
# CRUD: Services & Subscriptions
# -------------------------------
def add_service(data):
    url = f"{BASE_URL}/services"
    response = safe_request(requests.post, url, json=data)
    return response.json() if response and response.status_code == 201 else None

def get_services():
    url = f"{BASE_URL}/services"
    response = safe_request(requests.get, url)
    return response.json() if response and response.status_code == 200 else []

def subscribe_service(service_id, buyer_email, schedule):
    url = f"{BASE_URL}/subscribe"
    payload = {"service_id": service_id, "buyer_email": buyer_email, "schedule": schedule}
    res = safe_request(requests.post, url, json=payload)
    return res is not None and res.status_code == 200

def unsubscribe_service(service_id):
    url = f"{BASE_URL}/unsubscribe/{service_id}"
    res = safe_request(requests.post, url)
    return res is not None and res.status_code == 200


# ==========================================
# DOMAIN: ESCROW & TRANSACTIONS
# ==========================================

# -------------------------------
# POST: Escrow Triggers
# -------------------------------
def buy_product(product_id, buyer_email):
    url = f"{BASE_URL}/buy"
    payload = {"product_id": product_id, "buyer_email": buyer_email}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 200

def submit_review(reviewer_email, seller_name, rating, comment):
    url = f"{BASE_URL}/review"
    payload = {"reviewer_email": reviewer_email, "seller_name": seller_name, "rating": rating, "comment": comment}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 201


# ==========================================
# DOMAIN: WALLET
# ==========================================

# -------------------------------
# GET & POST: Wallet Actions
# -------------------------------
def get_wallet_balance(email):
    url = f"{BASE_URL}/wallet/{email}"
    response = safe_request(requests.get, url)
    return response.json().get('balance', 0.0) if response and response.status_code == 200 else 0.0

def process_wallet_transaction(email, amount, action):
    url = f"{BASE_URL}/wallet/transaction"
    payload = {"email": email, "amount": amount, "action": action}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 200

def get_wallet_history(email):
    url = f"{BASE_URL}/wallet/history/{email}"
    response = safe_request(requests.get, url)
    return response.json() if response and response.status_code == 200 else []


# ==========================================
# DOMAIN: INBOX & MESSAGING
# ==========================================

# -------------------------------
# GET & POST: Chat Actions
# -------------------------------
def send_message(sender, receiver, text):
    url = f"{BASE_URL}/messages"
    payload = {"sender_name": sender, "receiver_name": receiver, "message_text": text}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 201

def get_messages(user1, user2):
    url = f"{BASE_URL}/messages/{user1}/{user2}"
    response = safe_request(requests.get, url)
    return response.json() if response and response.status_code == 200 else []

def get_inbox(username):
    url = f"{BASE_URL}/inbox/{username}"
    response = safe_request(requests.get, url)
    return response.json() if response and response.status_code == 200 else []

def get_unread_count(username):
    url = f"{BASE_URL}/inbox/unread/{username}"
    response = safe_request(requests.get, url)
    return response.json().get('unread_count', 0) if response and response.status_code == 200 else 0

def get_my_hub(email):
    url = f"{BASE_URL}/my_hub/{email}"
    res = safe_request(requests.get, url)
    return res.json() if res and res.status_code == 200 else {"products": [], "subscriptions": []}
