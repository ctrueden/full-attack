from dataclasses import dataclass
from typing import Any, Protocol

from ..dice import Damage, Dice, Term


@dataclass(frozen=True)
class Check:
    """A game system's reading of a to-hit d20, before the GM adjudicates."""

    threat: bool = False
    confirm_d20: int | None = None
    auto_hit: bool = False
    auto_miss: bool = False


class GameSystem(Protocol):
    """The rules that differ between game systems.

    Each system defines its own weapon rules object (crit range, multiplier,
    traits, ...), which the core passes back to the other methods unexamined.
    """

    name: str

    def weapon_rules(self, *args: Any, **kwargs: Any) -> Any:
        """Build this system's rules for one weapon."""
        ...

    def penalty(self, step: int, rules: Any) -> int:
        """Return the attack bonus adjustment for iterative attack `step` (from 0)."""
        ...

    def check(self, d20: int, rules: Any, dice: Dice) -> Check:
        """Interpret a to-hit d20, rolling any crit confirmation needed."""
        ...

    def crit_damage(
        self, terms: list[Term], normal: Damage, rules: Any, dice: Dice
    ) -> Damage:
        """Return the full damage of a critical hit, given the normal damage."""
        ...

    def crit_note(self, rules: Any) -> str:
        """Describe how a crit changes damage, e.g. "x3"."""
        ...
