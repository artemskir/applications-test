"""Offline QA rejects missing/tampered source data without performing network I/O."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.resource_sources import load_sources, checked_payload


class ResourceDependencies(unittest.TestCase):
    def test_offline_reader_rejects_missing_or_changed_payload(self):
        payload=b'fixed source bytes\n'
        item={'file':'test.txt','bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('research.resource_sources.locked_sources',return_value=[item]), \
                 patch('research.resource_sources.urlopen',side_effect=AssertionError('Offline access tried network')):
                with self.assertRaises(FileNotFoundError): load_sources(root)
                (root/'test.txt').write_bytes(payload)
                self.assertEqual(load_sources(root),{'test.txt':payload.decode('utf-8')})
                (root/'test.txt').write_bytes(b'changed source!!!\n')
                with self.assertRaisesRegex(ValueError,'hash mismatch'): load_sources(root)

    def test_digest_rejects_equal_length_replacement(self):
        item={'file':'source.txt','bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()}
        with self.assertRaisesRegex(ValueError,'hash mismatch'): checked_payload(item,b'abd')
