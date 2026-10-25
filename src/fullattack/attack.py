from dataclasses import dataclass, field, replace

from .dice import Damage, Dice, default_dice, parse_terms, roll_damage


@dataclass(frozen=True, repr=False)
class AttackOutcome:
    """A single resolved attack: to-hit roll, damage, and potential crit.

    All dice are rolled up front, so `without(...)` shows the same rolls
    with some damage terms removed.
    """

    label: str | None
    bonus: int
    d20: int
    confirm_d20: int | None
    crit_mult: int
    damage: Damage
    crit_extra: Damage

    @property
    def to_hit(self) -> int:
        return self.d20 + self.bonus

    @property
    def threatened(self) -> bool:
        return self.confirm_d20 is not None

    @property
    def confirm_total(self) -> int | None:
        return None if self.confirm_d20 is None else self.confirm_d20 + self.bonus

    @property
    def crit_damage(self) -> Damage:
        return self.damage + self.crit_extra

    def without(self, *labels: str) -> "AttackOutcome":
        """Return a copy omitting damage terms whose labels contain any of the given strings."""
        return replace(
            self,
            damage=self.damage.without(*labels),
            crit_extra=self.crit_extra.without(*labels),
        )

    def __str__(self) -> str:
        header = f"{self.label}: " if self.label else ""
        lines = [f"{header}d20({self.d20}) + {self.bonus} = {self.to_hit}"]
        lines.append("Damage:")
        lines.append(str(self.damage))
        if self.threatened:
            lines.append(
                f"Crit confirm: d20({self.confirm_d20}) + {self.bonus} = {self.confirm_total}"
            )
            lines.append(f"Critical damage (x{self.crit_mult}):")
            lines.append(str(self.crit_damage))
        return "\n".join(lines)

    __repr__ = __str__


def one_attack(
    bonus: int,
    damage_expr: str,
    crit_range: int = 20,
    crit_mult: int = 2,
    label: str | None = None,
    dice: Dice = default_dice,
) -> AttackOutcome:
    """Resolve a single attack.

    Rolls d20 + bonus to hit and rolls damage. If the d20 is at or above
    `crit_range`, also rolls a crit confirmation and the extra critical
    damage (x`crit_mult`), so the player can pick whichever applies.

    Dice are rolled in this order: the to-hit d20, the confirm d20 (on a
    threat), the normal damage, then the extra critical damage (always).
    """
    d20 = dice(20)
    confirm_d20 = dice(20) if d20 >= crit_range else None
    damage, crit_extra = roll_damage(parse_terms(damage_expr), crit_mult, dice)
    return AttackOutcome(label, bonus, d20, confirm_d20, crit_mult, damage, crit_extra)


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
        return replace(self, hits=frozenset(nums))

    def crit(self, *nums: int) -> "AttackSequence":
        """Return a copy where the given attacks are confirmed crits (and thus hits)."""
        return replace(self, crits=frozenset(nums))

    def without(self, *labels: str) -> "AttackSequence":
        """Return a copy omitting damage terms whose labels contain any of the given strings."""
        return replace(self, outcomes=tuple(o.without(*labels) for o in self.outcomes))

    def __getitem__(self, num: int) -> AttackOutcome:
        return self.outcomes[num - 1]

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
            crit_note = f" (crit x{o.crit_mult})" if is_crit else ""
            lines.append(f"#{n} {o.label}{crit_note}: {dmg.total}")
        lines.append("=" * 20)
        lines.append(str(self.damage))
        return "\n".join(lines)

    __repr__ = __str__


def attack(attacks: list[tuple], dice: Dice = default_dice) -> AttackSequence:
    """Resolve a sequence of attacks.

    Each entry is a tuple of
    (label, bonus, damage_expr[, crit_range[, crit_mult]]),
    with crit_range defaulting to 20 and crit_mult to 2.
    """
    outcomes = []
    for entry in attacks:
        desc, bonus, damage_expr = entry[0], entry[1], entry[2]
        crit_range = entry[3] if len(entry) > 3 else 20
        crit_mult = entry[4] if len(entry) > 4 else 2
        outcomes.append(
            one_attack(bonus, damage_expr, crit_range, crit_mult, desc, dice)
        )
    return AttackSequence(tuple(outcomes))
