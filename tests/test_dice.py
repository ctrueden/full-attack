import pytest

from fullattack import (
    Damage,
    Term,
    TermRoll,
    parse_terms,
    roll,
    roll_damage,
    roll_term,
)


def test_parse_terms():
    assert parse_terms("2d10 monk + ~10d6 sneak attack + 5 magic") == [
        Term("monk", 2, 10),
        Term("sneak attack", 10, 6, extra=True),
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


@pytest.mark.parametrize(
    "expr, labeled",
    [
        ("1d20", "1d20 die"),
        ("2d20", "2d20 dice"),
        ("1d20 + 5", "1d20 die + 5 bonus"),
        ("1d20 - 3", "1d20 die - 3 penalty"),
        ("1d20-3", "1d20 die - 3 penalty"),
        ("- 1d4", "- 1d4 die"),
        ("2d6 fire + 5", "2d6 fire + 5 bonus"),
    ],
)
def test_default_labels(expr, labeled):
    assert parse_terms(expr, default_labels=True) == parse_terms(labeled)


def test_labels_required_by_default():
    with pytest.raises(ValueError, match=r"Could not parse term: '\+ 5'"):
        parse_terms("1d8 weapon + 5")


def test_default_labels_still_reject_garbage():
    with pytest.raises(ValueError):
        parse_terms("1d20 + oops", default_labels=True)
    with pytest.raises(ValueError):
        parse_terms("2d6fire", default_labels=True)


def test_roll_without_labels(script):
    assert roll("1d20 + 5", script(12)).splitlines() == [
        " 12  die",
        "  5  bonus",
        "-" * 20,
        " 17  Total",
    ]


def test_roll_defaults_to_d20(script):
    assert roll(dice=script(20)) == roll("1d20", script(20))


@pytest.mark.parametrize(
    "modifier, expr",
    [(5, "1d20 + 5"), (-3, "1d20 - 3"), (0, "1d20 + 0")],
)
def test_roll_integer_modifies_d20(script, modifier, expr):
    assert roll(modifier, script(12)) == roll(expr, script(12))


def test_roll_term(script):
    assert roll_term(Term("fire", 2, 6), dice=script(3, 5)) == TermRoll(
        "fire", False, rolls=(3, 5)
    )
    assert roll_term(Term("magic", 5), sets=2).flat == 10


def test_roll_negative_term(script):
    roll = roll_term(Term("drain", -2, 6), dice=script(4, 1))
    assert roll.rolls == (-4, -1)
    assert roll.value == -5


def test_roll_damage(script):
    damage = roll_damage(parse_terms("2d6 fire - 1 weak"), script(3, 4))
    assert damage.total == 6


def test_damage_without_and_add():
    a = Damage((TermRoll("fire", False, (3,)), TermRoll("sneak", True, (4,))))
    b = Damage((TermRoll("fire", False, (6,)),))
    assert a.without("SNEAK").total == 3
    assert (a + b).terms[0] == TermRoll("fire", False, (3, 6))


def test_parse_stray_operator():
    with pytest.raises(ValueError):
        parse_terms("1d8 weapon + + 2 str")
