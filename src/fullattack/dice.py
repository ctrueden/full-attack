import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from random import randint

Dice = Callable[[int], int]
"""A die roller: takes a number of sides and returns a roll from 1 to that."""


def default_dice(sides: int) -> int:
    """Roll one die with the given number of sides, using the `random` module."""
    return randint(1, sides)


TERM_RE = re.compile(r"^([+-])?\s*(~)?(\d+)(?:d(\d+))?\s+(.+)$")

# A '+' or '-' starts a new term when a count follows it or whitespace
# surrounds it, so labels like "two-weapon" keep their hyphens.
SPLIT_RE = re.compile(r"(?=[+-]\s*~?\d)|(?<=\s)(?=[+-](?:\s|$))")


@dataclass(frozen=True)
class Term:
    """One parsed damage term: N dice of M sides, or a flat N when `die` is None.

    A negative `count` subtracts, e.g. "- 2 enfeebled" or "- 1d6 drain".
    """

    label: str
    count: int
    die: int | None = None
    extra: bool = False


def parse_terms(expr: str) -> list[Term]:
    """Parse a damage expression into a list of terms.

    The expression is a '+'/'-'-separated list of terms, each of the form
    `[~]N[dM] label`, e.g. "2d10 monk + ~10d6 sneak attack - 2 enfeebled".
    A term with `dM` rolls N dice of M sides; without it, N is a flat bonus.
    A leading `~` marks an "extra" term: damage beyond the weapon's own,
    like sneak attack or flaming, which some game systems treat specially
    on a critical hit.

    Raises ValueError if a term cannot be parsed.
    """
    terms = []
    for part in SPLIT_RE.split(expr):
        part = part.strip()
        if not part:
            continue
        match = TERM_RE.match(part)
        if not match:
            raise ValueError(f"Could not parse term: {part!r}")
        sign, extra, count, die, label = match.groups()
        count = -int(count) if sign == "-" else int(count)
        terms.append(Term(label, count, int(die) if die else None, bool(extra)))
    return terms


def _matches(label: str, patterns: tuple[str, ...]) -> bool:
    """Check whether a label contains any of the patterns, ignoring case."""
    return any(p.lower() in label.lower() for p in patterns)


@dataclass(frozen=True)
class TermRoll:
    """The rolled result of one damage term, keeping each individual die.

    Dice from a subtracted term are stored as negative rolls.
    """

    label: str
    extra: bool
    rolls: tuple[int, ...] = ()
    flat: int = 0

    @property
    def value(self) -> int:
        return sum(self.rolls) + self.flat

    def __add__(self, other: "TermRoll") -> "TermRoll":
        return replace(
            self, rolls=self.rolls + other.rolls, flat=self.flat + other.flat
        )


def roll_term(term: Term, sets: int = 1, dice: Dice = default_dice) -> TermRoll:
    """Roll one parsed term `sets` times over (e.g. 2d6 with sets=2 rolls 4d6)."""
    count = term.count * sets
    if term.die:
        sign = -1 if count < 0 else 1
        rolls = tuple(sign * dice(term.die) for _ in range(abs(count)))
        return TermRoll(term.label, term.extra, rolls=rolls)
    return TermRoll(term.label, term.extra, flat=count)


@dataclass(frozen=True, repr=False)
class Damage:
    """A set of rolled damage terms, which can be filtered without re-rolling."""

    terms: tuple[TermRoll, ...]

    @property
    def total(self) -> int:
        return sum(t.value for t in self.terms)

    def without(self, *labels: str) -> "Damage":
        """Return a copy omitting terms whose labels contain any of the given strings."""
        return Damage(tuple(t for t in self.terms if not _matches(t.label, labels)))

    def __add__(self, other: "Damage") -> "Damage":
        """Combine two damages term by term, merging terms with the same label."""
        merged = {t.label: t for t in self.terms}
        for t in other.terms:
            merged[t.label] = merged[t.label] + t if t.label in merged else t
        return Damage(tuple(merged.values()))

    def __str__(self) -> str:
        lines = [f"{t.value:3d}  {t.label}" for t in self.terms]
        lines.append("-" * 20)
        lines.append(f"{self.total:3d}  Total")
        return "\n".join(lines)

    __repr__ = __str__


def roll_damage(terms: list[Term], dice: Dice = default_dice) -> Damage:
    """Roll each parsed term once."""
    return Damage(tuple(roll_term(t, dice=dice) for t in terms))


def roll(expr: str, dice: Dice = default_dice) -> str:
    """Roll a damage expression once and return the breakdown text."""
    return str(roll_damage(parse_terms(expr), dice))
