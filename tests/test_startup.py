from types import SimpleNamespace

import pytest
from telegram.ext import CallbackQueryHandler

from bot.constants import (
    CONFIRM_EXPENSE,
    ENTER_AMOUNT_DESC,
    ENTER_NEW_DEST_NAME,
    ENTER_TAGS,
    INCOME_CONFIRM,
    INCOME_ENTER_AMOUNT_DESC,
    INCOME_SELECT_DESTINATION,
    SELECT_BILL,
    SELECT_BUDGET,
    SELECT_CATEGORY,
    SELECT_DESTINATION,
    SELECT_ORIGIN,
    TRANSFER_CONFIRM,
    TRANSFER_ENTER_AMOUNT,
    TRANSFER_SELECT_DESTINATION,
    TRANSFER_SELECT_SOURCE,
)
from bot import main
from bot.handlers import expense, income, menu, transfer
from bot.handlers.common import cancel_current_flow_for_expense_shortcut


class FakeApp:
    def __init__(self):
        self.handlers = []
        self.run_polling_calls = 0

    def add_handler(self, handler):
        self.handlers.append(handler)

    def run_polling(self):
        self.run_polling_calls += 1


def test_requirements_pin_python_telegram_bot_22_7():
    requirements = main.__file__.replace("bot/main.py", "requirements.txt")

    with open(requirements, encoding="utf-8") as requirements_file:
        lines = [line.strip() for line in requirements_file.readlines()]

    assert "python-telegram-bot==22.7" in lines


def test_register_handlers_adds_all_known_handlers_and_catch_all_last(monkeypatch):
    app = FakeApp()

    sentinel_handlers = {
        "menu": object(),
        "expense": object(),
        "income": object(),
        "transfer": object(),
        "account": object(),
        "assets": object(),
    }

    monkeypatch.setattr(main, "menu_handlers", [sentinel_handlers["menu"]])
    monkeypatch.setattr(main, "expense_handlers", [sentinel_handlers["expense"]])
    monkeypatch.setattr(main, "income_handlers", [sentinel_handlers["income"]])
    monkeypatch.setattr(main, "transfer_handlers", [sentinel_handlers["transfer"]])
    monkeypatch.setattr(main, "account_handlers", [sentinel_handlers["account"]])
    monkeypatch.setattr(main, "assets_handlers", [sentinel_handlers["assets"]])

    main._register_handlers(app)

    assert app.handlers[:-1] == [
        sentinel_handlers["income"],
        sentinel_handlers["transfer"],
        sentinel_handlers["expense"],
        sentinel_handlers["menu"],
        sentinel_handlers["account"],
        sentinel_handlers["assets"],
    ]
    assert isinstance(app.handlers[-1], CallbackQueryHandler)
    assert app.handlers[-1].callback is main.handle_callback


def _callbacks(handlers):
    return [handler.callback for handler in handlers]


def test_quick_menu_button_is_handled_in_all_active_conversation_states():
    expense_states = [
        SELECT_ORIGIN,
        ENTER_AMOUNT_DESC,
        SELECT_DESTINATION,
        ENTER_NEW_DEST_NAME,
        SELECT_CATEGORY,
        SELECT_BUDGET,
        SELECT_BILL,
        ENTER_TAGS,
        CONFIRM_EXPENSE,
    ]
    for state in expense_states:
        assert menu.cancel_to_menu in _callbacks(expense.expense_conv.states[state])

    income_states = [INCOME_SELECT_DESTINATION, INCOME_ENTER_AMOUNT_DESC, INCOME_CONFIRM]
    for state in income_states:
        assert menu.cancel_to_menu in _callbacks(income.income_conv.states[state])

    transfer_states = [
        TRANSFER_ENTER_AMOUNT,
        TRANSFER_SELECT_SOURCE,
        TRANSFER_SELECT_DESTINATION,
        TRANSFER_CONFIRM,
    ]
    for state in transfer_states:
        assert menu.cancel_to_menu in _callbacks(transfer.transfer_conv.states[state])


def test_quick_expense_button_is_handled_in_all_active_conversation_states():
    expense_states = [
        SELECT_ORIGIN,
        ENTER_AMOUNT_DESC,
        SELECT_DESTINATION,
        ENTER_NEW_DEST_NAME,
        SELECT_CATEGORY,
        SELECT_BUDGET,
        SELECT_BILL,
        ENTER_TAGS,
        CONFIRM_EXPENSE,
    ]
    for state in expense_states:
        assert expense.start_expense_button in _callbacks(expense.expense_conv.states[state])

    income_states = [INCOME_SELECT_DESTINATION, INCOME_ENTER_AMOUNT_DESC, INCOME_CONFIRM]
    for state in income_states:
        assert cancel_current_flow_for_expense_shortcut in _callbacks(
            income.income_conv.states[state]
        )

    transfer_states = [
        TRANSFER_ENTER_AMOUNT,
        TRANSFER_SELECT_SOURCE,
        TRANSFER_SELECT_DESTINATION,
        TRANSFER_CONFIRM,
    ]
    for state in transfer_states:
        assert cancel_current_flow_for_expense_shortcut in _callbacks(
            transfer.transfer_conv.states[state]
        )


def test_main_builds_application_and_runs_polling(monkeypatch):
    fake_app = FakeApp()
    builder_calls = []

    class FakeBuilder:
        def token(self, token):
            builder_calls.append(("token", token))
            return self

        def build(self):
            builder_calls.append(("build", None))
            return fake_app

    monkeypatch.setattr(main, "TELEGRAM_TOKEN", "test-token")
    monkeypatch.setattr(main, "ApplicationBuilder", lambda: FakeBuilder())
    monkeypatch.setattr(main, "_validate_startup", lambda: builder_calls.append(("validate", None)))
    monkeypatch.setattr(main, "_register_handlers", lambda app: builder_calls.append(("register", app)))

    main.main()

    assert builder_calls == [
        ("validate", None),
        ("token", "test-token"),
        ("build", None),
        ("register", fake_app),
    ]
    assert fake_app.run_polling_calls == 1


def test_validate_startup_exits_when_required_env_is_missing(monkeypatch):
    monkeypatch.setattr(main, "validate_env", lambda: ["TELEGRAM_BOT_TOKEN"])

    with pytest.raises(SystemExit) as exc_info:
        main._validate_startup()

    assert exc_info.value.code == 1
