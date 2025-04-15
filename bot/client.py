import requests
from bot.config import FIREFLY_URL, FIREFLY_TOKEN

HEADERS = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}

def get_accounts(account_type=None):
    url = f"{FIREFLY_URL}/api/v1/accounts"
    if account_type:
        url += f"?type={account_type}"
    return requests.get(url, headers=HEADERS).json().get("data", [])

def create_transaction(payload):
    return requests.post(f"{FIREFLY_URL}/api/v1/transactions", json=payload, headers=HEADERS)

def create_account(name, acc_type="expense"):
    payload = {"name": name, "type": acc_type, "currency_id": 1}
    return requests.post(f"{FIREFLY_URL}/api/v1/accounts", json=payload, headers=HEADERS)
