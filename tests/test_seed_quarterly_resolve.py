"""Unit tests for quarterly suburb name resolution (no DB)."""
import pytest

from ingestion.seed_quarterly import resolve_quarterly_name_to_canonical


@pytest.fixture
def canonical():
    return {"MELBOURNE", "BALLARAT", "ST KILDA", "EAST MALVERN"}


def test_direct_match(canonical):
    name, kind = resolve_quarterly_name_to_canonical("MELBOURNE", canonical)
    assert name == "MELBOURNE"
    assert kind == "direct"


def test_directional_strips_suffix(canonical):
    name, kind = resolve_quarterly_name_to_canonical("BALLARAT NORTH", canonical)
    assert name == "BALLARAT"
    assert kind == "directional"


def test_parenthetical_strips(canonical):
    name, kind = resolve_quarterly_name_to_canonical("ST KILDA (WEST)", canonical)
    assert name == "ST KILDA"
    assert kind == "parenthetical"


def test_empty_unmatched(canonical):
    assert resolve_quarterly_name_to_canonical("", canonical) == (None, "unmatched")
    assert resolve_quarterly_name_to_canonical("   ", canonical) == (None, "unmatched")


def test_unknown_unmatched(canonical):
    name, kind = resolve_quarterly_name_to_canonical("NOWHERE", canonical)
    assert name is None
    assert kind == "unmatched"


def test_whitespace_uppercase(canonical):
    name, kind = resolve_quarterly_name_to_canonical("  melbourne  ", canonical)
    assert name == "MELBOURNE"
    assert kind == "direct"
