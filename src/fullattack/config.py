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


def examples_dir() -> Path:
    """The directory of example characters bundled with full-attack."""
    return Path(__file__).parent / "examples"


def characters() -> list[str]:
    """List the names of characters in the config directory and bundled examples."""
    dirs = (config_dir(), examples_dir())
    return sorted({p.stem for d in dirs for p in d.glob("*.toml")})


def find(character: str | os.PathLike) -> Path:
    """Find the file for a character name or path, as `load` does.

    Raises FileNotFoundError, naming where it looked, if there is no such file.
    """
    path = Path(character)
    if path.suffix != ".toml":
        bare = len(path.parts) == 1
        path = path.with_name(f"{path.name}.toml")
        if bare:
            candidates = [config_dir() / path, examples_dir() / path]
            for candidate in candidates:
                if candidate.is_file():
                    return candidate
            raise FileNotFoundError(
                f"No character {character!r} in {' or '.join(map(str, candidates))}"
            )
    if not path.is_file():
        raise FileNotFoundError(f"No character file {path}")
    return path


def load(character: str | os.PathLike) -> Character:
    """Load a character by name, or from a TOML file.

    A bare name like `load("allister")` reads ~/.config/full-attack/allister.toml,
    or else the bundled example of that name. Anything ending in `.toml` or
    containing a path separator is a file path, with `.toml` added if missing,
    e.g. `load("mychars/grog")`.
    """
    path = find(character)
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


def _per_weapon(where: str, value: Any, weapons: dict) -> dict[str, Any]:
    """Expand a value for every weapon, or check a table of values per weapon."""
    if not isinstance(value, dict):
        return dict.fromkeys(weapons, value)
    for weapon in value:
        if weapon not in weapons:
            raise ValueError(f"{where}: unknown weapon {weapon!r}")
    return value


def parse_character(data: dict[str, Any], default_name: str = "?") -> Character:
    """Build a character from parsed TOML data; see the bundled examples."""
    _check_keys(
        "top level",
        data,
        {"name", "system", "weapons", "routines", "buffs", "conditions"},
    )
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

    buffs = {}
    active = set()
    for section in ("buffs", "conditions"):
        for name, table in data.get(section, {}).items():
            where = f"{section}.{name}"
            if name in buffs:
                raise ValueError(f"{where}: already defined in buffs")
            _check_keys(
                where,
                table,
                {
                    "active",
                    "attack",
                    "damage",
                    "crit_damage",
                    "advantage",
                    "disadvantage",
                    "group",
                },
            )
            attack = _per_weapon(f"{where}.attack", table.get("attack", {}), weapons)
            adv, dis = (
                _per_weapon(f"{where}.{key}", table.get(key, {}), weapons)
                for key in ("advantage", "disadvantage")
            )
            damage = {}
            for key in ("damage", "crit_damage"):
                exprs = _per_weapon(f"{where}.{key}", table.get(key, {}), weapons)
                damage[key] = {
                    w: _terms(f"{where}.{key}.{w}", e) for w, e in exprs.items()
                }
            buffs[name] = Buff(
                name,
                attack,
                damage["damage"],
                damage["crit_damage"],
                adv,
                dis,
                condition=section == "conditions",
                group=table.get("group"),
            )
            if table.get("active", False):
                active.add(name)
    groups = {}
    for name in active:
        group = buffs[name].group
        if group in groups:
            raise ValueError(
                f"buffs {groups[group]!r} and {name!r} in group {group!r} "
                "are both active"
            )
        if group:
            groups[group] = name

    routines = {}
    for name, entries in data.get("routines", {}).items():
        routine = []
        for i, entry in enumerate(entries, 1):
            where = f"routines.{name} #{i}"
            _check_keys(where, entry, {"weapon", "step", "label", "buff"})
            if entry.get("weapon") not in weapons:
                raise ValueError(f"{where}: unknown weapon {entry.get('weapon')!r}")
            if "buff" in entry and entry["buff"] not in buffs:
                raise ValueError(f"{where}: unknown buff {entry['buff']!r}")
            routine.append(RoutineEntry(**entry))
        routines[name] = tuple(routine)

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
