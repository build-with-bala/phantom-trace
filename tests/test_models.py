"""Tests for data models."""

from src.models import PersonProfile, SiteResult, CheckType


def test_site_result_defaults():
    r = SiteResult(site="github", url="https://github.com/test", category="dev", username="test")
    assert r.found is False
    assert r.error is None
    assert r.metadata == {}


def test_person_profile_counts():
    p = PersonProfile(query="test", query_type="username")
    p.sites_found = [SiteResult(site="a", url="", category="", username="test", found=True)]
    p.sites_not_found = [SiteResult(site="b", url="", category="", username="test")]
    assert p.total_found == 1
    assert p.total_checked == 2


def test_profile_to_dict():
    p = PersonProfile(query="test", query_type="username", confidence_score=0.5)
    d = p.to_dict()
    assert d["query"] == "test"
    assert d["confidence_score"] == 0.5


def test_check_type_enum():
    assert CheckType.STATUS_CODE.value == "status_code"
    assert CheckType.RESPONSE_BODY.value == "response_body"
