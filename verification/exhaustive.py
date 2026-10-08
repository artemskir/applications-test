"""Complete ordered enumeration, not a random sample or covering array."""
from dataclasses import asdict
from hashlib import sha256
from itertools import product, combinations
import json
from pathlib import Path
from .reference import ALPHABET, evaluate
from .adapter import actual


def check(max_length=3):
    counts = {}; checksum = sha256()
    # Parsing bridge is checked independently of 112945 grouping evaluations.
    for record in ALPHABET:
        assert actual([record], analyze=True) == evaluate([record]), ('parser bridge', record)
    for length in range(max_length+1):
        count = 0
        for indexes in product(range(len(ALPHABET)), repeat=length):
            records = tuple(ALPHABET[i] for i in indexes)
            expected, got = evaluate(records), actual(records)
            if got != expected:
                return {'passed': False, 'counts': counts, 'counterexample': [asdict(r) for r in records],
                        'expected': repr(expected), 'actual': repr(got)}
            checksum.update(bytes(indexes) + b';')
            count += 1
        assert count == 48**length
        counts[str(length)] = count
    # Every 2-way and 3-way interaction of four per-row abstract factors is present.
    factors = [(r.telephone, r.name, r.date, r.source) for r in ALPHABET]
    domains = [set(row[i] for row in factors) for i in range(4)]
    interactions = {}
    for strength in (2, 3):
        expected_count = measured_count = 0
        for indexes in combinations(range(4), strength):
            wanted = set(product(*(domains[i] for i in indexes)))
            covered = {tuple(row[i] for i in indexes) for row in factors}
            assert covered == wanted
            expected_count += len(wanted); measured_count += len(covered)
        interactions[str(strength)] = {'covered': measured_count, 'required': expected_count}
    return {'passed': True, 'alphabet': 48, 'parser_bridge_states': 48, 'counts': counts,
            'total_sequences': sum(counts.values()), 'enumeration_sha256': checksum.hexdigest(),
            'interactions': interactions, 'counterexamples': [], 'scope': 'grouping on abstract fields; length <= 3'}
