import sys
from unittest.mock import Mock

import pytest

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import User, db
from src.expenis.core.service.personal_greeting_service import get_active_greeting, inspect_greeting
from src.expenis.server.greeting_cli import greeting_main, greeting_parser, run_greeting_command


async def run(*argv):
    await run_greeting_command(greeting_parser().parse_args(argv))


@pytest.mark.asyncio
async def test_individual_commands_and_errors(capsys):
    async with db:
        user = await db.run(lambda: User.create(username="alice"))
        await run("show", "--username", "alice")
        assert "No greeting" in capsys.readouterr().out
        await run("set", "--user-id", str(user.id), "--text", "🎉\nПоздравляю!")
        await run("show", "--all")
        output = capsys.readouterr().out
        assert "🎉\nПоздравляю!" in output and "Active: True" in output
        await run("delete", "--username", "alice")
        await run("delete", "--username", "alice")
        assert await inspect_greeting(user.id) is None
        with pytest.raises(NotFoundException):
            await run("set", "--username", "missing", "--text", "Hello")
        with pytest.raises(ValueError):
            await run("set", "--all", "--text", " ")


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["no", "", EOFError(), OSError()])
async def test_bulk_cancel_or_unavailable_confirmation(answer, monkeypatch, capsys):
    async with db:
        user = await db.run(lambda: User.create(username="alice"))
        def confirm(prompt):
            assert not db.in_transaction()
            if isinstance(answer, Exception):
                raise answer
            return answer
        monkeypatch.setattr("builtins.input", confirm)
        await run("set", "--all", "--text", "All")
        assert await inspect_greeting(user.id) is None
        output = capsys.readouterr().out
        assert "Recipients: 1" in output and "Cancelled" in output


@pytest.mark.asyncio
async def test_bulk_snapshot_confirmation_and_deletion(monkeypatch, capsys):
    async with db:
        first = await db.run(lambda: User.create(username="first"))
        # Selection must not be repeated after the operator confirms.
        from src.expenis.server import greeting_cli
        original = greeting_cli.select_greeting_recipients
        async def select(**kwargs):
            selected = await original(**kwargs)
            await db.run(lambda: User.create(username="late"))
            return selected
        monkeypatch.setattr(greeting_cli, "select_greeting_recipients", select)
        monkeypatch.setattr("builtins.input", lambda prompt: "yes")
        await run("set", "--all", "--text", "All")
        assert (await get_active_greeting(first.id)).text == "All"
        late = await db.run(lambda: User.get(User.username == "late"))
        assert await inspect_greeting(late.id) is None
        assert "Recipients: 1" in capsys.readouterr().out
        monkeypatch.setattr(greeting_cli, "select_greeting_recipients", original)
        await run("delete", "--all")
        assert await inspect_greeting(first.id) is None
        assert "Recipients: 2" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_empty_bulk_does_not_prompt(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", Mock(side_effect=AssertionError("Unexpected confirmation")))
    async with db:
        await run("set", "--all", "--text", "Empty")
    assert "Recipients: 0" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [
    ["set", "--all", "--username", "alice", "--text", "Hello"],
    ["show"],
    ["set", "--all", "--text", "Hello", "--expires-on", "2026-02-30"],
    ["set", "--all", "--text", "Hello", "--expires-on", "20261231"],
])
def test_parser_rejects_invalid_arguments(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        greeting_parser().parse_args(argv)
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_command_errors_have_nonzero_exit(monkeypatch, capsys):
    from src.expenis.server import greeting_cli
    async def fail(args):
        raise NotFoundException("User not found")
    monkeypatch.setattr(greeting_cli, "_run", fail)
    with pytest.raises(SystemExit) as exc:
        greeting_main(["show", "--username", "missing"])
    assert exc.value.code == 1
    assert "User not found" in capsys.readouterr().err


def test_main_dispatch_preserves_server_and_token(monkeypatch):
    from src.expenis.server import __main__ as entry
    from src.expenis.server import greeting_cli
    command = Mock()
    monkeypatch.setattr(greeting_cli, "greeting_main", command)
    monkeypatch.setattr(sys, "argv", ["server", "greeting", "show", "--all"])
    entry.main()
    command.assert_called_once_with(["show", "--all"])
    uvicorn = Mock()
    monkeypatch.setattr(entry.uvicorn, "run", uvicorn)
    monkeypatch.setattr(entry, "setup_logging", lambda: {})
    monkeypatch.setattr(sys, "argv", ["server"])
    entry.main()
    uvicorn.assert_called_once()
    token_calls = []
    async def token(username, days):
        token_calls.append((username, days))
    monkeypatch.setattr(entry, "_generate_token", token)
    monkeypatch.setattr(sys, "argv", ["server", "token", "--username", "alice", "--days", "7"])
    entry.main()
    assert token_calls == [("alice", 7)]
