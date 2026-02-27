"""Tests for term-dx CLI."""

import pytest
from click.testing import CliRunner

from term_dx.cli import main


def test_cli_help():
    """CLI --help exits 0 and shows usage."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "term-dx" in result.output
    assert "terminating" in result.output.lower()
