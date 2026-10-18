import re
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


def roll_terms(terms: list[dict], mult: int = 1) -> tuple[str, int]:
    """Roll parsed terms and tally the results.

    Each non-precision term's count is multiplied by `mult` (for critical
    hits); precision terms are rolled normally. Returns a tuple of
    (text, total), where text is a per-term breakdown followed by the total.
    """
    total = 0
    lines = []
    for term in terms:
        count = term['count'] if term['precision'] else term['count'] * mult
        if term['die']:
            value = sum(randint(1, term['die']) for _ in range(count))
        else:
            value = count
        total += value
        lines.append(f"{value:3d}  {term['label']}")
    lines.append('-' * 20)
    lines.append(f"{total:3d}  Total")
    return '\n'.join(lines), total


def roll(expr: str) -> str:
    """Roll a damage expression once and return the breakdown text."""
    text, _ = roll_terms(parse_terms(expr))
    return text


def one_attack(
    bonus: int,
    damage_expr: str,
    crit_range: int = 20,
    crit_mult: int = 2,
    label: str | None = None,
) -> str:
    """Resolve a single attack and return a text summary.

    Rolls d20 + bonus to hit and rolls normal damage. If the d20 is at or
    above `crit_range`, also rolls a crit confirmation and multiplied
    critical damage (x`crit_mult`), so the player can pick whichever applies.
    """
    lines = []
    header = f"{label + ': ' if label else ''}"
    d20 = randint(1, 20)
    lines.append(f"{header}d20({d20}) + {bonus} = {d20 + bonus}")

    terms = parse_terms(damage_expr)
    normal_text, _ = roll_terms(terms)
    lines.append("Damage:")
    lines.append(normal_text)

    if d20 >= crit_range:
        confirm_roll = randint(1, 20)
        lines.append(f"Crit confirm: d20({confirm_roll}) + {bonus} = {confirm_roll + bonus}")
        crit_text, _ = roll_terms(terms, mult=crit_mult)
        lines.append(f"Critical damage (x{crit_mult}):")
        lines.append(crit_text)

    return '\n'.join(lines)


def attack(attacks: list[tuple]) -> str:
    """Resolve a sequence of attacks and return their combined text.

    Each entry is a tuple of
    (label, bonus, damage_expr[, crit_range[, crit_mult]]),
    with crit_range defaulting to 20 and crit_mult to 2.
    """
    blocks = []
    for _, entry in enumerate(attacks, 1):
        desc, bonus, damage_expr = entry[0], entry[1], entry[2]
        crit_range = entry[3] if len(entry) > 3 else 20
        crit_mult = entry[4] if len(entry) > 4 else 2
        blocks.append(one_attack(bonus, damage_expr, crit_range, crit_mult, desc))
    return '\n\n'.join(blocks)


def full_attack(att_strike: int, dmg_strike: str, att_shield: int, dmg_shield: str) -> None:
    """Print Allister's full attack routine.

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
    print(attack(attacks))


dmg_strike = "2d10 monk + 1d6 merciful + 2d6 holy + ~10d6 sneak attack + 2 strength + 2 martial training + 5 magic"
dmg_shield = "1d4 weapon + ~10d6 sneak attack + 1 strength + 5 magic"
