"""External responses are fixtures; no requests to providers."""
from unittest.mock import Mock

import pytest
import requests

from Program import legacy_tools as core
from Program.config import config
from Program.tools.ip_lookup import IPLookupTool


def response(payload=None, status=200):
    return Mock(status_code=status, json=Mock(return_value=payload))


@pytest.fixture
def primary():
    return {"status": "success", "query": "192.0.2.1", "country": "Fixture",
            "countryCode": "FR", "isp": "Example", "lat": 1, "lon": 2,
            "regionName": "", "city": "", "zip": "", "timezone": "UTC",
            "org": "", "as": "", "mobile": False, "proxy": False, "hosting": False}


@pytest.mark.parametrize("status", [401, 429, 404, 503])
def test_http_errors_are_not_valid_results(monkeypatch, capsys, primary, status):
    http = Mock(return_value=response(primary, status))
    monkeypatch.setattr(requests, "get", http)
    assert IPLookupTool().run(ip="192.0.2.1")["success"] is False
    config.set("virustotal_api_key", "fixture")
    answers = iter(["3", "192.0.2.1"])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.virustotal_check()
    assert f"HTTP {status}" in capsys.readouterr().out
    save.assert_not_called()


@pytest.mark.parametrize("payload", [None, [], {}, {"status": "success"},
                                      {"status": "fail", "message": "private range"}])
def test_ip_invalid_schema(monkeypatch, payload):
    monkeypatch.setattr(requests, "get", Mock(return_value=response(payload)))
    assert not IPLookupTool().run(ip="192.0.2.1")["success"]


@pytest.mark.parametrize("field,value", [("query", "192.0.2.2"), ("lat", "1"),
                                         ("lon", float("nan")), ("country", None)])
def test_ip_invalid_required_fields(monkeypatch, primary, field, value):
    primary[field] = value
    monkeypatch.setattr(requests, "get", Mock(return_value=response(primary)))
    assert not IPLookupTool().run(ip="192.0.2.1")["success"]


@pytest.mark.parametrize("enrichment", [response({}, 429), response([]), response({}),
                                        response({"message": "invalid key"})])
def test_ip_enrichment_failure_is_partial_and_legacy_matches(monkeypatch, primary, enrichment):
    config.set("ipgeo_api_key", "fixture")
    monkeypatch.setattr(requests, "get", Mock(side_effect=[response(primary), enrichment] * 2))
    result = IPLookupTool().run(ip="192.0.2.1")
    assert result["success"] and result["partial"]
    assert "indisponible" in result["data"]["Avertissements"][0]
    monkeypatch.setattr(core, "get_input", lambda _: "192.0.2.1")
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.ip_lookup()
    assert save.call_args.args[1] == result["data"]


def test_ip_complete_and_optional_fields_missing(monkeypatch, primary):
    monkeypatch.setattr(requests, "get", Mock(return_value=response(primary)))
    assert IPLookupTool().run(ip="192.0.2.1")["partial"] is False
    del primary["city"]
    result = IPLookupTool().run(ip="192.0.2.1")
    assert result["partial"] and "Ville" not in result["data"]


@pytest.mark.parametrize("failure", [ValueError("bad JSON"), requests.Timeout("secret URL")])
def test_invalid_json_and_network_errors(monkeypatch, capsys, failure):
    http_response = response()
    http_response.json.side_effect = failure
    monkeypatch.setattr(requests, "get", Mock(return_value=http_response))
    assert not IPLookupTool().run(ip="192.0.2.1")["success"]
    config.set("virustotal_api_key", "fixture")
    answers = iter(["2", "example.org"])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.virustotal_check()
    output = capsys.readouterr().out
    assert "Aucune détection" not in output and "secret URL" not in output
    save.assert_not_called()


@pytest.mark.parametrize("stats", [None, {}, [], {"malicious": 0},
    {"malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0},
    {"malicious": False, "suspicious": 0, "harmless": 3, "undetected": 1},
    {"malicious": -1, "suspicious": 0, "harmless": 3, "undetected": 1}])
def test_vt_unavailable_analysis(monkeypatch, capsys, stats):
    config.set("virustotal_api_key", "fixture")
    monkeypatch.setattr(requests, "get", Mock(return_value=response(
        {"data": {"attributes": {"last_analysis_stats": stats}}})))
    answers = iter(["4", "a" * 64])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.virustotal_check()
    assert "Aucune détection" not in capsys.readouterr().out
    save.assert_not_called()


@pytest.mark.parametrize("mode", ["1", "2", "3", "4"])
@pytest.mark.parametrize("malicious", [0, 2])
def test_vt_valid_analysis_retains_counts_and_qualified_interpretation(monkeypatch, capsys, mode, malicious):
    config.set("virustotal_api_key", "fixture")
    stats = {"malicious": malicious, "suspicious": 1, "harmless": 10, "undetected": 20}
    monkeypatch.setattr(requests, "get", Mock(return_value=response(
        {"data": {"attributes": {"last_analysis_stats": stats}}})))
    answers = iter([mode, "fixture"])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.virustotal_check()
    assert save.call_args.args[1]["Malicious"] == malicious
    output = capsys.readouterr().out
    assert ("aucune garantie" if malicious == 0 else "2 MOTEURS") in output


@pytest.mark.parametrize("status,text,category", [(404, "", "not_found_count"),
    (200, "User not found", "not_found_count"), (200, "login page", "found_count"),
    (429, "", "error_count"), (500, "", "error_count")])
def test_social_empty_errors_and_possible_are_exportable(monkeypatch, capsys, status, text, category):
    monkeypatch.setattr(core, "get_input", lambda _: "fixture")
    monkeypatch.setattr(requests, "get", Mock(return_value=Mock(status_code=status, text=text, url="https://example.org/fixture")))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.social_media_lookup()
    data = save.call_args.args[1]
    assert data[category] > 0
    assert sum(data[k] for k in ("found_count", "not_found_count", "error_count")) == data[category]
    assert data["profile_status"] == "possible"
    assert "ne prouve" in capsys.readouterr().out


def test_social_timeouts_are_exportable(monkeypatch):
    monkeypatch.setattr(core, "get_input", lambda _: "fixture")
    monkeypatch.setattr(requests, "get", Mock(side_effect=requests.Timeout))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.social_media_lookup()
    data = save.call_args.args[1]
    assert data["error_count"] > 0 and data["found_count"] == 0 and data["profiles"] == {}


@pytest.mark.parametrize("payload", [None, [], {}, {"data": None},
                                      {"data": {"attributes": []}}, {"error": {"code": "NotFoundError"}}])
def test_vt_invalid_outer_schema(monkeypatch, capsys, payload):
    config.set("virustotal_api_key", "fixture")
    monkeypatch.setattr(requests, "get", Mock(return_value=response(payload)))
    answers = iter(["2", "example.org"])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.virustotal_check()
    assert "Aucune détection" not in capsys.readouterr().out
    save.assert_not_called()
