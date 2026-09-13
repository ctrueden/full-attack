import re
import sys
from random import randint

TERM_RE = re.compile(r'^(~)?(\d+)(?:d(\d+))?\s+(.+)$')


def parse_terms(expr):
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


def roll_terms(terms, mult=1):
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


def roll(expr):
    text, _ = roll_terms(parse_terms(expr))
    return text


def one_attack(bonus, damage_expr, crit_range=20, crit_mult=2, label=None):
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


def attack(attacks):
    blocks = []
    for _, entry in enumerate(attacks, 1):
        desc, bonus, damage_expr = entry[0], entry[1], entry[2]
        crit_range = entry[3] if len(entry) > 3 else 20
        crit_mult = entry[4] if len(entry) > 4 else 2
        blocks.append(one_attack(bonus, damage_expr, crit_range, crit_mult, desc))
    return '\n\n'.join(blocks)


def full_attack(att_strike: int, dmg_strike: str, att_shield: int, dmg_shield: str):
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
