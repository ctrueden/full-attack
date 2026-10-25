from dataclasses import dataclass

from ..dice import Damage, Dice, Term, roll_term
from .base import Check


@dataclass(frozen=True)
class Rules:
    """A 3.x weapon: threatens on `crit_range`-20 and deals x`crit_mult` on a crit."""

    crit_range: int = 20
    crit_mult: int = 2


@dataclass(frozen=True)
class ThirdEdition:
    """D&D 3.0/3.5 and Pathfinder 1E.

    A threat needs a confirmation roll. A crit multiplies the weapon's dice
    and flat bonuses, but never extra (~) terms such as sneak attack or
    flaming. Iterative attacks take a cumulative -5.
    """

    name: str

    def weapon_rules(self, crit_range: int = 20, crit_mult: int = 2) -> Rules:
        return Rules(crit_range, crit_mult)

    def penalty(self, step: int, rules: Rules) -> int:
        return -5 * step

    def check(self, d20: int, rules: Rules, dice: Dice) -> Check:
        threat = d20 >= rules.crit_range
        return Check(
            threat=threat,
            confirm_d20=dice(20) if threat else None,
            auto_hit=d20 == 20,
            auto_miss=d20 == 1,
        )

    def crit_damage(
        self, terms: list[Term], normal: Damage, rules: Rules, dice: Dice
    ) -> Damage:
        sets = rules.crit_mult - 1
        return normal + Damage(
            tuple(roll_term(t, sets, dice) for t in terms if not t.extra)
        )

    def crit_note(self, rules: Rules) -> str:
        return f"x{rules.crit_mult}"
