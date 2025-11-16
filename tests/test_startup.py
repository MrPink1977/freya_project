import os
import builtins
from types import SimpleNamespace

import freya.main as main


def make_config(startup_mode="normal", prompt_for_mode=True):
    return SimpleNamespace(startup_mode=startup_mode, prompt_for_mode=prompt_for_mode)


def test_parse_mode():
    assert main._parse_mode("diagnostic") == main.StartupMode.DIAGNOSTIC
    assert main._parse_mode("normal") == main.StartupMode.NORMAL
    assert main._parse_mode("unknown") == main.StartupMode.NORMAL


def test_select_startup_mode_non_interactive(monkeypatch):
    cfg = make_config(startup_mode="diagnostic", prompt_for_mode=True)
    # simulate non-interactive stdin
    monkeypatch.setattr(os, "isatty", lambda fd: False)
    assert main._select_startup_mode(cfg) == main.StartupMode.DIAGNOSTIC


def test_select_startup_mode_prompt_default(monkeypatch):
    cfg = make_config(startup_mode="normal", prompt_for_mode=True)
    # simulate interactive and an empty response
    monkeypatch.setattr(os, "isatty", lambda fd: True)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    assert main._select_startup_mode(cfg) == main.StartupMode.NORMAL


def test_select_startup_mode_prompt_choice(monkeypatch):
    cfg = make_config(startup_mode="normal", prompt_for_mode=True)
    monkeypatch.setattr(os, "isatty", lambda fd: True)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "d")
    assert main._select_startup_mode(cfg) == main.StartupMode.DIAGNOSTIC
