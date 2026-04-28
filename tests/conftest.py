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
