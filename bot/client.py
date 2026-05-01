import logging
import requests
from typing import Optional

from bot.config import FIREFLY_URL, FIREFLY_TOKEN
from bot.cache import cache

HEADERS = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
HTTP_TIMEOUT = 10  # seconds


def _build_headers() -> dict:
    """Build headers with validation."""
    if not FIREFLY_TOKEN:
        logging.error("FIREFLY_III_API_TOKEN is not set!")
        return {}
    return {"Authorization": f"Bearer {FIREFLY_TOKEN}"}


def safe_get(endpoint: str, params: Optional[dict] = None) -> list:
    """Safe GET request with timeout and error handling."""
    try:
        response = requests.get(
            f"{FIREFLY_URL}{endpoint}",
            headers=HEADERS,
            params=params,
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.exceptions.Timeout:
        logging.error(f"Timeout en GET {endpoint}")
        return []
    except Exception as e:
        logging.error(f"Error en GET {endpoint}: {e}")
        return []


def safe_post(endpoint: str, json_payload: dict) -> requests.Response:
    """Safe POST request with timeout and error handling."""
    return requests.post(
        f"{FIREFLY_URL}{endpoint}",
        json=json_payload,
        headers=HEADERS,
        timeout=HTTP_TIMEOUT,
    )


def get_accounts(account_type: Optional[str] = None, use_cache: bool = True) -> list:
    """Get accounts with optional caching."""
    cache_key = f"accounts:{account_type or 'all'}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    params = {"limit": 1000}
    if account_type:
        params["type"] = account_type

    accounts = safe_get("/api/v1/accounts", params)
    if account_type and not accounts:
        logging.warning(
            "No accounts returned with API filter type=%s; falling back to local filter",
            account_type,
        )
        all_accounts = safe_get("/api/v1/accounts", {"limit": 1000})
        accounts = [
            account
            for account in all_accounts
            if account.get("attributes", {}).get("type") == account_type
        ]
    if use_cache and accounts:
        cache.set(cache_key, accounts)
    return accounts


def get_categories() -> list:
    """Get all categories from Firefly III."""
    cached = cache.get("categories")
    if cached is not None:
        return cached

    categories = safe_get("/api/v1/categories", params={"limit": 100})
    if categories:
        cache.set("categories", categories)
    return categories


def get_budgets() -> list:
    """Get all budgets from Firefly III."""
    cached = cache.get("budgets")
    if cached is not None:
        return cached

    budgets = safe_get("/api/v1/budgets", params={"limit": 50})
    if budgets:
        cache.set("budgets", budgets)
    return budgets


def get_bills(use_cache: bool = True) -> list:
    """Get all bills from Firefly III with optional caching."""
    cache_key = "bills"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    bills = safe_get("/api/v1/bills", params={"limit": 100})
    if use_cache and bills:
        cache.set(cache_key, bills)
    return bills


def create_transaction(payload: dict) -> requests.Response:
    """Create a new transaction in Firefly III."""
    return safe_post("/api/v1/transactions", payload)


def create_account(name: str, acc_type: str = "expense") -> requests.Response:
    """Create a new account in Firefly III."""
    payload = {"name": name, "type": acc_type}
    return safe_post("/api/v1/accounts", payload)


def refresh_cache() -> None:
    """Force refresh all cached data."""
    cache.clear()
    logging.info("Cache refreshed")
