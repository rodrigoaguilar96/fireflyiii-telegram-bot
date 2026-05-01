import pytest
from telegram.ext import ConversationHandler

from bot.constants import (
    TRANSFER_ENTER_AMOUNT,
    TRANSFER_SELECT_SOURCE,
    TRANSFER_SELECT_DESTINATION,
    TRANSFER_CONFIRM,
)
from bot.handlers import menu, transfer
from tests.conftest import (
    FakeCallbackQuery,
    FakeContext,
    FakeMessage,
    FakeResponse,
    FakeUpdate,
    button_texts,
)


def transfer_asset_accounts():
    return [
        {
            "id": "asset-1",
            "attributes": {"name": "tarjeta", "type": "asset"},
        },
        {
            "id": "asset-2",
            "attributes": {"name": "caja ahorro", "type": "asset"},
        },
        {
            "id": "asset-3",
            "attributes": {"name": "efectivo", "type": "asset"},
        },
    ]


@pytest.mark.asyncio
async def test_menu_transfer_flow_happy_path_and_exact_payload(monkeypatch):
    accounts = transfer_asset_accounts()
    monkeypatch.setattr(transfer, "get_accounts", lambda account_type=None: accounts)
    monkeypatch.setattr(transfer, "OCULTAR_CUENTAS_LOWER", ["efectivo"])
    created_payloads = []
    monkeypatch.setattr(
        transfer,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    context = FakeContext()

    menu_message = FakeMessage("/menu")
    await menu.start_menu(FakeUpdate(message=menu_message), context)
    assert "🔁 Transferir" in button_texts(menu_message.replies[-1])

    start_query = FakeCallbackQuery("menu_transfer")
    state = await transfer.start_transfer(FakeUpdate(callback_query=start_query), context)
    assert state == TRANSFER_ENTER_AMOUNT
    assert "monto" in start_query.message.replies[-1]["text"].lower()

    amount_message = FakeMessage("25.50")
    state = await transfer.enter_amount(FakeUpdate(message=amount_message), context)
    assert state == TRANSFER_SELECT_SOURCE
    assert context.user_data["amount"] == 25.5
    assert button_texts(amount_message.replies[-1]) == ["tarjeta", "caja ahorro", "❌ Cancelar"]

    source_query = FakeCallbackQuery("transfer_source::asset-1")
    state = await transfer.select_source(FakeUpdate(callback_query=source_query), context)
    assert state == TRANSFER_SELECT_DESTINATION
    assert context.user_data["source_id"] == "asset-1"
    assert context.user_data["source_name"] == "tarjeta"
    assert "caja ahorro" in button_texts(source_query.message.replies[-1])
    assert "tarjeta" not in button_texts(source_query.message.replies[-1])

    destination_query = FakeCallbackQuery("transfer_destination::asset-2")
    state = await transfer.select_destination(
        FakeUpdate(callback_query=destination_query), context
    )
    assert state == TRANSFER_CONFIRM
    assert context.user_data["destination_id"] == "asset-2"
    assert context.user_data["destination_name"] == "caja ahorro"
    assert "transferencia tarjeta-caja ahorro" in destination_query.message.replies[-1]["text"]

    confirm_query = FakeCallbackQuery("confirm_transfer")
    state = await transfer.confirm_transfer(FakeUpdate(callback_query=confirm_query), context)
    assert state == ConversationHandler.END

    assert len(created_payloads) == 1
    transaction = created_payloads[0]["transactions"][0]
    assert transaction == {
        "type": "transfer",
        "amount": "25.5",
        "description": "transferencia tarjeta-caja ahorro",
        "source_id": "asset-1",
        "destination_id": "asset-2",
        "date": transaction["date"],
    }
    assert "Transferencia registrada correctamente" in confirm_query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_enter_amount_retries_on_invalid_input_without_creating_transfer(monkeypatch):
    called = False
    monkeypatch.setattr(transfer, "create_transaction", lambda payload: called)

    message = FakeMessage("nope")
    state = await transfer.enter_amount(FakeUpdate(message=message), FakeContext())

    assert state == TRANSFER_ENTER_AMOUNT
    assert "Monto inválido" in message.replies[-1]["text"]
    assert called is False


@pytest.mark.asyncio
async def test_transfer_keyboards_use_two_columns_and_filter_hidden_accounts(monkeypatch):
    accounts = transfer_asset_accounts() + [
        {"id": "asset-4", "attributes": {"name": "billetera", "type": "asset"}},
        {"id": "asset-5", "attributes": {"name": "broker", "type": "asset"}},
    ]
    monkeypatch.setattr(transfer, "OCULTAR_CUENTAS_LOWER", ["efectivo"])

    visible = transfer._get_visible_asset_accounts(accounts)
    keyboard = transfer._build_account_keyboard(visible, "transfer_source::")

    assert [button.text for button in keyboard[0]] == ["tarjeta", "caja ahorro"]
    assert [button.text for button in keyboard[1]] == ["billetera", "broker"]
    assert all(button.text != "efectivo" for row in keyboard for button in row)

    monkeypatch.setattr(transfer, "get_accounts", lambda account_type=None: accounts)
    context = FakeContext(user_data={"amount": 10.0})
    query = FakeCallbackQuery("transfer_source::asset-1")

    state = await transfer.select_source(FakeUpdate(callback_query=query), context)

    assert state == TRANSFER_SELECT_DESTINATION
    destination_keyboard = query.message.replies[-1]["reply_markup"].inline_keyboard
    assert [button.text for button in destination_keyboard[0]] == ["caja ahorro", "billetera"]
    assert [button.text for button in destination_keyboard[1]] == ["broker"]
    assert [button.text for button in destination_keyboard[2]] == ["❌ Cancelar"]


@pytest.mark.asyncio
async def test_transfer_rejects_same_source_and_destination(monkeypatch):
    accounts = transfer_asset_accounts()
    monkeypatch.setattr(transfer, "get_accounts", lambda account_type=None: accounts)
    monkeypatch.setattr(transfer, "OCULTAR_CUENTAS_LOWER", [])

    context = FakeContext(
        user_data={
            "amount": 10.0,
            "source_id": "asset-1",
            "source_name": "tarjeta",
        }
    )
    query = FakeCallbackQuery("transfer_destination::asset-1")

    state = await transfer.select_destination(FakeUpdate(callback_query=query), context)

    assert state == TRANSFER_SELECT_DESTINATION
    assert "distinta" in query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_transfer_stops_when_source_lookup_is_invalid(monkeypatch):
    accounts = transfer_asset_accounts()
    monkeypatch.setattr(transfer, "get_accounts", lambda account_type=None: accounts)
    monkeypatch.setattr(transfer, "OCULTAR_CUENTAS_LOWER", [])

    context = FakeContext(user_data={"amount": 10.0})
    query = FakeCallbackQuery("transfer_source::missing")

    state = await transfer.select_source(FakeUpdate(callback_query=query), context)

    assert state == ConversationHandler.END
    assert "No se pudo identificar la cuenta de origen" in query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_transfer_stops_when_no_destination_accounts_remain(monkeypatch):
    accounts = transfer_asset_accounts()
    monkeypatch.setattr(transfer, "get_accounts", lambda account_type=None: accounts)
    monkeypatch.setattr(transfer, "OCULTAR_CUENTAS_LOWER", ["caja ahorro", "efectivo"])

    context = FakeContext(user_data={"amount": 10.0})
    query = FakeCallbackQuery("transfer_source::asset-1")

    state = await transfer.select_source(FakeUpdate(callback_query=query), context)

    assert state == ConversationHandler.END
    assert "No hay cuentas disponibles para seleccionar como destino" in query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_transfer_cancellation_does_not_create_transaction(monkeypatch):
    called = False

    def fake_create_transaction(payload):
        nonlocal called
        called = True
        return FakeResponse()

    monkeypatch.setattr(transfer, "create_transaction", fake_create_transaction)
    context = FakeContext(user_data={"amount": 10.0})

    state = await transfer.cancel_transfer(
        FakeUpdate(callback_query=FakeCallbackQuery("cancel_transfer")), context
    )

    assert state == ConversationHandler.END
    assert called is False


@pytest.mark.asyncio
async def test_transfer_stops_when_no_selectable_accounts_available(monkeypatch):
    monkeypatch.setattr(transfer, "get_accounts", lambda account_type=None: [])

    start_query = FakeCallbackQuery("menu_transfer")
    state = await transfer.start_transfer(FakeUpdate(callback_query=start_query), FakeContext())

    assert state == ConversationHandler.END
    assert "No hay cuentas disponibles" in start_query.message.replies[-1]["text"]
