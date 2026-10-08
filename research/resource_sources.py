"""Explicit preparation and hash-checked offline access to pinned public QA inputs."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'research/resource_sources.lock.json'
MAX_DOWNLOAD = 16 * 1024 * 1024


def locked_sources():
    return json.loads(LOCK.read_text(encoding='utf-8'))['sources']


def checked_payload(item, data):
    if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Resource size/hash mismatch: ' + item['file'])
    data.decode('utf-8')
    return data


def load_sources(directory):
    # This path has no networking, even when the cache is missing.
    return {item['file']: checked_payload(item, (directory / item['file']).read_bytes()).decode('utf-8')
            for item in locked_sources()}


def fetch_sources(directory):
    directory.mkdir(parents=True, exist_ok=False)
    results = []
    for item in locked_sources():
        request = Request(item['url'], headers={'User-Agent':'xlsx-local-qa/1.0'})
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError('Unexpected HTTP status: ' + item['file'])
            data = response.read(MAX_DOWNLOAD + 1)
        if len(data) > MAX_DOWNLOAD:
            raise ValueError('Download size limit: ' + item['file'])
        checked_payload(item, data)
        with (directory / item['file']).open('xb') as stream:
            stream.write(data)
        results.append({'file':item['file'], 'sha256':item['sha256'], 'http_status':200})
    with (directory / 'download.json').open('x', encoding='utf-8') as stream:
        json.dump({'lock_sha256':hashlib.sha256(LOCK.read_bytes()).hexdigest(), 'downloads':results}, stream, indent=2)
    return results
