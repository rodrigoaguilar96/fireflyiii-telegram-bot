from types import SimpleNamespace

import pytest
from telegram.ext import CallbackQueryHandler

from bot import main


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
        "transfer": object(),
        "account": object(),
        "assets": object(),
    }

    monkeypatch.setattr(main, "menu_handlers", [sentinel_handlers["menu"]])
    monkeypatch.setattr(main, "expense_handlers", [sentinel_handlers["expense"]])
    monkeypatch.setattr(main, "transfer_handlers", [sentinel_handlers["transfer"]])
    monkeypatch.setattr(main, "account_handlers", [sentinel_handlers["account"]])
    monkeypatch.setattr(main, "assets_handlers", [sentinel_handlers["assets"]])

    main._register_handlers(app)

    assert app.handlers[:-1] == list(sentinel_handlers.values())
    assert isinstance(app.handlers[-1], CallbackQueryHandler)
    assert app.handlers[-1].callback is main.handle_callback


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
