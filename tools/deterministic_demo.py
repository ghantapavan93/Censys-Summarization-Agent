import json
import os
import sys

# Ensure project root is on sys.path for 'backend' package resolution
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.summarizer_llm import deterministic_summary
from backend.services.input_normalizer import normalize_input
from backend.services.ingest import canonicalize_records


def main():
    with open('examples/hosts_dataset.json', 'r', encoding='utf-8') as f:
        payload = json.load(f)

    norm = normalize_input(payload)
    recs = canonicalize_records(norm.get('raw_records') or [], field_map=None)

    # Convert pydantic models to dicts if needed
    records = []
    for r in recs:
        if hasattr(r, 'model_dump'):
            records.append(r.model_dump())
        elif hasattr(r, 'dict'):
            records.append(r.dict())
        else:
            records.append(r)

    res = deterministic_summary(records)
    print('OVERVIEW:\n', res.get('overview'))
    print('\nHIGHLIGHTS:', res.get('highlights'))
    print('\nSEVERITY MATRIX:', res.get('severity_matrix'))
    print('\nTOP PORTS:', res.get('top_ports'))
    print('\nASSETS BY COUNTRY:', res.get('assets_by_country'))
    print('\nCLUSTERS (first 5):', res.get('clusters', [])[:5])
    risks = res.get('key_risks', [])
    print(f"\nRISKS ({len(risks)}):")
    for r in risks[:5]:
        print('-', r.get('title'), '|', r.get('severity'), '| score', r.get('risk_score'), '| CVEs', ','.join(r.get('related_cves', [])))


if __name__ == '__main__':
    main()
