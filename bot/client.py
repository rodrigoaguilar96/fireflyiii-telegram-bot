import logging
import requests
from bot.config import FIREFLY_URL, FIREFLY_TOKEN

HEADERS = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}

def safe_get(endpoint, params=None):
    try:
        response = requests.get(f"{FIREFLY_URL}{endpoint}", headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        logging.error(f"Error en GET {endpoint}: {e}")
        return []

def get_accounts(account_type=None):
    params = {"limit": 1000}
    if account_type:
        params["type"] = account_type
    return safe_get("/api/v1/accounts", params)

def create_transaction(payload):
    return requests.post(f"{FIREFLY_URL}/api/v1/transactions", json=payload, headers=HEADERS)

def create_account(name, acc_type="expense"):
    payload = {"name": name, "type": acc_type, "currency_id": 1}
    return requests.post(f"{FIREFLY_URL}/api/v1/accounts", json=payload, headers=HEADERS)