import textwrap
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Any

from .attack import AttackSequence, one_attack
from .dice import Dice, Term, default_dice
from .systems import GameSystem


@dataclass(frozen=True)
class Weapon:
    """A weapon's base attack bonus, base damage, and game-system rules."""

    name: str
    bonus: int
    damage: tuple[Term, ...]
    rules: Any


@dataclass(frozen=True)
class RoutineEntry:
    """One attack in a routine: which weapon, at which iterative step.

    An entry with a `buff` is only rolled while that buff is active.
    """

    weapon: str
    step: int = 0
    label: str | None = None
    buff: str | None = None


@dataclass(frozen=True)
class Buff:
    """A named set of modifiers that can be switched on and off.

    Each field maps a weapon name to what the buff adds to that weapon:
    to its attack bonus, its damage, and its damage on a critical hit only.
    A condition (like shaken) works the same way as a buff. Buffs in the
    same `group` are alternatives: switching one on switches the rest off.
    """

    name: str
    attack: dict[str, int] = field(default_factory=dict)
    damage: dict[str, tuple[Term, ...]] = field(default_factory=dict)
    crit_damage: dict[str, tuple[Term, ...]] = field(default_factory=dict)
    condition: bool = False
    group: str | None = None


@dataclass(frozen=True, repr=False)
class Character:
    """A character's weapons, attack routines, buffs, and conditions.

    Each routine and weapon can be rolled by name, either via `attack`
    or as a method, e.g. `allister.full()` or `allister.strike()`.
    """

    name: str
    system: GameSystem
    weapons: dict[str, Weapon]
    routines: dict[str, tuple[RoutineEntry, ...]]
    buffs: dict[str, Buff] = field(default_factory=dict)
    active: frozenset[str] = frozenset()

    def _toggled(self, toggles: str | Iterable[str]) -> frozenset[str]:
        """Apply toggles like "bless" (on) or "-power attack" (off) to the active buffs."""
        if isinstance(toggles, str):
            toggles = (toggles,)
        active = set(self.active)
        for toggle in toggles:
            on = not toggle.startswith("-")
            name = toggle.lstrip("+-").strip()
            if name not in self.buffs:
                known = ", ".join(self.buffs) or "none"
                raise ValueError(f"Unknown buff {name!r} (known: {known})")
            if on:
                group = self.buffs[name].group
                if group:
                    active -= {b for b in active if self.buffs[b].group == group}
                active.add(name)
            else:
                active.discard(name)
        return frozenset(active)

    def buff(self, *toggles: str) -> "Character":
        """Return a copy with buffs switched on ("bless") or off ("-bless").

        Switching a buff on switches off the others in its group.
        """
        return replace(self, active=self._toggled(toggles))

    def _bonus(self, weapon: Weapon, active: list[Buff]) -> int:
        """A weapon's attack bonus with the given buffs, before iterative penalties."""
        return weapon.bonus + sum(b.attack.get(weapon.name, 0) for b in active)

    def attack(
        self,
        name: str,
        buffs: str | Iterable[str] = (),
        bonus: int | dict[str, int] = 0,
        dice: Dice = default_dice,
    ) -> AttackSequence:
        """Roll a routine, or a single attack with a weapon, by name.

        `buffs` toggles buffs for this roll only, as with `buff`.
        `bonus` adjusts every attack's bonus for this roll only, or just
        some weapons' bonuses, e.g. `{"shield": -2}`.
        """
        if name in self.routines:
            entries = self.routines[name]
        elif name in self.weapons:
            entries = (RoutineEntry(name),)
        else:
            known = ", ".join([*self.routines, *self.weapons])
            raise ValueError(f"Unknown routine or weapon {name!r} (known: {known})")
        if isinstance(bonus, int):
            bonus = dict.fromkeys(self.weapons, bonus)
        for weapon in bonus:
            if weapon not in self.weapons:
                raise ValueError(f"Unknown weapon {weapon!r} in bonus")
        toggled = self._toggled(buffs)
        active = [b for b in self.buffs.values() if b.name in toggled]
        outcomes = []
        for entry in entries:
            if entry.buff and entry.buff not in toggled:
                continue
            weapon = self.weapons[entry.weapon]
            terms = list(weapon.damage)
            crit_terms = []
            for b in active:
                terms.extend(b.damage.get(weapon.name, ()))
                crit_terms.extend(b.crit_damage.get(weapon.name, ()))
            outcomes.append(
                one_attack(
                    self._bonus(weapon, active)
                    + bonus.get(weapon.name, 0)
                    + self.system.penalty(entry.step, weapon.rules),
                    terms,
                    label=entry.label or weapon.name,
                    system=self.system,
                    rules=weapon.rules,
                    crit_only=crit_terms,
                    dice=dice,
                )
            )
        return AttackSequence(tuple(outcomes))

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self.__dict__.get("routines", {}) or name in self.__dict__.get(
            "weapons", {}
        ):
            return lambda buffs=(), bonus=0, dice=default_dice: self.attack(
                name, buffs, bonus, dice
            )
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def __dir__(self):
        return [*super().__dir__(), *self.routines, *self.weapons]

    def __str__(self) -> str:
        active = [b for b in self.buffs.values() if b.name in self.active]
        weapons = ", ".join(
            f"{w.name} {self._bonus(w, active):+d}" for w in self.weapons.values()
        )
        routines = ", ".join(f"{n} ({len(r)})" for n, r in self.routines.items())
        inactive = [b for b in self.buffs.values() if b.name not in self.active]
        rows = [
            ("Weapons", weapons),
            ("Routines", routines),
            ("Active", ", ".join(b.name for b in active)),
            ("Buffs", ", ".join(b.name for b in inactive if not b.condition)),
            ("Conditions", ", ".join(b.name for b in inactive if b.condition)),
        ]
        lines = [f"{self.name} ({self.system.name})"]
        for heading, text in rows:
            if text:
                lines.append(
                    textwrap.fill(
                        text,
                        width=79,
                        initial_indent=f"{heading + ':':12}",
                        subsequent_indent=" " * 12,
                    )
                )
        return "\n".join(lines)

    __repr__ = __str__
