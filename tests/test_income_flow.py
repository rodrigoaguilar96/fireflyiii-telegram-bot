import pytest
from decimal import Decimal
from telegram.ext import ConversationHandler

from bot.constants import (
    INCOME_CONFIRM,
    INCOME_ENTER_AMOUNT_DESC,
    INCOME_SELECT_DESTINATION,
)
from bot.handlers import income, menu
from tests.conftest import (
    FakeCallbackQuery,
    FakeContext,
    FakeMessage,
    FakeResponse,
    FakeUpdate,
    button_texts,
)


def patch_income_data(monkeypatch, all_accounts):
    def fake_get_accounts(account_type=None, use_cache=True):
        if account_type == "asset":
            return [a for a in all_accounts if a["attributes"]["type"] == "asset"]
        return all_accounts

    monkeypatch.setattr(income, "get_accounts", fake_get_accounts)


@pytest.mark.asyncio
async def test_menu_to_income_flow_creates_deposit(monkeypatch, all_accounts):
    patch_income_data(monkeypatch, all_accounts)
    created_payloads = []
    monkeypatch.setattr(
        income,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    context = FakeContext()

    menu_message = FakeMessage("/menu")
    await menu.start_menu(FakeUpdate(message=menu_message), context)
    assert "💰 Registrar ingreso" in button_texts(menu_message.replies[-1])

    menu_query = FakeCallbackQuery("menu_income")
    state = await income.start_income_button(FakeUpdate(callback_query=menu_query), context)
    assert state == INCOME_SELECT_DESTINATION
    assert "tarjeta" in button_texts(menu_query.message.replies[-1])

    destination_query = FakeCallbackQuery("income_dest::tarjeta")
    state = await income.select_income_destination(
        FakeUpdate(callback_query=destination_query), context
    )
    assert state == INCOME_ENTER_AMOUNT_DESC
    assert context.user_data["destination"] == "tarjeta"

    amount_message = FakeMessage("1500 sueldo mayo")
    state = await income.enter_income_amount_description(
        FakeUpdate(message=amount_message), context
    )
    assert state == INCOME_CONFIRM
    assert context.user_data["amount"] == Decimal("1500")
    assert context.user_data["description"] == "sueldo mayo"
    assert "Resumen del ingreso" in amount_message.replies[-1]["text"]

    confirm_query = FakeCallbackQuery("confirm_income")
    state = await income.confirm_income(FakeUpdate(callback_query=confirm_query), context)
    assert state == ConversationHandler.END

    assert len(created_payloads) == 1
    transaction = created_payloads[0]["transactions"][0]
    assert transaction["type"] == "deposit"
    assert transaction["amount"] == "1500.00"
    assert transaction["description"] == "sueldo mayo"
    assert transaction["destination_id"] == "asset-1"
    assert "source_name" not in transaction
    assert "source_id" not in transaction
    assert "date" in transaction
    assert "Ingreso registrado correctamente" in confirm_query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_income_amount_requires_description(monkeypatch):
    context = FakeContext(user_data={"destination": "tarjeta"})
    message = FakeMessage("1500")

    state = await income.enter_income_amount_description(FakeUpdate(message=message), context)

    assert state == INCOME_ENTER_AMOUNT_DESC
    assert "monto y la descripción juntos" in message.replies[-1]["text"]
    assert "amount" not in context.user_data


@pytest.mark.asyncio
async def test_income_flow_can_be_cancelled_with_command():
    context = FakeContext(user_data={"destination": "tarjeta"})
    message = FakeMessage("/cancel")

    state = await income.cancel_income(FakeUpdate(message=message), context)

    assert state == ConversationHandler.END
    assert context.user_data == {}
    assert "Operación cancelada" in message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_income_missing_destination_account_does_not_create_transaction(
    monkeypatch, all_accounts
):
    patch_income_data(monkeypatch, all_accounts)
    created_payloads = []
    monkeypatch.setattr(
        income,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    context = FakeContext(
        user_data={
            "destination": "inexistente",
            "amount": Decimal("10"),
            "description": "ajuste",
        }
    )
    message = FakeMessage()

    await income._create_income_transaction(message, context)

    assert created_payloads == []
    assert "Cuenta destino no encontrada" in message.replies[-1]["text"]
