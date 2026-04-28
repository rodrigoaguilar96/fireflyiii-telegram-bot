import pytest
from telegram.ext import ConversationHandler

from bot.constants import (
    SELECT_ORIGIN,
    ENTER_AMOUNT_DESC,
    SELECT_DESTINATION,
    SELECT_CATEGORY,
    SELECT_BUDGET,
    ENTER_TAGS,
    CONFIRM_EXPENSE,
)
from bot.handlers import expense, menu

from tests.conftest import (
    FakeCallbackQuery,
    FakeContext,
    FakeMessage,
    FakeResponse,
    FakeUpdate,
    button_texts,
)


def patch_expense_data(monkeypatch, all_accounts, expense_accounts, categories, budgets):
    def fake_get_accounts(account_type=None, use_cache=True):
        if account_type == "asset":
            return [a for a in all_accounts if a["attributes"]["type"] == "asset"]
        if account_type == "expense":
            return expense_accounts
        return all_accounts

    monkeypatch.setattr(expense, "get_accounts", fake_get_accounts)
    monkeypatch.setattr(expense, "get_categories", lambda: categories)
    monkeypatch.setattr(expense, "get_budgets", lambda: budgets)


@pytest.mark.asyncio
async def test_menu_to_expense_full_flow_preserves_multi_word_description(
    monkeypatch, all_accounts, expense_accounts, categories, budgets
):
    patch_expense_data(monkeypatch, all_accounts, expense_accounts, categories, budgets)
    created_payloads = []
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    context = FakeContext()

    menu_message = FakeMessage("/menu")
    await menu.start_menu(FakeUpdate(message=menu_message), context)
    assert "💸 Registrar gasto" in button_texts(menu_message.replies[-1])

    menu_query = FakeCallbackQuery("menu_expense")
    state = await expense.start_expense_button(
        FakeUpdate(callback_query=menu_query), context
    )
    assert state == SELECT_ORIGIN
    assert "tarjeta" in button_texts(menu_query.message.replies[-1])

    origin_query = FakeCallbackQuery("origin::tarjeta")
    state = await expense.select_origin(FakeUpdate(callback_query=origin_query), context)
    assert state == ENTER_AMOUNT_DESC

    amount_message = FakeMessage("12.55 supermercado pingo doce")
    state = await expense.enter_amount_description(
        FakeUpdate(message=amount_message), context
    )
    assert state == SELECT_DESTINATION
    assert context.user_data["amount"] == 12.55
    assert context.user_data["description"] == "supermercado pingo doce"

    dest_query = FakeCallbackQuery("dest::pingo doce")
    state = await expense.select_destination(FakeUpdate(callback_query=dest_query), context)
    assert state == SELECT_CATEGORY

    cat_query = FakeCallbackQuery("cat::supermercado")
    state = await expense.select_category(FakeUpdate(callback_query=cat_query), context)
    assert state == SELECT_BUDGET

    budget_query = FakeCallbackQuery("budget::comida")
    state = await expense.select_budget(FakeUpdate(callback_query=budget_query), context)
    assert state == ENTER_TAGS
    assert "⏭️ Sin tags" in button_texts(budget_query.message.replies[-1])

    tags_query = FakeCallbackQuery("tags::none")
    state = await expense.skip_tags(FakeUpdate(callback_query=tags_query), context)
    assert state == CONFIRM_EXPENSE
    assert "supermercado pingo doce" in tags_query.message.replies[-1]["text"]

    confirm_query = FakeCallbackQuery("confirm_expense")
    state = await expense.confirm_expense(FakeUpdate(callback_query=confirm_query), context)
    assert state == ConversationHandler.END

    assert len(created_payloads) == 1
    transaction = created_payloads[0]["transactions"][0]
    assert transaction["type"] == "withdrawal"
    assert transaction["amount"] == "12.55"
    assert transaction["description"] == "supermercado pingo doce"
    assert transaction["source_id"] == "asset-1"
    assert transaction["destination_id"] == "expense-1"
    assert transaction["category_id"] == "cat-1"
    assert transaction["budget_id"] == "budget-1"
    assert "date" in transaction
    assert "Gasto registrado correctamente" in confirm_query.message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_expense_button_flow_allows_optional_skips(
    monkeypatch, all_accounts, expense_accounts
):
    patch_expense_data(monkeypatch, all_accounts, expense_accounts, [], [])
    created_payloads = []
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    context = FakeContext()
    assert await expense.select_origin(
        FakeUpdate(callback_query=FakeCallbackQuery("origin::tarjeta")), context
    ) == ENTER_AMOUNT_DESC
    assert await expense.enter_amount_description(
        FakeUpdate(message=FakeMessage("8 cafe")), context
    ) == SELECT_DESTINATION
    assert await expense.select_destination(
        FakeUpdate(callback_query=FakeCallbackQuery("dest::none")), context
    ) == ENTER_TAGS
    assert await expense.skip_tags(
        FakeUpdate(callback_query=FakeCallbackQuery("tags::none")), context
    ) == CONFIRM_EXPENSE
    assert await expense.confirm_expense(
        FakeUpdate(callback_query=FakeCallbackQuery("confirm_expense")), context
    ) == ConversationHandler.END

    transaction = created_payloads[0]["transactions"][0]
    assert "destination_id" not in transaction
    assert "category_id" not in transaction
    assert "budget_id" not in transaction
    assert "tags" not in transaction


@pytest.mark.asyncio
async def test_expense_button_flow_can_create_new_destination(
    monkeypatch, all_accounts, expense_accounts, categories, budgets
):
    created_account = {"id": "expense-3", "attributes": {"name": "nuevo mercado", "type": "expense"}}
    accounts_after_create = all_accounts + [created_account]

    patch_expense_data(monkeypatch, accounts_after_create, expense_accounts, categories, budgets)
    monkeypatch.setattr(
        expense,
        "create_account",
        lambda name: FakeResponse({"data": {"attributes": {"name": name}}}),
    )
    created_payloads = []
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    context = FakeContext({"user_data": {}})
    context.user_data["amount"] = 20.0
    context.user_data["description"] = "compra"
    context.user_data["origin"] = "tarjeta"

    assert await expense.select_destination(
        FakeUpdate(callback_query=FakeCallbackQuery("dest::new")), context
    )
    assert await expense.enter_new_dest_name(
        FakeUpdate(message=FakeMessage("nuevo mercado")), context
    ) == SELECT_CATEGORY
    assert context.user_data["destination"] == "nuevo mercado"
    assert context.user_data["recent_destinations"] == ["nuevo mercado"]

    context.user_data["category"] = None
    context.user_data["budget"] = None
    context.user_data["tags"] = []
    await expense._create_expense_transaction(FakeMessage(), context)
    assert created_payloads[0]["transactions"][0]["destination_id"] == "expense-3"


@pytest.mark.asyncio
async def test_invalid_amount_stays_in_amount_step(monkeypatch):
    called = False
    monkeypatch.setattr(expense, "create_transaction", lambda payload: called)
    context = FakeContext()
    message = FakeMessage("nope")

    state = await expense.enter_amount_description(FakeUpdate(message=message), context)

    assert state == ENTER_AMOUNT_DESC
    assert "Monto inválido" in message.replies[-1]["text"]
    assert called is False


@pytest.mark.asyncio
async def test_amount_only_requires_amount_and_description_together(monkeypatch):
    context = FakeContext()

    first = FakeMessage("12.55")
    assert await expense.enter_amount_description(FakeUpdate(message=first), context) == ENTER_AMOUNT_DESC
    assert "monto y la descripción juntos" in first.replies[-1]["text"]
    assert "amount" not in context.user_data
    assert "awaiting_description" not in context.user_data


@pytest.mark.asyncio
async def test_quick_expense_validation_responses(monkeypatch, all_accounts):
    monkeypatch.setattr(expense, "get_accounts", lambda *args, **kwargs: all_accounts)

    no_args = FakeMessage("/gasto")
    await expense.quick_expense(FakeUpdate(message=no_args), FakeContext(args=[]))
    assert "Registrar gasto rápido" in no_args.replies[-1]["text"]

    few_args = FakeMessage("/gasto 12")
    await expense.quick_expense(FakeUpdate(message=few_args), FakeContext(args=["12"]))
    assert "Faltan argumentos" in few_args.replies[-1]["text"]

    bad_amount = FakeMessage("/gasto nope cafe tarjeta")
    await expense.quick_expense(
        FakeUpdate(message=bad_amount), FakeContext(args=["nope", "cafe", "tarjeta"])
    )
    assert "Monto inválido" in bad_amount.replies[-1]["text"]

    missing_origin = FakeMessage("/gasto 12 cafe inexistente")
    await expense.quick_expense(
        FakeUpdate(message=missing_origin), FakeContext(args=["12", "cafe", "inexistente"])
    )
    assert "Cuenta de origen 'inexistente' no encontrada" in missing_origin.replies[-1]["text"]


@pytest.mark.asyncio
async def test_quick_expense_creates_minimal_transaction(monkeypatch, all_accounts):
    monkeypatch.setattr(expense, "get_accounts", lambda *args, **kwargs: all_accounts)
    monkeypatch.setattr(expense, "get_categories", lambda: [])
    created_payloads = []
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    message = FakeMessage("/gasto 12 cafe tarjeta")
    context = FakeContext(args=["12", "cafe", "tarjeta"])
    await expense.quick_expense(FakeUpdate(message=message), context)

    transaction = created_payloads[0]["transactions"][0]
    assert transaction["amount"] == "12.0"
    assert transaction["description"] == "cafe"
    assert transaction["source_id"] == "asset-1"
    assert "Gasto registrado" in message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_quick_expense_applies_existing_category_and_destination(
    monkeypatch, all_accounts, categories
):
    monkeypatch.setattr(expense, "get_accounts", lambda *args, **kwargs: all_accounts)
    monkeypatch.setattr(expense, "get_categories", lambda: categories)
    created_payloads = []
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    message = FakeMessage("/gasto 12 cafe tarjeta supermercado pingo doce")
    await expense.quick_expense(
        FakeUpdate(message=message),
        FakeContext(args=["12", "cafe", "tarjeta", "supermercado", "pingo doce"]),
    )

    transaction = created_payloads[0]["transactions"][0]
    assert transaction["category_id"] == "cat-1"
    assert transaction["destination_id"] == "expense-1"


@pytest.mark.asyncio
async def test_quick_expense_documents_multi_word_description_gap(monkeypatch, all_accounts):
    monkeypatch.setattr(expense, "get_accounts", lambda *args, **kwargs: all_accounts)
    monkeypatch.setattr(expense, "get_categories", lambda: [])
    created_payloads = []
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: created_payloads.append(payload) or FakeResponse(),
    )

    message = FakeMessage("/gasto 12.55 supermercado pingo doce tarjeta")
    await expense.quick_expense(
        FakeUpdate(message=message),
        FakeContext(args=["12.55", "supermercado", "pingo", "doce", "tarjeta"]),
    )

    assert created_payloads == []
    assert "Cuenta de origen 'pingo' no encontrada" in message.replies[-1]["text"]


@pytest.mark.asyncio
async def test_quick_expense_firefly_error(monkeypatch, all_accounts):
    monkeypatch.setattr(expense, "get_accounts", lambda *args, **kwargs: all_accounts)
    monkeypatch.setattr(expense, "get_categories", lambda: [])
    monkeypatch.setattr(
        expense,
        "create_transaction",
        lambda payload: FakeResponse(status_error=RuntimeError("boom")),
    )

    message = FakeMessage("/gasto 12 cafe tarjeta")
    await expense.quick_expense(
        FakeUpdate(message=message), FakeContext(args=["12", "cafe", "tarjeta"])
    )

    assert "Error al registrar el gasto" in message.replies[-1]["text"]
