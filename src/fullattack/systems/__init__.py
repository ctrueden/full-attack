from .base import Check, GameSystem
from .d20_3x import ThirdEdition
from .dnd5e import FifthEdition

SYSTEMS: dict[str, GameSystem] = {
    s.name: s
    for s in (
        ThirdEdition("3.0"),
        ThirdEdition("3.5"),
        ThirdEdition("pf1"),
        FifthEdition(),
    )
}


def get_system(system: GameSystem | str) -> GameSystem:
    """Look up a game system by name (e.g. "pf1"), passing systems through."""
    if not isinstance(system, str):
        return system
    try:
        return SYSTEMS[system.lower()]
    except KeyError:
        known = ", ".join(SYSTEMS)
        raise ValueError(f"Unknown game system {system!r} (known: {known})") from None
