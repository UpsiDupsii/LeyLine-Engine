"""Basic sanity tests for LeyLine engine."""

import leyline


def test_version() -> None:
    assert leyline.__version__ == "0.1.0"
