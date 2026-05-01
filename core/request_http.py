import requests
from requests.exceptions import RequestException
from kivy.clock import Clock

BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 5  # Seconds before giving up on the server

# ---------------------------------------
# Network Armor
# ---------------------------------------
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

# A dummy response for functions that expect an object with a status_code
class FailedResponse:
    status_code = 500
    def json(self): return {"error": "Connection failed"}

# ---------------------------------------
# Users Table
# ---------------------------------------
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

# ---------------------------------------
# Products Table
# ---------------------------------------
def add_product(data):
    response = safe_request(requests.post, f"{BASE_URL}/products", json=data)
    if response and response.status_code == 201:
        return response.json()
    return None

def get_user_stats(full_name):
    url = f"{BASE_URL}/stats/{full_name}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return None

def get_products(satisfied=None):
    params = {}
    if satisfied is not None:
        params["satisfied"] = int(satisfied)
    
    response = safe_request(requests.get, f"{BASE_URL}/products", params=params)
    if response and response.status_code == 200:
        return response.json()
    return []

def update_product(product_id, data):
    response = safe_request(requests.put, f"{BASE_URL}/products/{product_id}", json=data)
    if response and response.status_code == 200:
        return response.json()
    return None

def delete_satisfied_products():
    response = safe_request(requests.delete, f"{BASE_URL}/products/satisfied")
    if response and response.status_code == 200:
        return response.json()
    return None

# ---------------------------------------
# Chat Messages
# ---------------------------------------
def send_message(sender, receiver, text):
    url = f"{BASE_URL}/messages"
    payload = {"sender_name": sender, "receiver_name": receiver, "message_text": text}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 201

def get_messages(user1, user2):
    url = f"{BASE_URL}/messages/{user1}/{user2}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return []

def get_inbox(username):
    url = f"{BASE_URL}/inbox/{username}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return []

# ---------------------------------------
# Escrow / Purchasing
# ---------------------------------------
def buy_product(product_id, buyer_email):
    url = f"{BASE_URL}/buy"
    payload = {"product_id": product_id, "buyer_email": buyer_email}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 200

# ---------------------------------------
# Wallet
# ---------------------------------------
def get_wallet_balance(email):
    url = f"{BASE_URL}/wallet/{email}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json().get('balance', 0.0)
    return 0.0

def process_wallet_transaction(email, amount, action):
    url = f"{BASE_URL}/wallet/transaction"
    payload = {"email": email, "amount": amount, "action": action}
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 200

def get_wallet_history(email):
    url = f"{BASE_URL}/wallet/history/{email}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return []

# ---------------------------------------
# Public Profile & Reviews
# ---------------------------------------
def get_user_profile(fullname):
    url = f"{BASE_URL}/profile/{fullname}"
    response = safe_request(requests.get, url)
    if response and response.status_code == 200:
        return response.json()
    return None

def submit_review(reviewer_email, seller_name, rating, comment):
    url = f"{BASE_URL}/review"
    payload = {
        "reviewer_email": reviewer_email, 
        "seller_name": seller_name, 
        "rating": rating, 
        "comment": comment
    }
    response = safe_request(requests.post, url, json=payload)
    return response is not None and response.status_code == 201
