# full-attack 🎲

Speed up D&D combat: roll an entire attack routine at once, then narrow it
down as the GM calls hits and misses.

Every die is rolled up front: to-hit, crit confirmations, normal damage, and
critical damage. You read off the attack totals, the GM says which ones hit,
and full-attack adds up the damage, broken down by type, so you can
also drop whatever the target is immune to.

You drive it from the Python REPL.

Supported game systems: D&D 3.0 (`"3.0"`), D&D 3.5 (`"3.5"`), and
Pathfinder 1E (`"pf1"`).

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
git clone https://github.com/ctrueden/full-attack
cd full-attack
mkdir -p ~/.config/full-attack
cp examples/allister.toml ~/.config/full-attack/
```

Start a REPL with everything imported and your character loaded:

```sh
uv run python -i -c "from fullattack import *; al = load('allister')"
```

(From outside the repository, use `uv run --project /path/to/full-attack ...`.)

```python
>>> al
Allister (pf1)
Weapons:    strike +35, shield +32
Routines:   full (9)
Active:     merciful, power attack, haste, good hope
Buffs:      flanking, held ground, combat expertise, fighting defensively,
            defensive crane, housing spirit, corrupted outsider, death mark,
            challenge, sanctified heroism, greater heroism, smite, tiger style
Conditions: dazzled, entangled, exhausted, fatigued, frightened, invisible,
            prone, shaken, sickened
```

The weapon bonuses shown include the active buffs and conditions.

## A combat round

### 1. Roll the routine

```python
>>> fa = al.full()
>>> fa
#1 First unarmed strike: d20(11) + 35 = 46
Damage:
 10  monk
  7  holy
 25  sneak attack
  2  strength
  2  martial training
  5  magic
  4  merciful
 10  power attack
  2  good hope
--------------------
 67  Total

#2 First shield bash: d20(8) + 32 = 40
...

#6 Third shield bash: d20(20) + 22 = 42 (auto-hit)
Damage:
...
--------------------
 46  Total
Crit confirm: d20(3) + 22 = 25
Critical damage (x2):
...
--------------------
 62  Total
...
```

Attacks are numbered from 1. Call out the attack totals to the GM. A
threat also shows its confirmation roll and its full critical damage.
A natural 20 is flagged `(auto-hit)` and a natural 1 is flagged
`(auto-miss)`.

Keep `fa` around: everything below reuses the same rolls. Calling
`al.full()` again rolls a new routine.

To look at a single attack again, use `fa[6]` (`fa[-1]` is the last one).

### 2. Tell it which attacks landed

```python
>>> fa.hit(1, 2, 4).crit(6)
#1 First unarmed strike: 67
#2 First shield bash: 50
#4 Second shield bash: 52
#6 Third shield bash (crit x2): 62
====================
 10  monk
  7  holy
129  sneak attack
  6  strength
  2  martial training
 25  magic
  4  merciful
 30  power attack
 10  good hope
  8  weapon
--------------------
231  Total
```

- `crit(...)` marks confirmed crits. A crit counts as a hit, so there's no
  need to repeat it in `hit(...)`.
- Numbers that don't match an attack raise an error, so a typo like
  `fa.hit(10)` won't quietly drop damage.
- Each call to `hit(...)` or `crit(...)` *replaces* the previous one rather
  than adding to it. If the GM corrects you, just call it again with the
  full list.
- full-attack doesn't police the rules: you can `crit` an attack that
  didn't threaten, and it will happily show you its critical damage.

### 3. Remove damage the target ignores

```python
>>> fa.hit(1, 2, 4).crit(6).without("sneak")
```

`without(...)` drops every damage term whose label contains any of the
given strings (case-insensitive), keeping the same rolls. It works anywhere
in the chain, on a single attack too (`fa[2].without("sneak", "holy")`),
and you can call it as many times as you like.

Common uses: a target that is immune to precision damage (`"sneak"`), not
evil (`"holy"`), or a creature for which merciful should be off
(`"merciful"`).

## Other rolls

Attack with a single weapon (a standard action, attack of opportunity, ...):

```python
>>> al.strike()
>>> al.shield()
```

The result works the same as a routine: `al.strike().hit(1)`.

Roll a damage expression on its own:

```python
>>> roll("2d6 fire - 1 weak")
  9  fire
 -1  weak
--------------------
  8  Total
```

An ad-hoc attack, without a character file. Arguments after the damage are
the crit range and multiplier:

```python
>>> one_attack(18, "1d12 greataxe + 7 strength", 20, 3)
```

## Buffs, conditions, and circumstances

Buffs and conditions are named sets of modifiers you can switch on and off:
to attack bonuses, to damage, and to damage on a crit only. The character
summary lists which ones are active.

For one roll only:

```python
>>> al.full(buffs="-power attack")
>>> al.full(buffs=["smite", "flanking", "shaken"])
```

For the rest of the fight, until you change it back:

```python
>>> al = al.buff("held ground", "-haste")
>>> al = al.buff("-held ground", "haste")
```

A name on its own (or with `+`) switches a buff on, and a leading `-`
switches it off. Conditions toggle exactly the same way.

Switching off haste also drops the haste attack from the routine.

For a one-off circumstance that isn't worth a buff, adjust the attack bonus
for one roll, either for every weapon or per weapon:

```python
>>> al.full(bonus=2)
>>> al.full(bonus={"shield": -2})
```

Buffs that are alternatives to each other, like `flanking` and
`outflanking`, share a `group`: switching one on switches the others off.
Beyond that, full-attack doesn't know the stacking rules: if two buffs
don't stack (say, two morale bonuses), don't switch both on.

## Writing a character file

Character files are [TOML](https://toml.io/). Put them in
`~/.config/full-attack/` to load them by name (`load("allister")` reads
`allister.toml`), or load any file directly with
`load("path/to/grog.toml")` (the `.toml` is optional when the path has a
`/`, e.g. `load("examples/allister")`). `characters()` lists the names available.
(If `$XDG_CONFIG_HOME` is set, that is used instead of `~/.config`.)

See [examples/allister.toml](examples/allister.toml) for a complete one.

```toml
name = "Grog"        # optional; defaults to the file name
system = "pf1"       # "3.0", "3.5" or "pf1"

[weapons.axe]
bonus = 18           # attack bonus, before buffs and conditions
damage = "1d12 greataxe + ~1d6 flaming + 7 strength"
crit_range = 20      # threatens on 20 (the default)
crit_mult = 3        # x3 damage on a crit (default x2)

[weapons.bite]
bonus = 13
damage = "1d6 bite + 3 strength"

[routines]
full = [
  { weapon = "axe", label = "Greataxe" },
  { weapon = "axe", step = 1, label = "Greataxe (iterative)" },
  { weapon = "axe", step = 2 },
  { weapon = "bite" },
  { weapon = "axe", label = "Haste", buff = "haste" },
]

[buffs.rage]
active = true                      # on when the character loads
attack = 2                         # a value for every weapon...
damage = { axe = "3 rage", bite = "1 rage" }  # ...or one per weapon

[buffs.haste]
attack = 1

[buffs."vicious strikes"]
crit_damage = { axe = "1d6 bleed" }  # added on a crit only

[buffs.flanking]
group = "flanking"                 # alternatives: one at a time
attack = 2

[buffs.outflanking]
group = "flanking"
attack = 4

[conditions.shaken]
attack = -2
```

**Weapons.** Each one needs a `bonus` and a `damage` expression. In 3.x,
`crit_range` and `crit_mult` set the critical threat range and multiplier.
The weapon's name (`axe`) doubles as a method: `grog.axe()`.

**Routines.** A list of attacks, each naming a `weapon`. `step` is the
iterative attack number, counting from 0: in 3.x each step takes another
−5 (step 1 is −5, step 2 is −10, and so on), and step defaults to 0. `label`
names the attack in the output (it defaults to the weapon name). Each
routine is also a method: `grog.full()`. A routine and a weapon can't share
a name. An entry with a `buff` is only rolled while that buff is active.

**Buffs and conditions** can set `attack` (a number), `damage` and
`crit_damage` (expressions), `active`, and `group`. Each of `attack`,
`damage` and `crit_damage` can be a single value for every weapon or a
table of values per weapon. Switching on a buff switches off the others in
its `group`, and at most one buff per group can start out `active`.
`crit_damage` is added to critical damage as is, without being multiplied.
Conditions go in `[conditions.NAME]` and work the same way as buffs; they
are just listed separately. Each name must be unique across both.

Mistakes are reported with their location, e.g.
`grog.toml: weapons.axe.damage: Could not parse term: 'oops'`.
After editing a file, `load` it again to pick up the changes.

### Damage expressions

An expression is a list of terms joined by `+` or `-`:

```
2d10 monk + ~2d6 holy + ~10d6 sneak attack + 7 strength - 2 enfeebled
```

- `NdM label` rolls N dice with M sides; `N label` is a flat amount.
- Every term needs a label. Labels can contain spaces and hyphens
  (`two-weapon fighting`), and terms with the same label are combined in
  totals.
- Mark **extra** damage with `~`: any dice beyond the weapon's own, such as
  sneak attack, flaming, holy, or merciful. In 3.x and Pathfinder 1E, a
  critical hit multiplies the weapon's dice and flat bonuses, but never
  extra damage.
- A `-` term subtracts.

## Tips

- **Reproducible rolls:** `import random; random.seed(42)` before rolling.
- **Rolling your own dice:** every rolling function accepts `dice=`, a
  function that takes a number of sides and returns the result. For
  example, to always roll the maximum:
  `al.full(dice=lambda sides: sides)`.

## Development

```sh
make test   # run the tests
make lint   # format and lint
```
