import pytest

from fullattack import Damage, Term, TermRoll, parse_terms, roll_damage, roll_term


def test_parse_terms():
    assert parse_terms("2d10 monk + ~10d6 sneak attack + 5 magic") == [
        Term("monk", 2, 10),
        Term("sneak attack", 10, 6, precision=True),
        Term("magic", 5),
    ]


def test_parse_subtraction():
    assert parse_terms("1d8 weapon - 2 enfeebled - 1d6 drain") == [
        Term("weapon", 1, 8),
        Term("enfeebled", -2),
        Term("drain", -1, 6),
    ]


def test_parse_hyphenated_label():
    assert parse_terms("2 two-weapon fighting") == [Term("two-weapon fighting", 2)]


def test_parse_error():
    with pytest.raises(ValueError):
        parse_terms("1d8 weapon + oops")


def test_roll_term(script):
    assert roll_term(Term("fire", 2, 6), dice=script(3, 5)) == TermRoll(
        "fire", False, rolls=(3, 5)
    )
    assert roll_term(Term("magic", 5), sets=2).flat == 10


def test_roll_negative_term(script):
    roll = roll_term(Term("drain", -2, 6), dice=script(4, 1))
    assert roll.rolls == (-4, -1)
    assert roll.value == -5


def test_roll_damage_crit(script):
    terms = parse_terms("1d8 weapon + ~1d6 sneak + 3 str")
    normal, extra = roll_damage(terms, crit_mult=3, dice=script(5, 2, 7, 1))
    assert normal.total == 5 + 2 + 3
    # Two more sets of the weapon die and flat bonus; precision not multiplied.
    assert [(t.label, t.value) for t in extra.terms] == [("weapon", 8), ("str", 6)]


def test_damage_without_and_add():
    a = Damage((TermRoll("fire", False, (3,)), TermRoll("sneak", True, (4,))))
    b = Damage((TermRoll("fire", False, (6,)),))
    assert a.without("SNEAK").total == 3
    assert (a + b).terms[0] == TermRoll("fire", False, (3, 6))


def test_parse_stray_operator():
    with pytest.raises(ValueError):
        parse_terms("1d8 weapon + + 2 str")
