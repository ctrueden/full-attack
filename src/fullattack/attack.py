from dataclasses import dataclass, field, replace
from typing import Any

from .dice import Damage, Dice, Term, default_dice, parse_terms, roll_damage
from .systems import Check, GameSystem, get_system


@dataclass(frozen=True, repr=False)
class AttackOutcome:
    """A single resolved attack: to-hit roll, damage, and potential crit.

    All dice are rolled up front, so `without(...)` shows the same rolls
    with some damage terms removed.
    """

    label: str | None
    bonus: int
    d20: int
    check: Check
    damage: Damage
    crit_damage: Damage
    crit_note: str

    @property
    def to_hit(self) -> int:
        return self.d20 + self.bonus

    @property
    def threatened(self) -> bool:
        return self.check.threat

    @property
    def confirm_d20(self) -> int | None:
        return self.check.confirm_d20

    @property
    def confirm_total(self) -> int | None:
        return None if self.confirm_d20 is None else self.confirm_d20 + self.bonus

    def without(self, *labels: str) -> "AttackOutcome":
        """Return a copy omitting damage terms whose labels contain any of the given strings."""
        return replace(
            self,
            damage=self.damage.without(*labels),
            crit_damage=self.crit_damage.without(*labels),
        )

    def __str__(self) -> str:
        header = f"{self.label}: " if self.label else ""
        auto = (
            " (auto-hit)"
            if self.check.auto_hit
            else " (auto-miss)"
            if self.check.auto_miss
            else ""
        )
        lines = [f"{header}d20({self.d20}) + {self.bonus} = {self.to_hit}{auto}"]
        lines.append("Damage:")
        lines.append(str(self.damage))
        if self.threatened:
            if self.confirm_d20 is not None:
                lines.append(
                    f"Crit confirm: d20({self.confirm_d20}) + {self.bonus} = {self.confirm_total}"
                )
            lines.append(f"Critical damage ({self.crit_note}):")
            lines.append(str(self.crit_damage))
        return "\n".join(lines)

    __repr__ = __str__


def one_attack(
    bonus: int,
    damage: str | list[Term],
    *rule_args: Any,
    label: str | None = None,
    system: GameSystem | str = "pf1",
    rules: Any = None,
    crit_only: str | list[Term] = (),
    dice: Dice = default_dice,
    **rule_kwargs: Any,
) -> AttackOutcome:
    """Resolve a single attack.

    Rolls d20 + bonus to hit, normal damage, and critical damage, so the
    player can pick whichever applies. `damage` is an expression or parsed
    terms. Unless `rules` is given, remaining arguments build the system's
    weapon rules, e.g. `one_attack(20, "1d8 axe", 20, 3)` for a 3.x weapon
    threatening on 20 with a x3 multiplier. `crit_only` terms are added to
    the critical damage only, unmultiplied.

    Dice are rolled in this order: the to-hit d20, any crit confirmation
    the system needs, the normal damage, then the critical damage (always),
    then the `crit_only` terms.
    """
    system = get_system(system)
    if rules is None:
        rules = system.weapon_rules(*rule_args, **rule_kwargs)
    terms = parse_terms(damage) if isinstance(damage, str) else damage
    d20 = dice(20)
    check = system.check(d20, rules, dice)
    damage = roll_damage(terms, dice)
    if isinstance(crit_only, str):
        crit_only = parse_terms(crit_only)
    crit_damage = system.crit_damage(terms, damage, rules, dice) + roll_damage(
        list(crit_only), dice
    )
    return AttackOutcome(
        label, bonus, d20, check, damage, crit_damage, system.crit_note(rules)
    )


@dataclass(frozen=True, repr=False)
class AttackSequence:
    """A series of resolved attacks, numbered from 1.

    Narrow it down as the GM adjudicates, e.g.:

        fa.hit(1, 2, 4).crit(1).without("sneak")

    Once hits are declared, printing shows only those attacks plus a grand
    total, broken down by damage type.
    """

    outcomes: tuple[AttackOutcome, ...]
    hits: frozenset[int] | None = None
    crits: frozenset[int] = field(default_factory=frozenset)

    def hit(self, *nums: int) -> "AttackSequence":
        """Return a copy where only the given attacks (plus any crits) hit."""
        return replace(self, hits=self._check_nums(nums))

    def crit(self, *nums: int) -> "AttackSequence":
        """Return a copy where the given attacks are confirmed crits (and thus hits)."""
        return replace(self, crits=self._check_nums(nums))

    def _check_nums(self, nums: tuple[int, ...]) -> frozenset[int]:
        bad = [n for n in nums if not 1 <= n <= len(self.outcomes)]
        if bad:
            raise IndexError(
                f"No attack {', '.join(map(str, bad))}: "
                f"attacks are numbered 1 to {len(self.outcomes)}"
            )
        return frozenset(nums)

    def without(self, *labels: str) -> "AttackSequence":
        """Return a copy omitting damage terms whose labels contain any of the given strings."""
        return replace(self, outcomes=tuple(o.without(*labels) for o in self.outcomes))

    def __getitem__(self, num: int) -> AttackOutcome:
        """Get attack `num`, numbered from 1; negative numbers count from the end."""
        if num == 0 or abs(num) > len(self.outcomes):
            raise IndexError(
                f"No attack {num}: attacks are numbered 1 to {len(self.outcomes)}"
            )
        return self.outcomes[num - 1 if num > 0 else num]

    def __iter__(self):
        return iter(self.outcomes)

    def __len__(self) -> int:
        return len(self.outcomes)

    def _landed(self) -> list[tuple[int, AttackOutcome, bool]]:
        """List (number, outcome, is_crit) for each attack that hit."""
        hits = (self.hits or frozenset()) | self.crits
        return [
            (n, o, n in self.crits) for n, o in enumerate(self.outcomes, 1) if n in hits
        ]

    @property
    def damage(self) -> Damage:
        """Combined damage of all attacks that hit, merged by damage type."""
        total = Damage(())
        for _, o, is_crit in self._landed():
            total = total + (o.crit_damage if is_crit else o.damage)
        return total

    def __str__(self) -> str:
        if self.hits is None and not self.crits:
            return "\n\n".join(f"#{n} {o}" for n, o in enumerate(self.outcomes, 1))
        lines = []
        for n, o, is_crit in self._landed():
            dmg = o.crit_damage if is_crit else o.damage
            crit_note = f" (crit {o.crit_note})" if is_crit else ""
            lines.append(f"#{n} {o.label}{crit_note}: {dmg.total}")
        lines.append("=" * 20)
        lines.append(str(self.damage))
        return "\n".join(lines)

    __repr__ = __str__


def attack(
    attacks: list[tuple],
    system: GameSystem | str = "pf1",
    dice: Dice = default_dice,
) -> AttackSequence:
    """Resolve a sequence of attacks.

    Each entry is a tuple of (label, bonus, damage_expr, *rule_args), where
    rule_args build the system's weapon rules; for 3.x, these are
    [crit_range[, crit_mult]], defaulting to 20 and 2.
    """
    return AttackSequence(
        tuple(
            one_attack(bonus, expr, *rule_args, label=label, system=system, dice=dice)
            for label, bonus, expr, *rule_args in attacks
        )
    )
