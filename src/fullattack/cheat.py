import keyword
import sys

from .character import Character, RoutineEntry
from .config import examples_dir, load
from .style import stripe, theme

README = "https://github.com/ctrueden/full-attack#readme"


def _loaded() -> dict[str, Character]:
    """The characters held in the interactive session's variables, by variable."""
    return {
        name: value
        for name, value in vars(sys.modules["__main__"]).items()
        if isinstance(value, Character) and not name.startswith("_")
    }


def _attacks(character: Character, name: str) -> int:
    """How many attacks a routine or weapon would roll right now."""
    entries = character.routines.get(name, (RoutineEntry(name),))
    return sum(not e.buff or e.buff in character.active for e in entries)


def _call(var: str, c: Character, name: str, args: str = "") -> str:
    """Code that rolls a routine or weapon, as a method if its name allows it."""
    # Note: A name like "attack" is hidden by the real attribute of that name.
    usable = name.isidentifier() and not keyword.iskeyword(name)
    if usable and name not in object.__dir__(c):
        return f"{var}.{name}({args})"
    return f'{var}.attack("{name}"{", " + args if args else ""})'


def _combat(var: str, c: Character, target: str) -> list[tuple]:
    """Sections showing a round of combat, using the character's own names."""
    # Note: Attack numbers must exist, since `hit` and `crit` reject others.
    count = _attacks(c, target)
    hits = ", ".join(map(str, range(1, max(2, min(count, 3)))))
    crit = min(count, 3)
    rows = [
        (f"fa = {_call(var, c, target)}", "roll everything up front"),
        (f"fa[{crit}]", f"look at attack #{crit} again"),
        (f"fa.hit({hits})", "these hit: total their damage"),
        (f"fa.hit({hits}).crit({crit})", f"...and #{crit} is a crit"),
    ]
    terms = [t for w in c.weapons.values() for t in w.damage]
    label = next((t.label for t in sorted(terms, key=lambda t: not t.extra)), None)
    if label:
        rows.append(
            (
                f'fa.hit({hits}).crit({crit}).without("{label}")',
                "...minus what the target ignores",
            )
        )
    weapon = _call(var, c, next(iter(c.weapons)))
    rows.append((weapon, "a single attack with one weapon"))
    sections = [("Roll a round, then call hits and crits", rows)]

    inactive = [b for b in c.buffs.values() if b.name not in c.active]
    # Note: The shortest names keep the examples within the terminal's width.
    on = min((b.name for b in inactive if not b.condition), key=len, default=None)
    off = min((b for b in c.buffs if b in c.active), key=len, default=None)
    condition = min((b.name for b in inactive if b.condition), key=len, default=None)
    rows = []
    if on:
        rows.append((_call(var, c, target, f'buffs="{on}"'), "one roll with a buff on"))
    if off:
        rows.append(
            (_call(var, c, target, f'buffs="-{off}"'), "one roll with a buff off")
        )
    if on:
        rows.append((f'{var} += "{on}"', "stays on until you change it"))
    if off:
        rows.append((f'{var} -= "{off}"', "stays off until you change it"))
    if condition:
        rows.append((f'{var} += "{condition}"', "conditions work the same way"))
    rows.append((_call(var, c, target, "bonus=2"), "adjust attack bonus for one roll"))
    rows.append((_call(var, c, target, "adv=True"), "advantage (or dis=True)"))
    sections.append(("Buffs and circumstances", rows))
    return sections


def cheat(character: Character | None = None) -> None:
    """Print examples of the most common commands, using a character's own names.

    With no argument, uses the first character loaded in this session, or
    else the bundled example Allister.
    """
    loaded = _loaded()
    if character is None:
        character = next(iter(loaded.values()), None)
    sections = []
    if character is None:
        var = "allister"
        character = load(examples_dir() / "allister.toml")
        rows = [(f'{var} = load("allister")', "load a character by name")]
        sections.append(("Get started", rows))
    else:
        var = next((n for n, c in loaded.items() if c is character), "pc")

    names = [*character.routines, *character.weapons]
    target = next((n for n in names if _attacks(character, n)), None)
    if target:
        sections.extend(_combat(var, character, target))

    rows = [
        (var, "show weapons, routines, and buffs"),
        ('roll("2d6 fire - 1 weak")', "roll any damage expression"),
        ("characters()", "list characters you can load()"),
    ]
    rows += [(f"cheat({n})", f"this sheet for {n}") for n in loaded if n != var]
    sections.append(("Everything else", rows))

    width = max(len(code) for _, rows in sections for code, _ in rows)
    sgr = theme().stripe
    print(f"Cheat sheet: {var} is {character.name} ({character.system.name})")
    for heading, rows in sections:
        print(f"\n{stripe(heading, sgr)}")
        for code, note in rows:
            print(f"  {code:{width}}  # {note}")
    print(f"\nFull guide: {README}")
