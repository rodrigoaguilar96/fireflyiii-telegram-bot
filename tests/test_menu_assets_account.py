import pytest

from bot.constants import EXPENSE_BUTTON_TEXT, MENU_BUTTON_TEXT
from bot.handlers import account, assets, common, menu, subscriptions
from tests.conftest import FakeCallbackQuery, FakeContext, FakeMessage, FakeUpdate, button_texts


@pytest.mark.asyncio
async def test_start_and_menu_show_main_keyboard():
    message = FakeMessage("/start")

    await menu.start_menu(FakeUpdate(message=message), FakeContext())

    quick_reply = message.replies[0]
    quick_buttons = [
        getattr(button, "text", button)
        for row in quick_reply["reply_markup"].keyboard
        for button in row
    ]
    assert quick_buttons == [MENU_BUTTON_TEXT, EXPENSE_BUTTON_TEXT]

    buttons = button_texts(message.replies[-1])
    assert "💸 Registrar gasto" in buttons
    assert "🔁 Transferir" in buttons
    assert "💼 Ver cuentas" in buttons
    assert "📊 Ver cuenta + movimientos" in buttons
    assert "🧾 Suscripciones pendientes" in buttons
    assert "📋 Ver comandos" in buttons


@pytest.mark.asyncio
async def test_menu_callbacks_route_to_assets_and_commands(monkeypatch, asset_accounts):
    monkeypatch.setattr(assets, "get_accounts", lambda account_type=None: asset_accounts)

    assets_query = FakeCallbackQuery("menu_assets")
    await menu.handle_menu_selection(FakeUpdate(callback_query=assets_query), FakeContext())
    assert "Tus cuentas de activo" in assets_query.message.replies[-1]["text"]

    commands_query = FakeCallbackQuery("menu_commands")
    await menu.handle_menu_selection(FakeUpdate(callback_query=commands_query), FakeContext())
    assert "Comandos disponibles" in commands_query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_menu_subscriptions_callback_routes_without_flow_side_effects(monkeypatch):
    calls = []

    async def fake_show_current_period_subscriptions(update, context):
        calls.append((update, context))
        await update.callback_query.message.reply_text("subscriptions ok")

    monkeypatch.setattr(
        subscriptions,
        "show_current_period_subscriptions",
        fake_show_current_period_subscriptions,
    )

    query = FakeCallbackQuery("menu_subscriptions")
    context = FakeContext(user_data={"existing": "value"})

    await menu.handle_menu_selection(FakeUpdate(callback_query=query), context)

    assert query.answers == [{"text": None}]
    assert query.message.replies[-1]["text"] == "subscriptions ok"
    assert calls[0][1] is context
    assert context.user_data == {"existing": "value"}


@pytest.mark.asyncio
async def test_assets_lists_visible_accounts_and_hides_configured(monkeypatch, asset_accounts):
    monkeypatch.setattr(assets, "get_accounts", lambda account_type=None: asset_accounts)
    monkeypatch.setattr(assets, "OCULTAR_CUENTAS_LOWER", ["efectivo"])

    message = FakeMessage("/assets")
    await assets.list_assets(FakeUpdate(message=message), FakeContext())

    buttons = button_texts(message.replies[-1])
    assert "tarjeta" in buttons
    assert "efectivo" not in buttons


@pytest.mark.asyncio
async def test_assets_handles_empty_and_errors(monkeypatch):
    monkeypatch.setattr(assets, "get_accounts", lambda account_type=None: [])
    empty = FakeMessage("/assets")
    await assets.list_assets(FakeUpdate(message=empty), FakeContext())
    assert "No hay cuentas visibles" in empty.replies[-1]["text"]

    def boom(account_type=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(assets, "get_accounts", boom)
    error = FakeMessage("/assets")
    await assets.list_assets(FakeUpdate(message=error), FakeContext())
    assert "No se pudo obtener" in error.replies[-1]["text"]


@pytest.mark.asyncio
async def test_show_account_validation_and_success(monkeypatch):
    no_name = FakeMessage("/cuenta")
    await account.show_account(FakeUpdate(message=no_name), FakeContext())
    assert "Uso: /cuenta" in no_name.replies[-1]["text"]

    bad_count = FakeMessage("/cuenta tarjeta nope")
    await account.show_account(FakeUpdate(message=bad_count), FakeContext())
    assert "Cantidad de movimientos inválida" in bad_count.replies[-1]["text"]

    async def found_display(name, limit=3):
        return "ok"

    monkeypatch.setattr(account, "format_account_display", found_display)
    found = FakeMessage("/cuenta tarjeta 2")
    await account.show_account(FakeUpdate(message=found), FakeContext())
    assert found.replies[-1]["text"] == "ok"

    async def missing_display(name, limit=3):
        return None

    monkeypatch.setattr(account, "format_account_display", missing_display)
    missing = FakeMessage("/cuenta missing")
    await account.show_account(FakeUpdate(message=missing), FakeContext())
    assert "Cuenta no encontrada" in missing.replies[-1]["text"]


@pytest.mark.asyncio
async def test_format_account_display(monkeypatch, all_accounts, transactions):
    monkeypatch.setattr(common, "get_accounts", lambda: all_accounts)
    monkeypatch.setattr(common, "safe_get", lambda endpoint, params=None: transactions)

    result = await common.format_account_display("tarjeta", limit=3)

    assert "📊 *tarjeta*" in result
    assert "Balance: 100.00" in result
    assert "supermercado pingo doce" in result


def test_split_message_prefers_newline():
    text = "a\n" + ("b" * 10)
    chunks = account._split_message(text, max_length=5)
    assert chunks == ["a", "bbbbb", "bbbbb"]


@pytest.mark.asyncio
async def test_account_callback_and_catch_all(monkeypatch):
    async def callback_display(name, limit=3):
        return "account ok"

    monkeypatch.setattr(account, "format_account_display", callback_display)
    query = FakeCallbackQuery("cuenta::tarjeta")
    await account.handle_callback(FakeUpdate(callback_query=query), FakeContext())
    assert query.message.replies[-1]["text"] == "account ok"

    reserved = FakeCallbackQuery("origin::tarjeta")
    await account.handle_callback(FakeUpdate(callback_query=reserved), FakeContext())
    assert reserved.message.replies == []


@pytest.mark.asyncio
async def test_account_callback_ignores_transfer_callbacks(monkeypatch):
    called = False

    async def callback_display(name, limit=3):
        nonlocal called
        called = True
        return "account ok"

    monkeypatch.setattr(account, "format_account_display", callback_display)

    for data in (
        "transfer_source::asset-1",
        "transfer_destination::asset-2",
        "confirm_transfer",
        "cancel_transfer",
    ):
        query = FakeCallbackQuery(data)
        await account.handle_callback(FakeUpdate(callback_query=query), FakeContext())
        assert query.message.replies == []

    assert called is False
