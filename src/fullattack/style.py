import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Terminal colors for output, as ANSI SGR parameters ("" for none).

    `stripe` is the background of every other attack, and `dim` the text
    color of de-emphasized output, like inactive buffs.
    """

    name: str
    stripe: str = ""
    dim: str = ""


THEMES = {
    t.name: t
    for t in (
        Theme("dark", stripe="48;5;236", dim="38;5;242"),
        Theme("light", stripe="48;5;254", dim="38;5;248"),
        Theme("plain"),
    )
}

_theme: Theme | None = None


def set_theme(theme: Theme | str | None) -> None:
    """Choose a theme by name ("dark", "light", "plain"), or None to detect one."""
    global _theme
    if isinstance(theme, str):
        if theme not in THEMES:
            raise ValueError(f"Unknown theme {theme!r} (known: {', '.join(THEMES)})")
        theme = THEMES[theme]
    _theme = theme


def theme() -> Theme:
    """The current theme: the one set with `set_theme`, or else detected.

    Detection honors $NO_COLOR and $FULL_ATTACK_THEME, uses "plain" when
    output isn't a terminal, and otherwise picks "light" or "dark" from the
    terminal's $COLORFGBG if set, defaulting to "dark".
    """
    if _theme:
        return _theme
    if os.environ.get("NO_COLOR"):
        return THEMES["plain"]
    if os.environ.get("FULL_ATTACK_THEME") in THEMES:
        return THEMES[os.environ["FULL_ATTACK_THEME"]]
    if not sys.stdout.isatty():
        return THEMES["plain"]
    background = os.environ.get("COLORFGBG", "").split(";")[-1]
    return THEMES["light" if background in ("7", "15") else "dark"]


def paint(text: str, sgr: str) -> str:
    """Wrap text in an ANSI color, if any."""
    return f"\x1b[{sgr}m{text}\x1b[0m" if sgr and text else text


def stripe(text: str, sgr: str) -> str:
    """Give each line of text a background color reaching the end of the line."""
    if not sgr:
        return text
    # Erasing to the end of the line fills it with the current background.
    return "\n".join(f"\x1b[{sgr}m{line}\x1b[K\x1b[0m" for line in text.split("\n"))
