import ipaddress
from Program.reliability import host_bounds

from Program import legacy_tools as core


def run():
    cidr = core.get_input("CIDR (ex: 10.0.0.0/24)")
    if not cidr:
        return

    core.print_header(f"NETBLOCK HOST COUNTER - {cidr}")
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except Exception as e:
        core.print_error(f"CIDR invalide: {e}")
        return

    hosts = network.num_addresses
    usable, first, last = host_bounds(network)

    data = {
        "network": str(network.network_address),
        "broadcast": str(network.broadcast_address),
        "prefix": network.prefixlen,
        "hosts_total": hosts,
        "hosts_usable": usable,
        "first_host": first,
        "last_host": last,
    }
    for k, v in data.items():
        core.print_result(k, str(v))
    core.ask_save(f"netblock_{cidr.replace('/', '_')}", data)

