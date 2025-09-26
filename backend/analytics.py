from collections import Counter
from typing import List, Dict
from schemas import Host, DatasetInsights

def _top_k(counter, k=10) -> List[Dict[str, int]]:
    return [{"value": v, "count": c} for v, c in counter.most_common(k)]

def derive_dataset_insights(hosts: List[Host]) -> DatasetInsights:
    ports, protos, sw, asns, countries = Counter(), Counter(), Counter(), Counter(), Counter()
    for h in hosts:
        if h.location and h.location.country:
            countries[h.location.country] += 1
        if h.autonomous_system and h.autonomous_system.asn:
            asns[str(h.autonomous_system.asn)] += 1
        for s in (h.services or []):
            if s.port: ports[str(s.port)] += 1
            if s.protocol: protos[s.protocol] += 1
            if s.software:
                for soft in s.software:
                    key = ":".join([x for x in [soft.vendor, soft.product, soft.version] if x])
                    if key:
                        sw[key] += 1
    return DatasetInsights(
        top_ports=_top_k(ports),
        top_protocols=_top_k(protos),
        top_software=_top_k(sw),
        top_asns=_top_k(asns),
        countries=_top_k(countries),
    )
