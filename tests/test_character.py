import tomllib
from pathlib import Path

import pytest

from fullattack import load, parse_character

EXAMPLE = Path(__file__).parent.parent / "examples" / "allister.toml"

CHARACTER = tomllib.loads("""
system = "pf1"

[weapons.axe]
bonus = 10
damage = "1d8 axe + ~1d6 frost"
crit_range = 20
crit_mult = 3

[weapons.dagger]
bonus = 8
damage = "1d4 dagger"

[routines]
full = [{ weapon = "axe" }, { weapon = "dagger", step = 1, label = "Off hand" }]

[buffs.rage]
active = true
damage = "2 rage"

[buffs.bless]
damage = { axe = "1 bless" }
""")


def test_routine(script):
    c = parse_character(CHARACTER, "Grog")
    # axe: d20, 1d8, 1d6, 2 rage, crit extra 2x 1d8; dagger: d20, 1d4, crit 1d4
    fa = c.full(dice=script(12, 5, 4, 3, 2, 9, 3, 4))
    assert fa[1].label == "axe" and fa[1].bonus == 10
    assert fa[1].damage.total == 5 + 4 + 2
    assert fa[1].crit_note == "x3"
    assert fa[2].label == "Off hand" and fa[2].bonus == 3
    assert fa[2].damage.total == 3 + 2


def test_buff_toggles(script):
    c = parse_character(CHARACTER)
    assert c.active == {"rage"}
    assert c.buff("bless", "-rage").active == {"bless"}
    o = c.attack("axe", buffs=("+bless",), dice=script(12, 5, 4, 1, 1))[1]
    assert [t.label for t in o.damage.terms] == ["axe", "frost", "rage", "bless"]
    with pytest.raises(ValueError, match="Unknown buff"):
        c.buff("haste")


def test_single_weapon_attack(script):
    c = parse_character(CHARACTER)
    fa = c.dagger(dice=script(20, 2, 3, 1))
    assert len(fa) == 1 and fa[1].check.auto_hit


def test_unknown_name():
    c = parse_character(CHARACTER)
    with pytest.raises(AttributeError):
        c.flurry()
    with pytest.raises(ValueError, match="Unknown routine or weapon"):
        c.attack("flurry")


@pytest.mark.parametrize(
    "change, error",
    [
        ({"system": "gurps"}, "Unknown game system"),
        ({"weapons": {"axe": {"damage": "1d8 axe + oops"}}}, r"weapons\.axe\.damage"),
        ({"weapons": {"axe": {"keen": True}}}, "invalid pf1 weapon rules"),
        ({"routines": {"full": [{"weapon": "bow"}]}}, "unknown weapon 'bow'"),
        ({"buffs": {"bless": {"damage": {"bow": "1 bless"}}}}, "unknown weapon"),
    ],
)
def test_config_errors(change, error):
    with pytest.raises(ValueError, match=error):
        parse_character({**CHARACTER, **change})


def test_load_example():
    allister = load(EXAMPLE)
    assert allister.name == "Allister"
    assert len(allister.routines["full"]) == 9
    assert [o.bonus for o in allister.full()] == [25, 25, 20, 20, 15, 15, 10, 20, 25]


def test_load_by_name(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "full-attack").mkdir()
    (tmp_path / "full-attack" / "grog.toml").write_text('system = "3.5"\n')
    c = load("grog")
    assert c.name == "Grog" and c.system.name == "3.5"
