"""Sequences of edits, checked after each operation against a fresh independent model."""
from collections import Counter
from hashlib import sha256
from hypothesis import settings, seed, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition, get_state_machine_test
from .reference import ALPHABET, evaluate
from .adapter import actual


def check(seed_value=42, examples=100, steps=30):
    counts = Counter(); lengths = Counter(); trace = sha256()
    class RecordsMachine(RuleBasedStateMachine):
        def __init__(self):
            super().__init__(); self.records = []; counts['programs'] += 1
        @precondition(lambda self: len(self.records) < 12)
        @rule(index=st.integers(0, 47))
        def append(self, index):
            self.records.append(ALPHABET[index]); counts['append'] += 1
        @precondition(lambda self: bool(self.records))
        @rule(position=st.integers(0, 11))
        def remove(self, position):
            self.records.pop(position % len(self.records)); counts['remove'] += 1
        @precondition(lambda self: bool(self.records))
        @rule(position=st.integers(0, 11), index=st.integers(0, 47))
        def replace(self, position, index):
            self.records[position % len(self.records)] = ALPHABET[index]; counts['replace'] += 1
        @precondition(lambda self: len(self.records) > 1)
        @rule()
        def reverse(self):
            self.records.reverse(); counts['reverse'] += 1
        @invariant()
        def contract(self):
            counts['invariant'] += 1; lengths[len(self.records)] += 1
            trace.update(bytes(ALPHABET.index(r) for r in self.records) + b';')
            assert actual(self.records, analyze=True) == evaluate(self.records)
    # Seed the generated @given test itself; decorating a wrapper does not propagate a seed.
    run = seed(seed_value)(get_state_machine_test(RecordsMachine,
                settings=settings(max_examples=examples, stateful_step_count=steps, deadline=None, database=None)))
    run()
    assert counts['invariant'] > 0
    return {'passed': True, 'seed': seed_value, 'example_limit': examples, 'step_limit': steps,
            'calls': dict(counts), 'lengths': dict(lengths), 'trace_sha256':trace.hexdigest()}
