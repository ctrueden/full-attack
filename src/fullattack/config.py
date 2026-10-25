import os
import tomllib
from pathlib import Path
from typing import Any

from .character import Buff, Character, RoutineEntry, Weapon
from .dice import Term, parse_terms
from .systems import get_system


def config_dir() -> Path:
    """The directory searched for characters by name: ~/.config/full-attack."""
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "full-attack"


def characters() -> list[str]:
    """List the names of characters in the config directory."""
    return sorted(p.stem for p in config_dir().glob("*.toml"))


def load(character: str | os.PathLike) -> Character:
    """Load a character by name from the config directory, or from a TOML file.

    Anything ending in `.toml` or containing a path separator is a file path;
    otherwise, e.g. `load("allister")` reads ~/.config/full-attack/allister.toml.
    """
    path = Path(character)
    if path.suffix != ".toml" and len(path.parts) == 1:
        path = config_dir() / f"{character}.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)
    try:
        return parse_character(data, default_name=path.stem.capitalize())
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from None


def _terms(where: str, expr: str) -> tuple[Term, ...]:
    try:
        return tuple(parse_terms(expr))
    except ValueError as e:
        raise ValueError(f"{where}: {e}") from None


def _check_keys(where: str, table: dict, allowed: set[str]) -> None:
    unknown = set(table) - allowed
    if unknown:
        raise ValueError(f"{where}: unknown keys {', '.join(sorted(unknown))}")


def parse_character(data: dict[str, Any], default_name: str = "?") -> Character:
    """Build a character from parsed TOML data; see examples/allister.toml."""
    _check_keys("top level", data, {"name", "system", "weapons", "routines", "buffs"})
    if "system" not in data:
        raise ValueError('missing game system, e.g. system = "pf1"')
    system = get_system(data["system"])

    weapons = {}
    for name, table in data.get("weapons", {}).items():
        where = f"weapons.{name}"
        rule_args = {k: v for k, v in table.items() if k not in ("bonus", "damage")}
        try:
            rules = system.weapon_rules(**rule_args)
        except TypeError:
            raise ValueError(
                f"{where}: invalid {system.name} weapon rules {rule_args}"
            ) from None
        weapons[name] = Weapon(
            name,
            table.get("bonus", 0),
            _terms(f"{where}.damage", table.get("damage", "")),
            rules,
        )

    routines = {}
    for name, entries in data.get("routines", {}).items():
        routine = []
        for i, entry in enumerate(entries, 1):
            where = f"routines.{name} #{i}"
            _check_keys(where, entry, {"weapon", "step", "label"})
            if entry.get("weapon") not in weapons:
                raise ValueError(f"{where}: unknown weapon {entry.get('weapon')!r}")
            routine.append(RoutineEntry(**entry))
        routines[name] = tuple(routine)

    buffs = {}
    active = set()
    for name, table in data.get("buffs", {}).items():
        where = f"buffs.{name}"
        _check_keys(where, table, {"damage", "active"})
        damage = table.get("damage", {})
        if isinstance(damage, str):
            damage = dict.fromkeys(weapons, damage)
        for weapon in damage:
            if weapon not in weapons:
                raise ValueError(f"{where}: unknown weapon {weapon!r}")
        buffs[name] = Buff(
            name,
            {w: _terms(f"{where}.damage.{w}", e) for w, e in damage.items()},
        )
        if table.get("active", False):
            active.add(name)

    clash = set(routines) & set(weapons)
    if clash:
        raise ValueError(f"names used for both routines and weapons: {clash}")

    return Character(
        data.get("name", default_name),
        system,
        weapons,
        routines,
        buffs,
        frozenset(active),
    )
