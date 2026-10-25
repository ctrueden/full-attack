import pytest

from fullattack import attack, one_attack


def test_one_attack_no_threat(script):
    # d20, normal 1d8, extra 1d8 (rolled even without a threat)
    o = one_attack(10, "1d8 weapon + 2 str", crit_range=19, dice=script(12, 6, 1))
    assert o.to_hit == 22
    assert not o.threatened
    assert o.damage.total == 8


def test_one_attack_threat(script):
    # d20, confirm d20, normal 1d8, extra 1d8
    o = one_attack(5, "1d8 weapon + 2 str", crit_range=19, dice=script(19, 7, 6, 3))
    assert o.threatened
    assert o.confirm_total == 12
    assert o.crit_damage.total == 6 + 2 + 3 + 2


def test_sequence_narrowing(script):
    fa = attack(
        [("A", 10, "1d6 a + ~1d6 sneak"), ("B", 5, "1d6 a + ~1d6 sneak")],
        dice=script(20, 15, 1, 2, 3, 10, 4, 5, 6),
    )
    assert fa[1].threatened and not fa[2].threatened
    # A crit: (1 + 2 sneak) + extra 3; B hit: 4 + 5 sneak.
    assert fa.hit(2).crit(1).damage.total == 1 + 2 + 3 + 4 + 5
    assert fa.hit(2).crit(1).without("sneak").damage.total == 1 + 3 + 4


def test_sequence_numbering(script):
    fa = attack([("A", 1, "1 a"), ("B", 2, "1 b")], dice=script(5, 6))
    assert fa[1].label == "A" and fa[2].label == "B" and fa[-1].label == "B"
    for num in (0, 3, -3):
        with pytest.raises(IndexError, match="numbered 1 to 2"):
            fa[num]
    with pytest.raises(IndexError, match="No attack 3"):
        fa.hit(1, 3)
    with pytest.raises(IndexError, match="No attack 0"):
        fa.crit(0)
