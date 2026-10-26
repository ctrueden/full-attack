from pathlib import Path

import pytest

from fullattack import get_system, load, one_attack, parse_terms, roll_damage

dnd5e = get_system("5e")
BRYNN = Path(__file__).parent.parent / "examples" / "brynn.toml"


def test_5e_check(script):
    rules = dnd5e.weapon_rules(19)
    assert not dnd5e.check(18, rules, script()).threat
    check = dnd5e.check(19, rules, script())
    assert check.threat and check.confirm_d20 is None and not check.auto_hit
    assert dnd5e.check(20, rules, script()).auto_hit
    assert dnd5e.check(1, rules, script()).auto_miss


def test_5e_penalty():
    assert dnd5e.penalty(3, dnd5e.weapon_rules()) == 0


def test_5e_crit_doubles_all_dice_but_not_flats(script):
    terms = parse_terms("1d8 rapier + ~3d6 sneak attack + 4 dex")
    normal = roll_damage(terms, script(5, 1, 2, 3))
    crit = dnd5e.crit_damage(terms, normal, dnd5e.weapon_rules(), script(8, 6, 6, 6))
    assert [(t.label, t.value) for t in crit.terms] == [
        ("rapier", 13),
        ("sneak attack", 24),
        ("dex", 4),
    ]
    assert dnd5e.crit_note(dnd5e.weapon_rules()) == "dice x2"


def test_5e_attack_display(script):
    o = one_attack(5, "1d8 rapier", system="5e", dice=script(20, 4, 7))
    text = str(o)
    assert "d20(20) + 5 = 25 (auto-hit)" in text
    assert "Crit confirm" not in text
    assert "Critical damage (dice x2):" in text
    assert o.crit_damage.total == 11


@pytest.mark.parametrize(
    "mode, d20, shown", [("adv", 15, "adv(4, 15)"), ("dis", 4, "dis(4, 15)")]
)
def test_advantage(script, mode, d20, shown):
    o = one_attack(5, "1 x", system="5e", mode=mode, dice=script(4, 15))
    assert o.d20 == d20 and o.to_hit == d20 + 5
    assert f"{shown} + 5 = {d20 + 5}" in str(o)
    with pytest.raises(ValueError, match="Unknown d20 mode"):
        one_attack(5, "1 x", mode="advantage")


def test_brynn(script):
    brynn = load(BRYNN)
    assert [o.bonus for o in brynn.attack("attack", dice=lambda s: 1)] == [9, 9, 9]
    gwm = brynn.attack("attack", buffs="great weapon master", dice=lambda s: 1)
    assert [o.bonus for o in gwm] == [4, 4, 4]
    assert gwm[1].damage.total == 2 + 5 + 10
    # Advantage and disadvantage from any source cancel out.
    assert brynn.greatsword(buffs="target prone", dice=lambda s: 1)[1].mode == "adv"
    assert brynn.greatsword(dis=True, dice=lambda s: 1)[1].mode == "dis"
    both = brynn.greatsword(buffs=["target prone", "poisoned"], dice=lambda s: 1)
    assert both[1].mode is None
    assert (
        brynn.greatsword(buffs="poisoned", adv=True, dice=lambda s: 1)[1].mode is None
    )
