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
full = [
  { weapon = "axe" },
  { weapon = "dagger", step = 1, label = "Off hand" },
  { weapon = "axe", label = "Haste", buff = "haste" },
]

[buffs.rage]
active = true
damage = "2 rage"

[buffs.bless]
damage = { axe = "1 bless" }

[buffs.focus]
attack = { dagger = 3 }
crit_damage = "1d4 bleed"

[buffs.haste]
attack = 1

[buffs.flanking]
group = "flanking"
attack = 2

[buffs.outflanking]
group = "flanking"
attack = 4

[conditions.shaken]
attack = -2
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
    o = c.attack("axe", buffs="-rage", dice=script(12, 5, 4, 1, 1))[1]
    assert [t.label for t in o.damage.terms] == ["axe", "frost"]
    with pytest.raises(ValueError, match="Unknown buff"):
        c.buff("bardsong")


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
        ({"buffs": {"bless": {"attack": {"bow": 1}}}}, "unknown weapon"),
        ({"routines": {"full": [{"weapon": "axe", "buff": "x"}]}}, "unknown buff"),
        ({"conditions": {"rage": {}}}, "already defined"),
        (
            {
                "buffs": {
                    "a": {"group": "g", "active": True},
                    "b": {"group": "g", "active": True},
                }
            },
            "both active",
        ),
    ],
)
def test_config_errors(change, error):
    with pytest.raises(ValueError, match=error):
        parse_character({**CHARACTER, **change})


def test_load_example():
    allister = load(EXAMPLE)
    assert allister.name == "Allister"
    assert len(allister.routines["full"]) == 9
    # Base +37/+34, with power attack (-5), haste (+1), and good hope (+2).
    assert [o.bonus for o in allister.full()] == [35, 32, 30, 27, 25, 22, 20, 27, 35]
    unhasted = allister.full(buffs="-haste")
    assert len(unhasted) == 8 and unhasted[-1].label == "Eternal defender slam"


def test_load_by_name(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "full-attack").mkdir()
    (tmp_path / "full-attack" / "grog.toml").write_text('system = "3.5"\n')
    c = load("grog")
    assert c.name == "Grog" and c.system.name == "3.5"


def test_load_without_suffix():
    assert load(EXAMPLE.with_suffix("")).name == "Allister"


def test_attack_modifiers(script):
    c = parse_character(CHARACTER)
    assert [o.bonus for o in c.full(buffs="haste", dice=script(*[1] * 30))] == [
        11,
        4,
        11,
    ]
    fa = c.full(buffs=["focus", "shaken"], bonus={"axe": 5}, dice=script(*[1] * 30))
    assert [o.bonus for o in fa] == [13, 4]
    assert c.dagger(bonus=-1, dice=script(*[1] * 9))[1].bonus == 7


def test_crit_only_damage(script):
    c = parse_character(CHARACTER)
    # d20, 1d4 dagger, crit extra 1d4, then crit-only 1d4 bleed
    o = c.dagger(buffs=["focus", "-rage"], dice=script(5, 2, 3, 4))[1]
    assert [t.label for t in o.damage.terms] == ["dagger"]
    assert [(t.label, t.value) for t in o.crit_damage.terms] == [
        ("dagger", 5),
        ("bleed", 4),
    ]


def test_summary():
    text = str(parse_character(CHARACTER, "Grog").buff("haste"))
    assert "Weapons:    axe +11, dagger +9" in text
    assert "Active:     rage, haste" in text
    assert "Buffs:      bless, focus" in text
    assert "Conditions: shaken" in text


def test_buff_groups():
    c = parse_character(CHARACTER)
    assert c.buff("flanking").buff("outflanking").active == {"rage", "outflanking"}
    assert c.buff("outflanking", "flanking").active == {"rage", "flanking"}
    assert c.buff("flanking", "-flanking").active == {"rage"}
    assert c.buff("flanking", "haste").active == {"rage", "flanking", "haste"}
