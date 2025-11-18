import builtins
import os
from types import SimpleNamespace

from freya.startup import StartupMode, parse_mode, select_startup_mode


def make_config(startup_mode="normal", prompt_for_mode=True):
    return SimpleNamespace(startup_mode=startup_mode, prompt_for_mode=prompt_for_mode)


def test_parse_mode():
    assert parse_mode("diagnostic") == StartupMode.DIAGNOSTIC
    assert parse_mode("normal") == StartupMode.NORMAL
    assert parse_mode("unknown") == StartupMode.NORMAL


def test_select_startup_mode_non_interactive(monkeypatch):
    cfg = make_config(startup_mode="diagnostic", prompt_for_mode=True)
    # simulate non-interactive stdin
    monkeypatch.setattr(os, "isatty", lambda fd: False)
    assert select_startup_mode(cfg) == StartupMode.DIAGNOSTIC


def test_select_startup_mode_prompt_default(monkeypatch):
    cfg = make_config(startup_mode="normal", prompt_for_mode=True)
    # simulate interactive and an empty response
    monkeypatch.setattr(os, "isatty", lambda fd: True)
    monkeypatch.setattr(builtins, "input", lambda prompt='': "")
    assert select_startup_mode(cfg) == StartupMode.NORMAL


def test_select_startup_mode_prompt_choice(monkeypatch):
    cfg = make_config(startup_mode="normal", prompt_for_mode=True)
    monkeypatch.setattr(os, "isatty", lambda fd: True)
    monkeypatch.setattr(builtins, "input", lambda prompt='': "d")
    assert select_startup_mode(cfg) == StartupMode.DIAGNOSTIC
