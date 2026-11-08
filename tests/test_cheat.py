import sys

import pytest

import fullattack
from fullattack import cheat, load, parse_character


def run_examples(output: str, namespace: dict) -> list[str]:
    """Execute every example of a printed cheat sheet, in order."""
    namespace.update(vars(fullattack))
    examples = [
        line.split("  # ")[0].strip()
        for line in output.splitlines()
        if line.startswith("  ")
    ]
    for example in examples:
        exec(example, namespace)  # noqa: S102
    return examples


@pytest.fixture
def session(monkeypatch):
    """Define variables as though typed at the interactive prompt."""

    def define(name, value):
        monkeypatch.setattr(sys.modules["__main__"], name, value, raising=False)

    return define


@pytest.mark.parametrize("name", ["allister", "brynn"])
def test_examples_run(session, capsys, name):
    character = load(name)
    session(name, character)
    cheat()
    examples = run_examples(capsys.readouterr().out, {name: character})
    assert any(e.startswith(f"fa = {name}.") for e in examples)
    assert any(".without(" in e for e in examples)


def test_uses_character_names(session, capsys):
    session("al", load("allister"))
    cheat()
    output = capsys.readouterr().out
    assert output.startswith("Cheat sheet: al is Allister (pf1)")
    assert "fa = al.full()" in output
    assert 'al += "smite"' in output
    assert 'al -= "haste"' in output
    assert 'al += "prone"' in output


def test_without_a_session(capsys):
    cheat()
    output = capsys.readouterr().out
    assert 'allister = load("allister")' in output
    run_examples(output, {})


def test_character_outside_session(capsys):
    cheat(load("brynn"))
    output = capsys.readouterr().out
    assert output.startswith("Cheat sheet: pc is Brynn (5e)")
    assert 'fa = pc.attack("attack")' in output


def test_lists_other_characters(session, capsys):
    session("allister", load("allister"))
    session("brynn", load("brynn"))
    cheat()
    assert "cheat(brynn)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"weapons": {"axe": {}}},
        {"weapons": {"axe": {"damage": "1 cut"}}},
        {
            "weapons": {"axe": {}},
            "routines": {"full": [{"weapon": "axe"}, {"weapon": "axe"}]},
        },
        {"weapons": {"great axe": {}, "class": {}, "name": {}}},
        {
            "weapons": {"axe": {}},
            "routines": {"rage": [{"weapon": "axe", "buff": "rage"}]},
            "buffs": {"rage": {}},
        },
    ],
)
def test_sparse_characters(session, capsys, data):
    character = parse_character({"system": "pf1", **data})
    session("grog", character)
    cheat()
    run_examples(capsys.readouterr().out, {"grog": character})
