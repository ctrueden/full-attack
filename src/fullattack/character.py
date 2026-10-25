from dataclasses import dataclass, field, replace
from typing import Any

from .attack import AttackSequence, one_attack
from .dice import Dice, Term, default_dice
from .systems import GameSystem


@dataclass(frozen=True)
class Weapon:
    """A weapon's final attack bonus, base damage, and game-system rules."""

    name: str
    bonus: int
    damage: tuple[Term, ...]
    rules: Any


@dataclass(frozen=True)
class RoutineEntry:
    """One attack in a routine: which weapon, at which iterative step."""

    weapon: str
    step: int = 0
    label: str | None = None


@dataclass(frozen=True)
class Buff:
    """A named group of damage terms that can be switched on and off.

    Maps each weapon name to the terms the buff adds to it.
    """

    name: str
    damage: dict[str, tuple[Term, ...]]


@dataclass(frozen=True, repr=False)
class Character:
    """A character's weapons, attack routines, and buffs.

    Each routine and weapon can be rolled by name, either via `attack`
    or as a method, e.g. `allister.full()` or `allister.strike()`.
    """

    name: str
    system: GameSystem
    weapons: dict[str, Weapon]
    routines: dict[str, tuple[RoutineEntry, ...]]
    buffs: dict[str, Buff] = field(default_factory=dict)
    active: frozenset[str] = frozenset()

    def _toggled(self, toggles: tuple[str, ...]) -> frozenset[str]:
        """Apply toggles like "bless" (on) or "-power attack" (off) to the active buffs."""
        active = set(self.active)
        for toggle in toggles:
            on = not toggle.startswith("-")
            name = toggle.lstrip("+-").strip()
            if name not in self.buffs:
                known = ", ".join(self.buffs) or "none"
                raise ValueError(f"Unknown buff {name!r} (known: {known})")
            (active.add if on else active.discard)(name)
        return frozenset(active)

    def buff(self, *toggles: str) -> "Character":
        """Return a copy with buffs switched on ("bless") or off ("-bless")."""
        return replace(self, active=self._toggled(toggles))

    def attack(
        self, name: str, buffs: tuple[str, ...] = (), dice: Dice = default_dice
    ) -> AttackSequence:
        """Roll a routine, or a single attack with a weapon, by name.

        `buffs` toggles buffs for this roll only, as with `buff`.
        """
        if name in self.routines:
            entries = self.routines[name]
        elif name in self.weapons:
            entries = (RoutineEntry(name),)
        else:
            known = ", ".join([*self.routines, *self.weapons])
            raise ValueError(f"Unknown routine or weapon {name!r} (known: {known})")
        active = [b for b in self.buffs.values() if b.name in self._toggled(buffs)]
        outcomes = []
        for entry in entries:
            weapon = self.weapons[entry.weapon]
            terms = list(weapon.damage)
            for b in active:
                terms.extend(b.damage.get(weapon.name, ()))
            outcomes.append(
                one_attack(
                    weapon.bonus + self.system.penalty(entry.step, weapon.rules),
                    terms,
                    label=entry.label or weapon.name,
                    system=self.system,
                    rules=weapon.rules,
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
            return lambda buffs=(), dice=default_dice: self.attack(name, buffs, dice)
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def __dir__(self):
        return [*super().__dir__(), *self.routines, *self.weapons]

    def __str__(self) -> str:
        weapons = ", ".join(f"{w.name} {w.bonus:+d}" for w in self.weapons.values())
        routines = ", ".join(f"{n} ({len(r)})" for n, r in self.routines.items())
        buffs = "  ".join(
            f"[{'x' if b in self.active else ' '}] {b}" for b in self.buffs
        )
        lines = [f"{self.name} ({self.system.name})", f"Weapons:  {weapons}"]
        if routines:
            lines.append(f"Routines: {routines}")
        if buffs:
            lines.append(f"Buffs:    {buffs}")
        return "\n".join(lines)

    __repr__ = __str__
