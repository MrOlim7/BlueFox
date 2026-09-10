"""Small validation helpers shared by retained tool entrypoints."""
import ipaddress


def response_object(response, source):
    if response.status_code != 200:
        raise ValueError(f"{source}: HTTP {response.status_code}, résultat indisponible")
    try:
        data = response.json()
    except ValueError:
        raise ValueError(f"{source}: JSON invalide") from None
    if not isinstance(data, dict):
        raise ValueError(f"{source}: objet JSON attendu")
    return data


def host_bounds(network):
    """Count and endpoints with ipaddress.hosts semantics, without iteration."""
    first = int(network.network_address)
    last = int(network.broadcast_address)
    if network.num_addresses > 2:
        first += 1
        if network.version == 4:
            last -= 1
    address = ipaddress.IPv4Address if network.version == 4 else ipaddress.IPv6Address
    return last - first + 1, str(address(first)), str(address(last))


def port_range(start, end):
    start, end = int(start), int(end)
    if not 1 <= start <= end <= 65535:
        raise ValueError("Plage de ports invalide : 1 <= début <= fin <= 65535 requis")
    return range(start, end + 1)


def parse_ports(value):
    ports = set()
    for part in value.replace(" ", "").split(","):
        bounds = part.split("-", 1)
        ports.update(port_range(bounds[0], bounds[-1]))
    return sorted(ports)
