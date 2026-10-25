import pytest

from fullattack import get_system, one_attack, parse_terms, roll_damage

pf1 = get_system("pf1")


def test_get_system():
    assert get_system("PF1") is pf1
    assert get_system(pf1) is pf1
    with pytest.raises(ValueError, match="Unknown game system"):
        get_system("gurps")


def test_3x_check(script):
    rules = pf1.weapon_rules(19)
    assert not pf1.check(18, rules, script()).threat
    check = pf1.check(19, rules, script(7))
    assert check.threat and check.confirm_d20 == 7 and not check.auto_hit
    assert pf1.check(20, rules, script(1)).auto_hit
    assert pf1.check(1, rules, script()).auto_miss


def test_3x_penalty():
    rules = pf1.weapon_rules()
    assert [pf1.penalty(step, rules) for step in range(4)] == [0, -5, -10, -15]


def test_3x_crit_damage(script):
    terms = parse_terms("1d8 weapon + ~1d6 flaming + 3 str + ~2 extra flat")
    normal = roll_damage(terms, script(5, 2))
    # Two more sets of the weapon die and flat bonus; extra terms not multiplied.
    crit = pf1.crit_damage(terms, normal, pf1.weapon_rules(20, 3), script(7, 1))
    assert [(t.label, t.value) for t in crit.terms] == [
        ("weapon", 13),
        ("flaming", 2),
        ("str", 9),
        ("extra flat", 2),
    ]
    assert pf1.crit_note(pf1.weapon_rules(20, 3)) == "x3"


def test_3x_attack_display(script):
    o = one_attack(5, "1d8 axe", 20, 3, label="Axe", dice=script(20, 4, 6, 1, 2))
    text = str(o)
    assert "d20(20) + 5 = 25 (auto-hit)" in text
    assert "Crit confirm: d20(4) + 5 = 9" in text
    assert "Critical damage (x3):" in text
    assert o.crit_damage.total == 9
