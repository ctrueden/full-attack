from .attack import AttackOutcome, AttackSequence, attack, one_attack
from .dice import (
    Damage,
    Dice,
    Term,
    TermRoll,
    default_dice,
    parse_terms,
    roll,
    roll_damage,
    roll_term,
)

# Allister's routine and damage expressions; these move to TOML config.


def full_attack(
    att_strike: int,
    dmg_strike: str,
    att_shield: int,
    dmg_shield: str,
    dice: Dice = default_dice,
) -> AttackSequence:
    """Resolve Allister's full attack routine.

    Interleaves unarmed strikes and shield bashes at iterative penalties,
    plus the Eternal Defender slam and the extra attack from haste.
    Takes the base attack bonus and damage expression for each weapon.
    """
    attacks = [
        ("First unarmed strike", att_strike - 0, dmg_strike, 19),
        (
            "First shield bash",
            att_shield - 0,
            dmg_shield,
            19,
        ),  # shield master feat waives -2 TWF penalty
        ("Second unarmed strike", att_strike - 5, dmg_strike, 19),
        ("Second shield bash", att_shield - 5, dmg_shield, 19),
        ("Third unarmed strike", att_strike - 10, dmg_strike, 19),
        ("Third shield bash", att_shield - 10, dmg_shield, 19),
        ("Fourth unarmed strike", att_strike - 15, dmg_strike, 19),
        ("Eternal defender slam", att_shield - 5, dmg_shield, 19),  # Slam ability
        ("Haste attack", att_strike - 0, dmg_strike, 19),
    ]
    return attack(attacks, dice)


dmg_strike = "2d10 monk + 1d6 merciful + 2d6 holy + ~10d6 sneak attack + 2 good hope + 10 power attack + 2 strength + 2 martial training + 5 magic"

dmg_shield = "1d4 weapon + ~10d6 sneak attack + 2 good hope + 5 power attack + 1 strength + 5 magic"
