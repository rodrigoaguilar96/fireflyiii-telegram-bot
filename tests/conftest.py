import pytest


class FakeUser:
    def __init__(self, user_id=123):
        self.id = user_id


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append({"text": text, **kwargs})


class FakeCallbackQuery:
    def __init__(self, data, message=None):
        self.data = data
        self.message = message or FakeMessage()
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append({"text": text, **kwargs})


class FakeUpdate:
    def __init__(self, message=None, callback_query=None, user_id=123):
        self.message = message
        self.callback_query = callback_query
        self.effective_user = FakeUser(user_id)


class FakeContext:
    def __init__(self, args=None, user_data=None):
        self.args = args or []
        self.user_data = user_data if user_data is not None else {}


class FakeResponse:
    def __init__(self, payload=None, status_error=None, json_error=None):
        self.payload = payload or {}
        self.status_error = status_error
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


@pytest.fixture
def asset_accounts():
    return [
        {
            "id": "asset-1",
            "attributes": {
                "name": "tarjeta",
                "type": "asset",
                "current_balance": "100.00",
            },
        },
        {
            "id": "asset-2",
            "attributes": {
                "name": "efectivo",
                "type": "asset",
                "current_balance": "50.00",
            },
        },
    ]


@pytest.fixture
def expense_accounts():
    return [
        {"id": "expense-1", "attributes": {"name": "pingo doce", "type": "expense"}},
        {"id": "expense-2", "attributes": {"name": "uber", "type": "expense"}},
    ]


@pytest.fixture
def all_accounts(asset_accounts, expense_accounts):
    return asset_accounts + expense_accounts


@pytest.fixture
def categories():
    return [
        {"id": "cat-1", "attributes": {"name": "supermercado"}},
        {"id": "cat-2", "attributes": {"name": "transporte"}},
    ]


@pytest.fixture
def budgets():
    return [
        {"id": "budget-1", "attributes": {"name": "comida"}},
        {"id": "budget-2", "attributes": {"name": "mensual"}},
    ]


@pytest.fixture
def bills():
    return [
        {"id": "bill-1", "attributes": {"name": "internet hogar", "active": True}},
        {"id": "bill-2", "attributes": {"name": "gym", "active": True}},
    ]


@pytest.fixture
def mixed_bills(bills):
    return bills + [
        {"id": "bill-3", "attributes": {"name": "old streaming", "active": False}},
        {"id": "bill-4", "attributes": {"name": "", "active": True}},
        {"id": None, "attributes": {"name": "broken id", "active": True}},
        {"id": "bill-5", "attributes": "bad"},
        "invalid-entry",
    ]


@pytest.fixture
def subscription_bills():
    return [
        {
            "id": "bill-active-unpaid-string",
            "attributes": {
                "name": "Netflix *unsafe* [name]",
                "active": True,
                "pay_dates": ["2026-05-04"],
                "paid_dates": [],
                "amount_min": "10.00",
                "amount_max": "10.00",
                "currency_symbol": "€",
            },
        },
        {
            "id": "bill-active-unpaid-dict",
            "attributes": {
                "name": "Internet",
                "active": True,
                "pay_dates": [{"date": "2026-05-14T12:30:00+00:00"}],
                "paid_dates": [],
                "amount_min": "20.00",
                "amount_max": "25.50",
                "currency_code": "EUR",
            },
        },
        {
            "id": "bill-paid",
            "attributes": {
                "name": "Gym",
                "active": True,
                "pay_dates": ["2026-05-20"],
                "paid_dates": ["2026-05-20"],
                "amount_min": "30.00",
                "amount_max": "30.00",
                "currency_code": "EUR",
            },
        },
        {
            "id": "bill-paid-early",
            "attributes": {
                "name": "Rent",
                "active": True,
                "pay_dates": ["2026-05-01"],
                "paid_dates": ["2026-04-30"],
                "amount_min": "800.00",
                "amount_max": "800.00",
                "currency_code": "EUR",
            },
        },
        {
            "id": "bill-paid-late",
            "attributes": {
                "name": "Insurance",
                "active": True,
                "pay_dates": ["2026-05-10"],
                "paid_dates": ["2026-05-12"],
                "amount_min": "50.00",
                "amount_max": "50.00",
                "currency_code": "EUR",
            },
        },
        {
            "id": "bill-out-of-period",
            "attributes": {
                "name": "Cloud",
                "active": True,
                "pay_dates": ["2026-06-01"],
                "paid_dates": [],
                "amount_min": "7.00",
                "amount_max": "7.00",
                "currency_code": "EUR",
            },
        },
        {
            "id": "bill-inactive",
            "attributes": {
                "name": "Old service",
                "active": False,
                "pay_dates": ["2026-05-10"],
                "paid_dates": [],
            },
        },
        {
            "id": "bill-missing-amount",
            "attributes": {
                "name": "Unknown amount",
                "active": True,
                "pay_dates": ["2026-05-22"],
                "paid_dates": [],
            },
        },
        {"id": "broken-attributes", "attributes": "bad"},
        "not-a-bill",
    ]


@pytest.fixture
def transactions():
    return [
        {
            "attributes": {
                "transactions": [
                    {
                        "date": "2026-04-27T10:00:00+00:00",
                        "description": "supermercado pingo doce",
                        "amount": "-12.55",
                    }
                ]
            }
        }
    ]


def button_texts(reply):
    markup = reply.get("reply_markup")
    if not markup:
        return []
    return [
        button.text
        for row in markup.inline_keyboard
        for button in row
    ]
