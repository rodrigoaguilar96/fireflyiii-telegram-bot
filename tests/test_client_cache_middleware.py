import time
from decimal import Decimal

import pytest
import requests

from bot import client, middleware
from bot.cache import TTLCache
from bot.handlers import expense
from tests.conftest import FakeCallbackQuery, FakeContext, FakeMessage, FakeResponse, FakeUpdate, button_texts


def test_ttl_cache_get_set_expire_invalidate_clear():
    cache = TTLCache(default_ttl=1)
    assert cache.get("missing") is None

    cache.set("key", "value")
    assert cache.get("key") == "value"

    cache.set("expired", "value", ttl=-1)
    assert cache.get("expired") is None

    cache.invalidate("key")
    assert cache.get("key") is None

    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None


def test_safe_get_success_timeout_and_error(monkeypatch):
    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *args, **kwargs: FakeResponse({"data": [{"id": "1"}]}),
    )
    assert client.safe_get("/ok") == [{"id": "1"}]

    def timeout(*args, **kwargs):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(client.requests, "get", timeout)
    assert client.safe_get("/timeout") == []

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(client.requests, "get", boom)
    assert client.safe_get("/boom") == []


def test_safe_get_and_safe_post_build_api_headers(monkeypatch):
    captured_get = {}
    captured_post = {}

    def fake_get(url, **kwargs):
        captured_get["url"] = url
        captured_get["headers"] = kwargs.get("headers", {})
        return FakeResponse({"data": []})

    def fake_post(url, **kwargs):
        captured_post["url"] = url
        captured_post["headers"] = kwargs.get("headers", {})
        return FakeResponse({"data": {}})

    monkeypatch.setattr(client, "FIREFLY_TOKEN", "test-token")
    monkeypatch.setattr(client.requests, "get", fake_get)
    monkeypatch.setattr(client.requests, "post", fake_post)

    client.safe_get("/api/v1/accounts")
    client.safe_post("/api/v1/transactions", {"transactions": []})

    assert captured_get["headers"] == {
        "Authorization": "Bearer test-token",
        "Accept": "application/vnd.api+json",
    }
    assert captured_post["headers"] == {
        "Authorization": "Bearer test-token",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/json",
    }


def test_get_accounts_uses_cache_and_local_filter_fallback(monkeypatch, all_accounts):
    local_cache = TTLCache(default_ttl=60)
    monkeypatch.setattr(client, "cache", local_cache)

    calls = []

    def fake_safe_get(endpoint, params=None):
        calls.append(params)
        if params and params.get("type") == "asset":
            return []
        return all_accounts

    monkeypatch.setattr(client, "safe_get", fake_safe_get)

    accounts = client.get_accounts("asset")
    assert [a["id"] for a in accounts] == ["asset-1", "asset-2"]
    assert len(calls) == 2

    cached = client.get_accounts("asset")
    assert cached == accounts
    assert len(calls) == 2


def test_refresh_cache_clears_cache(monkeypatch):
    local_cache = TTLCache(default_ttl=60)
    local_cache.set("x", "y")
    monkeypatch.setattr(client, "cache", local_cache)

    client.refresh_cache()

    assert local_cache.get("x") is None


def test_get_bills_uses_cache(monkeypatch, bills):
    local_cache = TTLCache(default_ttl=60)
    monkeypatch.setattr(client, "cache", local_cache)

    calls = []

    def fake_safe_get(endpoint, params=None):
        calls.append((endpoint, params))
        return bills

    monkeypatch.setattr(client, "safe_get", fake_safe_get)

    assert client.get_bills() == bills
    assert client.get_bills() == bills
    assert calls == [("/api/v1/bills", {"limit": 100})]


def test_get_bills_for_period_sends_start_end_and_limit(monkeypatch, bills):
    calls = []

    def fake_safe_get(endpoint, params=None):
        calls.append((endpoint, params))
        return bills

    monkeypatch.setattr(client, "safe_get", fake_safe_get)

    result = client.get_bills_for_period("2026-05-01", "2026-05-31")

    assert result == bills
    assert calls == [
        (
            "/api/v1/bills",
            {"start": "2026-05-01", "end": "2026-05-31", "limit": 100},
        )
    ]


def test_get_bills_for_period_cache_is_optional_and_isolated(monkeypatch, bills):
    local_cache = TTLCache(default_ttl=60)
    monkeypatch.setattr(client, "cache", local_cache)
    calls = []

    def fake_safe_get(endpoint, params=None):
        calls.append(params)
        return bills

    monkeypatch.setattr(client, "safe_get", fake_safe_get)

    assert client.get_bills_for_period("2026-05-01", "2026-05-31") == bills
    assert client.get_bills_for_period("2026-05-01", "2026-05-31") == bills
    assert len(calls) == 2
    assert local_cache.get("bills:2026-05-01:2026-05-31") is None

    assert client.get_bills_for_period("2026-05-01", "2026-05-31", use_cache=True) == bills
    assert client.get_bills_for_period("2026-05-01", "2026-05-31", use_cache=True) == bills
    assert len(calls) == 3
    assert local_cache.get("bills:2026-05-01:2026-05-31") == bills

    assert client.get_bills() == bills
    assert local_cache.get("bills") == bills


@pytest.mark.asyncio
async def test_auth_open_allowed_and_denied(monkeypatch):
    monkeypatch.setattr(middleware, "ALLOWED_USER_IDS", [])
    assert await middleware.require_auth(FakeUpdate(message=FakeMessage(), user_id=1), FakeContext())

    monkeypatch.setattr(middleware, "ALLOWED_USER_IDS", [1])
    assert await middleware.require_auth(FakeUpdate(message=FakeMessage(), user_id=1), FakeContext())

    denied_message = FakeMessage()
    assert not await middleware.require_auth(
        FakeUpdate(message=denied_message, user_id=2), FakeContext()
    )
    assert "No estás autorizado" in denied_message.replies[-1]["text"]

    denied_query = FakeCallbackQuery("x")
    assert not await middleware.require_auth(
        FakeUpdate(callback_query=denied_query, user_id=2), FakeContext()
    )
    assert denied_query.answers[-1]["show_alert"] is True


def test_validation_helpers():
    assert middleware.sanitize_text("  abc  ", 2) == "ab"
    assert middleware.validate_amount("12,55") == Decimal("12.55")
    assert middleware.validate_amount("12.10") == Decimal("12.10")
    assert middleware.validate_amount("12.1") == Decimal("12.10")
    assert middleware.validate_amount("10.000") == Decimal("10.00")
    assert middleware.validate_amount("12.1200") == Decimal("12.12")
    assert middleware.validate_amount("12.123") is None
    assert middleware.validate_amount("nope") is None
    assert middleware.validate_amount("NaN") is None


def test_keyboard_and_summary_helpers(expense_accounts, mixed_bills):
    context = FakeContext(user_data={"recent_destinations": ["uber"]})

    destination_rows = expense._build_destination_keyboard(expense_accounts, context)
    destination_buttons = [button.text for row in destination_rows for button in row]
    assert "🕐 uber" in destination_buttons
    assert "⏭️ Sin cuenta destino" in destination_buttons

    category_buttons = [button.text for row in expense._build_category_keyboard([]) for button in row]
    assert "⏭️ Sin categoría" in category_buttons

    usable_bills = expense._get_usable_active_bills(mixed_bills)
    assert [bill["id"] for bill in usable_bills] == ["bill-2", "bill-1"]

    bill_keyboard = expense._build_bill_keyboard(usable_bills)
    assert [button.text for button in bill_keyboard[0]] == ["gym", "internet hogar"]
    assert [button.text for button in bill_keyboard[-1]] == ["⏭️ Sin suscripción/factura"]

    markup = expense._get_keyboard_with_cancel([])
    assert "❌ Cancelar" in [button.text for row in markup.inline_keyboard for button in row]

    summary = expense._build_confirmation_summary(
        {
            "amount": Decimal("12.55"),
            "description": "supermercado pingo doce",
            "origin": "tarjeta",
            "destination": None,
            "category": None,
            "budget": None,
            "bill_name": "internet hogar",
            "tags": [],
        }
    )
    assert "supermercado pingo doce" in summary
    assert "_Sin cuenta destino_" in summary
    assert "internet hogar" in summary
