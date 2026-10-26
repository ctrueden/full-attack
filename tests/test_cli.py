import subprocess

import pytest

from fullattack import characters, find, load
from fullattack.cli import _variable, main


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path / "full-attack"


def test_bundled_examples(config):
    assert {"allister", "brynn"} <= set(characters())
    assert load("allister").name == "Allister"
    with pytest.raises(FileNotFoundError, match="No character 'grog' in"):
        find("grog")


def test_config_dir_shadows_examples(config):
    config.mkdir()
    (config / "allister.toml").write_text('name = "Mine"\nsystem = "pf1"\n')
    assert load("allister").name == "Mine"


def test_init(config, capsys):
    assert main(["--init", "brynn"]) == 0
    assert (config / "brynn.toml").is_file()
    assert main(["--init", "brynn"]) == 1
    assert "not overwriting" in capsys.readouterr().err
    assert main(["--init", "grog"]) == 1


def test_variable_names(tmp_path):
    assert _variable(tmp_path / "Allister.toml") == "allister"
    assert _variable(tmp_path / "my-char.toml") == "my_char"
    assert _variable(tmp_path / "class.toml") == "class_"


def test_launch(config, monkeypatch, capsys):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    assert main(["allister", "brynn"]) == 0
    setup = commands[0][-1]
    assert setup.startswith("from fullattack import *; allister = load('allister')")
    assert "brynn = load(" in setup
    assert "Try: allister.full()" in capsys.readouterr().out


def test_launch_bad_character(config, capsys):
    assert main(["grog"]) == 1
    assert "No character 'grog'" in capsys.readouterr().err
