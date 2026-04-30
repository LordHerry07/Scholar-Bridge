import requests

BASE_URL = "http://127.0.0.1:5000"

#---------------------------------------
# Users Table
#---------------------------------------
# POST - Signin User
def add_user(full_name, email, password):
    url = f"{BASE_URL}/users"
    payload = {
        "full_name": full_name,
        "email": email,
        "password": password
    }

    response = requests.post(url, json=payload)
    return response.json()

# POST - Login User
def log_user(email, password):
    url = f"{BASE_URL}/login"
    payload = {
        "email": email,
        "password": password
    }
    return requests.post(url, json=payload)
# GET - Users
def get_users():
    url = f"{BASE_URL}/users"
    response = requests.get(url)
    return response.json()


# PUT - Update Users
def update_user(user_id, full_name, email, password):
    url = f"{BASE_URL}/users/{user_id}"
    payload = {
        "full_name": full_name,
        "email": email,
        "password": password
    }

    response = requests.put(url, json=payload)
    return response.json()


# DELETE - Users
def delete_user(user_id):
    url = f"{BASE_URL}/users/{user_id}"
    response = requests.delete(url)
    return response.json()

#---------------------------------------
# Products Table
#---------------------------------------
def add_product(data):
    response = requests.post(f"{BASE_URL}/products", json=data)

    if response.status_code == 201:
        return response.json()
    else:
        print("POST failed:", response.text)
        return None

def get_user_stats(full_name):
    url = f"{BASE_URL}/stats/{full_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("GET Stats failed:", response.text)
        return None    
    

def get_products(satisfied=None):
    params = {}

    if satisfied is not None:
        params["satisfied"] = int(satisfied)

    response = requests.get(f"{BASE_URL}/products", params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print("GET failed:", response.text)
        return None

def update_product(product_id, data):
    response = requests.put(f"{BASE_URL}/products/{product_id}", json=data)

    if response.status_code == 200:
        return response.json()
    else:
        print("PUT failed:", response.text)
        return None

def delete_satisfied_products():
    response = requests.delete(f"{BASE_URL}/products/satisfied")

    if response.status_code == 200:
        return response.json()
    else:
        print("DELETE failed:", response.text)
        return None

# ---------------------------------------
# Chat Messages
# ---------------------------------------
def send_message(sender, receiver, text):
    url = f"{BASE_URL}/messages"
    payload = {
        "sender_name": sender,
        "receiver_name": receiver,
        "message_text": text
    }
    response = requests.post(url, json=payload)
    return response.status_code == 201

def get_messages(user1, user2):
    url = f"{BASE_URL}/messages/{user1}/{user2}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def get_inbox(username):
    url = f"{BASE_URL}/inbox/{username}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# ---------------------------------------
# Escrow / Purchasing
# ---------------------------------------
def buy_product(product_id, buyer_email):
    url = f"{BASE_URL}/buy"
    payload = {
        "product_id": product_id,
        "buyer_email": buyer_email
    }

    print(f"🚨 DEBUG -> Sending to API | Product ID: {product_id} | Buyer: {buyer_email}")

    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return True
    else:
        print("Purchase failed:", response.text)
        return False

# ---------------------------------------
# Wallet
# ---------------------------------------
def get_wallet_balance(email):
    url = f"{BASE_URL}/wallet/{email}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('balance', 0.0)
    return 0.0

def process_wallet_transaction(email, amount, action):
    url = f"{BASE_URL}/wallet/transaction"
    payload = {
        "email": email,
        "amount": amount,
        "action": action
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

# ---------------------------------------
# Public Profile
# ---------------------------------------
def get_user_profile(fullname):
    url = f"{BASE_URL}/profile/{fullname}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def get_wallet_history(email):
    url = f"{BASE_URL}/wallet/history/{email}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []