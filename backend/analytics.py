from collections import Counter
from typing import List, Dict

from .schemas import Host, DatasetInsights


def _top_k_dict(counter: Counter, k: int = 10) -> List[Dict[str, int]]:
    """Convert a Counter into a list of single-key dicts sorted by count desc."""
    return [{str(value): count} for value, count in counter.most_common(k)]


def generate_insights(hosts: List[Host], k: int = 10) -> DatasetInsights:
    """Aggregate dataset-wide insights from a list of Host models.

    Returns lists of single-key dictionaries to match tests' expected shape.
    """
    ports: Counter = Counter()
    protocols: Counter = Counter()
    software: Counter = Counter()
    asns: Counter = Counter()
    countries: Counter = Counter()

    for h in hosts or []:
        # Countries
        if getattr(h, "location", None) and getattr(h.location, "country", None):
            countries[str(h.location.country)] += 1

        # ASNs: prefer name if present, else ASN number
        if getattr(h, "autonomous_system", None):
            name = getattr(h.autonomous_system, "name", None)
            asn_no = getattr(h.autonomous_system, "asn", None)
            if name:
                asns[str(name)] += 1
            elif asn_no is not None:
                asns[str(asn_no)] += 1

        # Services
        for s in getattr(h, "services", []) or []:
            if getattr(s, "port", None) is not None:
                ports[str(s.port)] += 1
            if getattr(s, "protocol", None):
                # normalize protocol to lower-case for consistent counting
                protocols[str(s.protocol).lower()] += 1
            if getattr(s, "software", None):
                for soft in s.software or []:
                    prod = getattr(soft, "product", None)
                    if prod:
                        software[str(prod)] += 1

    return DatasetInsights(
        top_ports=_top_k_dict(ports, k),
        top_protocols=_top_k_dict(protocols, k),
        top_software=_top_k_dict(software, k),
        top_asns=_top_k_dict(asns, k),
        countries=_top_k_dict(countries, k),
    )


# Backwards-compat helper name used by older imports
derive_dataset_insights = generate_insights
