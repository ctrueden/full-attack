import pytest

from fullattack import attack, set_theme, theme


def test_stripes_alternate_outcomes(script):
    set_theme("dark")
    fa = attack(
        [("A", 1, "1 a"), ("B", 2, "1 b"), ("C", 3, "1 c")], dice=script(5, 6, 7)
    )
    a, b, c = str(fa).split("\n\n")
    assert "\x1b[" not in a and "\x1b[" not in c
    assert all(line.startswith("\x1b[48;5;236m") for line in b.split("\n"))
    summary = str(fa.hit(1, 2, 3)).split("\n")
    assert "\x1b[" not in summary[0] and summary[1].startswith("\x1b[48;5;236m")


def test_theme_detection(monkeypatch):
    set_theme(None)
    monkeypatch.setenv("FULL_ATTACK_THEME", "light")
    assert theme().name == "light"
    monkeypatch.setenv("NO_COLOR", "1")
    assert theme().name == "plain"
    with pytest.raises(ValueError, match="Unknown theme"):
        set_theme("neon")
