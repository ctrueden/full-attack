from dataclasses import dataclass

from ..dice import Damage, Dice, Term, roll_term
from .base import Check


@dataclass(frozen=True)
class Rules:
    """A 5E weapon: crits on a natural `crit_range`-20 (e.g. 19 for a Champion)."""

    crit_range: int = 20


@dataclass(frozen=True)
class FifthEdition:
    """D&D 5E.

    A natural roll in the crit range is a critical hit, with no confirmation
    roll. A crit rolls all of the attack's damage dice twice, extra (~) dice
    like sneak attack included, but not flat bonuses. Extra attacks take no
    iterative penalty.
    """

    name: str = "5e"

    def weapon_rules(self, crit_range: int = 20) -> Rules:
        return Rules(crit_range)

    def penalty(self, step: int, rules: Rules) -> int:
        return 0

    def check(self, d20: int, rules: Rules, dice: Dice) -> Check:
        return Check(
            threat=d20 >= rules.crit_range, auto_hit=d20 == 20, auto_miss=d20 == 1
        )

    def crit_damage(
        self, terms: list[Term], normal: Damage, rules: Rules, dice: Dice
    ) -> Damage:
        return normal + Damage(tuple(roll_term(t, 1, dice) for t in terms if t.die))

    def crit_note(self, rules: Rules) -> str:
        return "dice x2"
