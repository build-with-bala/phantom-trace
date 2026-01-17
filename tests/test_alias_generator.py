"""Tests for alias generation."""

import pytest
from src.modules.alias_generator import generate_aliases, generate_from_real_name


def test_basic_aliases():
    aliases = generate_aliases("johndoe")
    assert len(aliases) > 0
    assert "johndoe" not in aliases  # original excluded
    assert any("j0hndoe" in a or "johnd0e" in a for a in aliases)


def test_split_compound_username():
    aliases = generate_aliases("john_doe")
    assert "johndoe" in aliases or "doe_john" in aliases


def test_name_generation():
    aliases = generate_from_real_name("John", "Doe")
    assert "johndoe" in aliases
    assert "j.doe" in aliases
    assert "doejohn" in aliases


def test_name_with_year():
    aliases = generate_from_real_name("John", "Doe", birth_year=1995)
    assert any("95" in a for a in aliases)
    assert any("1995" in a for a in aliases)


def test_max_results():
    aliases = generate_aliases("test", max_results=10)
    assert len(aliases) <= 10
