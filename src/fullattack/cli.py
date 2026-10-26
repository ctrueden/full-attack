import argparse
import keyword
import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from .config import characters, config_dir, examples_dir, find, load
from .style import THEMES


def _variable(path: Path) -> str:
    """A Python variable name for a character file, e.g. allister for allister.toml."""
    name = re.sub(r"\W", "_", path.stem.lower())
    return f"{name}_" if keyword.iskeyword(name) or name[:1].isdigit() else name


def _init(name: str) -> int:
    source = examples_dir() / f"{name}.toml"
    if not source.is_file():
        examples = ", ".join(p.stem for p in sorted(examples_dir().glob("*.toml")))
        print(f"No example named {name!r} (examples: {examples})", file=sys.stderr)
        return 1
    target = config_dir() / source.name
    if target.exists():
        print(f"{target} already exists; not overwriting it", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    print(f"Copied example {name!r} to {target}; edit it to make it your own.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Load characters, then start a Python REPL to roll their attacks."""
    parser = argparse.ArgumentParser(
        prog="full-attack",
        description="Start a Python REPL with full-attack imported and the given "
        "characters loaded, each as a variable named after its file.",
    )
    parser.add_argument(
        "characters",
        nargs="*",
        metavar="CHARACTER",
        help=f"a character name (from {config_dir()} or the bundled examples) "
        "or a TOML file path",
    )
    parser.add_argument("--theme", choices=THEMES, help="color theme")
    parser.add_argument(
        "--list", action="store_true", help="list available characters and exit"
    )
    parser.add_argument(
        "--init",
        metavar="EXAMPLE",
        help=f"copy a bundled example character into {config_dir()} and exit",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('full-attack')}"
    )
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(characters()))
        return 0
    if args.init:
        return _init(args.init)

    # Load each character here first, to report problems before the REPL starts.
    setup = ["from fullattack import *"]
    print(f"full-attack {version('full-attack')}")
    hint = "load('allister')"
    for character in args.characters:
        try:
            path = find(character)
            loaded = load(path)
        except (OSError, ValueError) as e:
            print(f"full-attack: {e}", file=sys.stderr)
            return 1
        # The REPL runs in this directory, so loading what was given works there.
        line = f"{_variable(path)} = load({str(character)!r})"
        setup.append(line)
        print(f"  {line}")
        variable = _variable(path)
        if hint.startswith("load"):
            first = next(iter([*loaded.routines, *loaded.weapons]), None)
            hint = f"{variable}.{first}()" if first else variable
    print(f"Try: {hint}", flush=True)

    env = {**os.environ}
    if args.theme:
        env["FULL_ATTACK_THEME"] = args.theme
    command = [sys.executable, "-i", "-c", "; ".join(setup)]
    return subprocess.run(command, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
