import requests

BASE_URL = "http://192.168.254.110:5000"

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