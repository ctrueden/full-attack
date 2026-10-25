import re
from dataclasses import dataclass, field, replace
from random import randint

TERM_RE = re.compile(r'^(~)?(\d+)(?:d(\d+))?\s+(.+)$')


def parse_terms(expr: str) -> list[dict]:
    """Parse a damage expression into a list of term dicts.

    The expression is a '+'-separated list of terms, each of the form
    `[~]N[dM] label`, e.g. "2d10 monk + ~10d6 sneak attack + 5 magic".
    A term with `dM` rolls N dice of M sides; without it, N is a flat bonus.
    A leading `~` marks a "precision" term (like sneak attack), which is
    not multiplied on a critical hit.

    Returns a list of dicts with keys 'precision', 'count', 'die', 'label'.
    Raises ValueError if a term cannot be parsed.
    """
    terms = []
    for part in expr.split('+'):
        part = part.strip()
        if not part:
            continue
        match = TERM_RE.match(part)
        if not match:
            raise ValueError(f"Could not parse term: {part!r}")
        precision, count, die, label = match.groups()
        terms.append({
            'precision': bool(precision),
            'count': int(count),
            'die': int(die) if die else None,
            'label': label,
        })
    return terms


def _matches(label: str, patterns: tuple[str, ...]) -> bool:
    """Check whether a label contains any of the patterns, ignoring case."""
    return any(p.lower() in label.lower() for p in patterns)


@dataclass(frozen=True)
class TermRoll:
    """The rolled result of one damage term, keeping each individual die."""

    label: str
    precision: bool
    rolls: tuple[int, ...] = ()
    flat: int = 0

    @property
    def value(self) -> int:
        return sum(self.rolls) + self.flat

    def __add__(self, other: 'TermRoll') -> 'TermRoll':
        return replace(self, rolls=self.rolls + other.rolls, flat=self.flat + other.flat)


def roll_term(term: dict, sets: int = 1) -> TermRoll:
    """Roll one parsed term `sets` times over (e.g. 2d6 with sets=2 rolls 4d6)."""
    count = term['count'] * sets
    if term['die']:
        rolls = tuple(randint(1, term['die']) for _ in range(count))
        return TermRoll(term['label'], term['precision'], rolls=rolls)
    return TermRoll(term['label'], term['precision'], flat=count)


@dataclass(frozen=True, repr=False)
class Damage:
    """A set of rolled damage terms, which can be filtered without re-rolling."""

    terms: tuple[TermRoll, ...]

    @property
    def total(self) -> int:
        return sum(t.value for t in self.terms)

    def without(self, *labels: str) -> 'Damage':
        """Return a copy omitting terms whose labels contain any of the given strings."""
        return Damage(tuple(t for t in self.terms if not _matches(t.label, labels)))

    def __add__(self, other: 'Damage') -> 'Damage':
        """Combine two damages term by term, merging terms with the same label."""
        merged = {t.label: t for t in self.terms}
        for t in other.terms:
            merged[t.label] = merged[t.label] + t if t.label in merged else t
        return Damage(tuple(merged.values()))

    def __str__(self) -> str:
        lines = [f"{t.value:3d}  {t.label}" for t in self.terms]
        lines.append('-' * 20)
        lines.append(f"{self.total:3d}  Total")
        return '\n'.join(lines)

    __repr__ = __str__


def roll_damage(terms: list[dict], crit_mult: int = 1) -> tuple[Damage, Damage]:
    """Roll parsed terms, returning (normal damage, extra damage on a crit).

    The crit extra holds `crit_mult - 1` additional sets of each non-precision
    term, so normal + extra is the full critical damage.
    """
    normal = Damage(tuple(roll_term(t) for t in terms))
    extra = Damage(tuple(
        roll_term(t, crit_mult - 1) for t in terms if not t['precision']
    ))
    return normal, extra


def roll(expr: str) -> str:
    """Roll a damage expression once and return the breakdown text."""
    normal, _ = roll_damage(parse_terms(expr))
    return str(normal)


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

    def without(self, *labels: str) -> 'AttackOutcome':
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
            lines.append(f"Crit confirm: d20({self.confirm_d20}) + {self.bonus} = {self.confirm_total}")
            lines.append(f"Critical damage (x{self.crit_mult}):")
            lines.append(str(self.crit_damage))
        return '\n'.join(lines)

    __repr__ = __str__


def one_attack(
    bonus: int,
    damage_expr: str,
    crit_range: int = 20,
    crit_mult: int = 2,
    label: str | None = None,
) -> AttackOutcome:
    """Resolve a single attack.

    Rolls d20 + bonus to hit and rolls damage. If the d20 is at or above
    `crit_range`, also rolls a crit confirmation and the extra critical
    damage (x`crit_mult`), so the player can pick whichever applies.
    """
    d20 = randint(1, 20)
    confirm_d20 = randint(1, 20) if d20 >= crit_range else None
    damage, crit_extra = roll_damage(parse_terms(damage_expr), crit_mult)
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

    def hit(self, *nums: int) -> 'AttackSequence':
        """Return a copy where only the given attacks (plus any crits) hit."""
        return replace(self, hits=frozenset(nums))

    def crit(self, *nums: int) -> 'AttackSequence':
        """Return a copy where the given attacks are confirmed crits (and thus hits)."""
        return replace(self, crits=frozenset(nums))

    def without(self, *labels: str) -> 'AttackSequence':
        """Return a copy omitting damage terms whose labels contain any of the given strings."""
        return replace(self, outcomes=tuple(o.without(*labels) for o in self.outcomes))

    def __getitem__(self, num: int) -> AttackOutcome:
        return self.outcomes[num - 1]

    def _landed(self) -> list[tuple[int, AttackOutcome, bool]]:
        """List (number, outcome, is_crit) for each attack that hit."""
        hits = (self.hits or frozenset()) | self.crits
        return [
            (n, o, n in self.crits)
            for n, o in enumerate(self.outcomes, 1)
            if n in hits
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
            return '\n\n'.join(f"#{n} {o}" for n, o in enumerate(self.outcomes, 1))
        lines = []
        for n, o, is_crit in self._landed():
            dmg = o.crit_damage if is_crit else o.damage
            crit_note = f" (crit x{o.crit_mult})" if is_crit else ""
            lines.append(f"#{n} {o.label}{crit_note}: {dmg.total}")
        lines.append('=' * 20)
        lines.append(str(self.damage))
        return '\n'.join(lines)

    __repr__ = __str__


def attack(attacks: list[tuple]) -> AttackSequence:
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
        outcomes.append(one_attack(bonus, damage_expr, crit_range, crit_mult, desc))
    return AttackSequence(tuple(outcomes))


def full_attack(att_strike: int, dmg_strike: str, att_shield: int, dmg_shield: str) -> AttackSequence:
    """Resolve Allister's full attack routine.

    Interleaves unarmed strikes and shield bashes at iterative penalties,
    plus the Eternal Defender slam and the extra attack from haste.
    Takes the base attack bonus and damage expression for each weapon.
    """
    attacks = [
      ("First unarmed strike",  att_strike -  0, dmg_strike, 19),
      ("First shield bash",     att_shield -  0, dmg_shield, 19), # shield master feat waives -2 TWF penalty
      ("Second unarmed strike", att_strike -  5, dmg_strike, 19),
      ("Second shield bash",    att_shield -  5, dmg_shield, 19),
      ("Third unarmed strike",  att_strike - 10, dmg_strike, 19),
      ("Third shield bash",     att_shield - 10, dmg_shield, 19),
      ("Fourth unarmed strike", att_strike - 15, dmg_strike, 19),
      ("Eternal defender slam", att_shield -  5, dmg_shield, 19), # Slam ability
      ("Haste attack",          att_strike -  0, dmg_strike, 19),
    ]
    return attack(attacks)


dmg_strike = "2d10 monk + 1d6 merciful + 2d6 holy + ~10d6 sneak attack + 2 good hope + 10 power attack + 2 strength + 2 martial training + 5 magic"

dmg_shield = "1d4 weapon + ~10d6 sneak attack + 2 good hope + 5 power attack + 1 strength + 5 magic"
