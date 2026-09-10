import ipaddress
from unittest.mock import Mock

import pytest

from Program import extra_tools, legacy_tools as core
from Program.reliability import host_bounds, parse_ports
from Program.tools import netblock_host_counter


@pytest.mark.parametrize("cidr,count,first,last", [
    ("192.0.2.0/31", 2, "192.0.2.0", "192.0.2.1"),
    ("192.0.2.1/32", 1, "192.0.2.1", "192.0.2.1"),
    ("2001:db8::/127", 2, "2001:db8::", "2001:db8::1"),
    ("2001:db8::/128", 1, "2001:db8::", "2001:db8::"),
    ("10.0.0.0/8", 2**24 - 2, "10.0.0.1", "10.255.255.254"),
    ("2001:db8::/64", 2**64 - 1, "2001:db8::1", "2001:db8::ffff:ffff:ffff:ffff"),
])
def test_calculators_never_enumerate(monkeypatch, cidr, count, first, last):
    def denied(*args):
        pytest.fail("Host enumeration is forbidden in calculators")
    monkeypatch.setattr(ipaddress.IPv4Network, "hosts", denied)
    monkeypatch.setattr(ipaddress.IPv6Network, "hosts", denied)
    assert host_bounds(ipaddress.ip_network(cidr)) == (count, first, last)
    monkeypatch.setattr(core, "get_input", lambda _: cidr)
    save = Mock()
    monkeypatch.setattr(core, "ask_save", save)
    core.subnet_calculator()
    assert save.call_args.args[1]["Nombre d'hôtes"] == count
    assert save.call_args.args[1]["Première IP"] == first
    assert save.call_args.args[1]["Dernière IP"] == last
    netblock_host_counter.run()
    assert save.call_args.args[1]["hosts_usable"] == count
    assert save.call_args.args[1]["first_host"] == first
    assert save.call_args.args[1]["last_host"] == last


@pytest.mark.parametrize("cidr", ["10.0.0.0/8", "2001:db8::/64"])
def test_sweep_consumes_at_most_256_hosts(monkeypatch, cidr):
    cls = type(ipaddress.ip_network(cidr))
    original = cls.hosts
    def guarded(network):
        for index, host in enumerate(original(network)):
            if index >= 256:
                pytest.fail("Sweep enumerated more than 256 hosts")
            yield host
    monkeypatch.setattr(cls, "hosts", guarded)
    monkeypatch.setattr(core, "get_input", lambda _: cidr)
    run = Mock(return_value=Mock(returncode=1))
    monkeypatch.setattr(extra_tools.subprocess, "run", run)
    monkeypatch.setattr(core, "ask_save", Mock())
    extra_tools.ping_sweep_cidr()
    assert run.call_count == 256


@pytest.mark.parametrize("value", ["1-999999999999999999999", "0-80", "90-80", "65536", "x", "80,"])
def test_invalid_ports_fail_before_materializing_range(value):
    with pytest.raises(ValueError):
        parse_ports(value)


def test_port_ranges_preserve_valid_ports():
    assert parse_ports("22, 80-82,80,65535") == [22, 80, 81, 82, 65535]


@pytest.mark.parametrize("tool,answers", [
    (core.port_scanner, ["192.0.2.1", "4", "1", "999999999999999999999"]),
    (core.tcp_connect_test, ["192.0.2.1", "1-999999999999999999999"]),
])
def test_bad_ports_do_not_scan(monkeypatch, capsys, tool, answers):
    answers = iter(answers)
    monkeypatch.setattr(core, "get_input", lambda _: next(answers))
    tool()
    assert "[ERREUR]" in capsys.readouterr().out
