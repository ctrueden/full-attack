import pytest


def scripted(*values: int):
    """Return a die roller that yields the given values in order."""
    it = iter(values)

    def dice(sides: int) -> int:
        value = next(it, None)
        assert value is not None, f"ran out of scripted rolls for a d{sides}"
        assert 1 <= value <= sides, f"scripted {value} for a d{sides}"
        return value

    return dice


@pytest.fixture
def script():
    return scripted
