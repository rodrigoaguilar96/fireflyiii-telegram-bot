from datetime import datetime

import pytest

from bot.handlers import subscriptions
from tests.conftest import FakeCallbackQuery, FakeContext, FakeUpdate


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 2, 15, 12, 0, tzinfo=tz)


def test_get_current_period_bounds_uses_configured_timezone_month_end(monkeypatch):
    monkeypatch.setattr(subscriptions, "TIMEZONE", "Europe/Lisbon")
    monkeypatch.setattr(subscriptions, "datetime", FixedDateTime)

    assert subscriptions.get_current_period_bounds() == ("2026-02-01", "2026-02-28")


def test_extract_pending_subscriptions_filters_unpaid_due_instances(subscription_bills):
    pending = subscriptions.extract_pending_subscriptions(
        subscription_bills,
        "2026-05-01",
        "2026-05-31",
    )

    assert [item["name"] for item in pending] == [
        "Netflix *unsafe* [name]",
        "Internet",
        "Unknown amount",
    ]
    assert [item["due_date"] for item in pending] == [
        "2026-05-04",
        "2026-05-14",
        "2026-05-22",
    ]
    assert "Gym" not in [item["name"] for item in pending]
    assert "Rent" not in [item["name"] for item in pending]
    assert "Insurance" not in [item["name"] for item in pending]
    assert "Cloud" not in [item["name"] for item in pending]
    assert "Old service" not in [item["name"] for item in pending]


def test_build_pending_subscriptions_message_formats_amounts_and_plain_text(subscription_bills):
    message = subscriptions.build_pending_subscriptions_message(
        subscription_bills,
        "2026-05-01",
        "2026-05-31",
    )

    assert "Suscripciones pendientes del período actual" in message
    assert "• Netflix *unsafe* [name] — vence 2026-05-04 — 10.00 €" in message
    assert "• Internet — vence 2026-05-14 — 20.00 - 25.50 EUR" in message
    assert "• Unknown amount — vence 2026-05-22 — monto no disponible" in message
    assert "Gym" not in message
    assert "Rent" not in message
    assert "Insurance" not in message


def test_build_pending_subscriptions_message_empty_state():
    assert subscriptions.build_pending_subscriptions_message([], "2026-05-01", "2026-05-31") == (
        "✅ No tenés suscripciones pendientes en el período actual."
    )


def test_build_pending_subscriptions_message_falls_back_for_invalid_amount():
    bills = [
        {
            "attributes": {
                "name": "Invalid amount",
                "active": True,
                "pay_dates": ["2026-05-09"],
                "paid_dates": [],
                "amount_min": "not-a-number",
                "amount_max": "not-a-number",
                "currency_code": "EUR",
            }
        }
    ]

    message = subscriptions.build_pending_subscriptions_message(
        bills,
        "2026-05-01",
        "2026-05-31",
    )

    assert "• Invalid amount — vence 2026-05-09 — monto no disponible" in message


def test_extract_pending_subscriptions_keeps_payments_one_to_one():
    bills = [
        {
            "attributes": {
                "name": "Weekly service",
                "active": True,
                "pay_dates": ["2026-05-01", "2026-05-08"],
                "paid_dates": ["2026-05-05"],
                "amount_min": "5.00",
                "amount_max": "5.00",
                "currency_code": "EUR",
            }
        }
    ]

    pending = subscriptions.extract_pending_subscriptions(bills, "2026-05-01", "2026-05-31")

    assert pending == [
        {
            "name": "Weekly service",
            "due_date": "2026-05-01",
            "amount": "5.00 EUR",
        }
    ]


def test_extract_pending_subscriptions_keeps_out_of_grace_payments_pending():
    bills = [
        {
            "attributes": {
                "name": "Delayed service",
                "active": True,
                "pay_dates": ["2026-05-01"],
                "paid_dates": ["2026-05-09"],
                "amount_min": "15.00",
                "amount_max": "15.00",
                "currency_code": "EUR",
            }
        }
    ]

    pending = subscriptions.extract_pending_subscriptions(bills, "2026-05-01", "2026-05-31")

    assert pending == [
        {
            "name": "Delayed service",
            "due_date": "2026-05-01",
            "amount": "15.00 EUR",
        }
    ]


@pytest.mark.asyncio
async def test_show_current_period_subscriptions_replies_with_pending_bills(
    monkeypatch,
    subscription_bills,
):
    monkeypatch.setattr(
        subscriptions,
        "get_current_period_bounds",
        lambda: ("2026-05-01", "2026-05-31"),
    )
    calls = []

    def fake_get_bills_for_period(start, end):
        calls.append((start, end))
        return subscription_bills

    monkeypatch.setattr(subscriptions.client, "get_bills_for_period", fake_get_bills_for_period)

    query = FakeCallbackQuery("menu_subscriptions")
    await subscriptions.show_current_period_subscriptions(
        FakeUpdate(callback_query=query),
        FakeContext(),
    )

    assert calls == [("2026-05-01", "2026-05-31")]
    assert "Netflix *unsafe* [name]" in query.message.replies[-1]["text"]
    assert "parse_mode" not in query.message.replies[-1]


@pytest.mark.asyncio
async def test_show_current_period_subscriptions_replies_empty_state(monkeypatch):
    monkeypatch.setattr(
        subscriptions,
        "get_current_period_bounds",
        lambda: ("2026-05-01", "2026-05-31"),
    )
    monkeypatch.setattr(subscriptions.client, "get_bills_for_period", lambda start, end: [])

    query = FakeCallbackQuery("menu_subscriptions")
    await subscriptions.show_current_period_subscriptions(
        FakeUpdate(callback_query=query),
        FakeContext(),
    )

    assert query.message.replies[-1]["text"] == "✅ No tenés suscripciones pendientes en el período actual."


@pytest.mark.asyncio
async def test_show_current_period_subscriptions_handles_client_exception(monkeypatch):
    monkeypatch.setattr(
        subscriptions,
        "get_current_period_bounds",
        lambda: ("2026-05-01", "2026-05-31"),
    )

    def boom(start, end):
        raise RuntimeError("upstream failed")

    monkeypatch.setattr(subscriptions.client, "get_bills_for_period", boom)

    query = FakeCallbackQuery("menu_subscriptions")
    await subscriptions.show_current_period_subscriptions(
        FakeUpdate(callback_query=query),
        FakeContext(),
    )

    assert query.message.replies[-1]["text"] == "No se pudieron obtener las suscripciones pendientes ahora."
