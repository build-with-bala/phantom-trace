"""Tests for metadata extraction."""

from src.models import PersonProfile, SiteResult
from src.modules.metadata_extractor import MetadataExtractor, calculate_confidence


def test_confidence_empty():
    p = PersonProfile(query="test", query_type="username")
    assert calculate_confidence(p) == 0.0


def test_confidence_with_results():
    p = PersonProfile(query="test", query_type="username")
    p.sites_found = [
        SiteResult(site=f"site{i}", url="", category=cat, username="test", found=True)
        for i, cat in enumerate(["social", "dev", "gaming", "blog"])
    ]
    p.real_name_guess = "Test User"
    p.locations = ["NYC"]
    score = calculate_confidence(p)
    assert 0.5 < score <= 1.0


def test_extractor_empty():
    ext = MetadataExtractor()
    result = ext.process_results([])
    assert result["probable_name"] is None
