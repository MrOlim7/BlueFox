import hashlib
import json
from unittest.mock import Mock

import pytest
import requests

from Program import legacy_tools as core, ui
from Program.passwords import pwned_count
from Program.tools import ioc_analyzer, password_strength_estimator


@pytest.mark.parametrize("value,kind", [("999.999.999.999", "unknown"),
    ("192.0.2.1", "ipv4"), ("2001:db8::1", "ipv6"), ("::ffff:192.0.2.1", "ipv6"),
    ("2001:db8:::1", "unknown"), ("http://999.999.999.999/", "unknown"),
    ("https://", "unknown"), ("https://example.org:99999/", "unknown"),
    ("example.org", "domain"), ("person@example.org", "email"), ("a" * 64, "hash_sha256")])
def test_ioc_validation_and_export(monkeypatch, value, kind):
    monkeypatch.setattr(core, "get_input", lambda _: value)
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    ioc_analyzer.run()
    result = save.call_args.args[1]
    assert result["type"] == kind and result["input"] == value
    if kind != "unknown":
        assert result["links"]


@pytest.mark.parametrize("url,hostname,link_type", [
    ("https://user:password@example.org:8443/path", "example.org", "/domain/"),
    ("https://user:password@[2001:db8::1]:8443/path", "2001:db8::1", "/ip-address/"),
])
def test_url_links_use_hostname_and_preserve_input(url, hostname, link_type):
    result = ioc_analyzer.analyze(url)
    assert result["type"] == "url" and result["input"] == url
    assert result["hostname"] == hostname
    assert link_type in result["links"]["virustotal"]
    assert all("user" not in link and "password" not in link and "8443" not in link for link in result["links"].values())


def test_password_estimator_uses_masked_input_without_stripping(monkeypatch, capsys):
    secret = "  Password123!  "
    getpass = Mock(return_value=secret)
    monkeypatch.setattr(ui.getpass, "getpass", getpass)
    monkeypatch.setattr(core, "get_input", Mock(side_effect=AssertionError("visible input")))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    password_strength_estimator.run()
    output = capsys.readouterr().out
    assert f"Length: {len(secret)}" in output and "Estimation limitée" in output
    assert secret not in output and "Strong" not in output
    save.assert_not_called()
    getpass.assert_called_once()


def test_breach_password_prefix_only_no_secret_or_full_hash_in_output_or_exports(monkeypatch, capsys):
    secret = "  password with spaces  "
    digest = hashlib.sha1(secret.encode()).hexdigest().upper()
    answers = iter(["fixture@example.org", "oui"])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    monkeypatch.setattr(ui.getpass, "getpass", Mock(return_value=secret))
    http = Mock(side_effect=[
        Mock(status_code=200, json=lambda: {"found": True, "result": [
            {"source": "fixture", "password": secret, "hash": digest}]}),
        Mock(status_code=200, text=digest[5:] + ":12"),
    ])
    monkeypatch.setattr(requests, "get", http)
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.haveibeenpwned()
    request = http.call_args_list[1]
    assert request.args == (f"https://api.pwnedpasswords.com/range/{digest[:5]}",)
    assert secret not in str(request) and digest not in str(request) and digest[5:] not in str(request)
    data = save.call_args.args[1]
    assert data["password_pwned"] is True and data["password_count"] == 12
    output = capsys.readouterr().out + json.dumps(data)
    assert secret not in output and digest not in output


@pytest.mark.parametrize("status,text", [(401, ""), (429, ""), (200, ""), (200, "not a range")])
def test_password_unavailable_is_not_negative(monkeypatch, status, text):
    monkeypatch.setattr(requests, "get", Mock(return_value=Mock(status_code=status, text=text)))
    with pytest.raises(ValueError):
        pwned_count("fixture")


def test_password_absent_valid_range(monkeypatch):
    monkeypatch.setattr(requests, "get", Mock(return_value=Mock(status_code=200, text="0" * 35 + ":0")))
    assert pwned_count("fixture") == 0


@pytest.mark.parametrize("secret", ["   ", " trailing "])
def test_password_spaces_are_hashed_exactly(monkeypatch, secret):
    digest = hashlib.sha1(secret.encode()).hexdigest().upper()
    http = Mock(return_value=Mock(status_code=200, text=digest[5:] + ":7"))
    monkeypatch.setattr(requests, "get", http)
    assert pwned_count(secret) == 7
    assert http.call_args.args[0].endswith(digest[:5])


def test_password_malformed_response_after_match_is_rejected(monkeypatch):
    digest = hashlib.sha1(b"fixture").hexdigest().upper()
    monkeypatch.setattr(requests, "get", Mock(return_value=Mock(
        status_code=200, text=digest[5:] + ":1\nmalformed")))
    with pytest.raises(ValueError):
        pwned_count("fixture")


def test_password_transport_exception_does_not_leak_secrets(monkeypatch, capsys):
    secret = " secret with spaces "
    digest = hashlib.sha1(secret.encode()).hexdigest().upper()
    answers = iter(["fixture@example.org", "oui"])
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    monkeypatch.setattr(ui.getpass, "getpass", lambda _: secret)
    monkeypatch.setattr(requests, "get", Mock(side_effect=[
        Mock(status_code=404), requests.Timeout(secret + digest)]))
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.haveibeenpwned()
    data = save.call_args.args[1]
    assert data["password_status"] == "unavailable" and "password_pwned" not in data
    output = capsys.readouterr().out + json.dumps(data)
    assert secret not in output and digest not in output
