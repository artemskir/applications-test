import hashlib
from pathlib import Path
from . import SPEC_VERSION
from .models import FieldResult, RowResult, NormalizationError, failure
from . import phone, dates, names
from .deduplicate import apply
from .reader import read_rows, validate_archive
from .report import write_report
from .invariants import validate_rows, verify_report
from .preservation import restore_bytes
from .files import checked_paths, stage_for, publish, cleanup


def snapshot_file(path, limit):
    with path.open('rb') as stream:
        snapshot = stream.read(limit + 1)
    if len(snapshot) > limit:
        raise NormalizationError('INPUT_LIMIT', 'Превышен --max-input-bytes.', 5)
    return snapshot


def source_result(cell):
    if cell.metadata.get('parse_issue') == 'CELL_NUMERIC_INVALID':
        return failure(cell, 'CELL_NUMERIC_INVALID')
    if cell.kind == 'f':
        return failure(cell, 'FIELD_FORMULA')
    if cell.kind == 'e':
        return failure(cell, 'FIELD_EXCEL_ERROR')
    return FieldResult(cell, canonical=cell.value, display=cell.value)


def unchanged(source, snapshot):
    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != hashlib.sha256(snapshot).hexdigest():
        raise NormalizationError('INPUT_CHANGED', 'Исходник изменился во время обработки; результат не опубликован.', 3)


def normalize(input_path, output_path, sheet=None, max_input_bytes=104857600, max_uncompressed_bytes=536870912, max_rows=1048575):
    source, destination = checked_paths(input_path, output_path)
    snapshot = snapshot_file(source, max_input_bytes)
    raw_rows, selection = read_rows(snapshot, sheet, max_uncompressed_bytes, max_rows)
    rows = [RowResult(raw, [names.analyze(raw.cells[0]), phone.analyze(raw.cells[1]), dates.analyze(raw.cells[2]), source_result(raw.cells[3])]) for raw in raw_rows]
    groups = apply(rows)
    validate_rows(rows)
    stage = None
    try:
        stage = stage_for(destination)
        counts = write_report(stage, rows, groups, snapshot, source, selection)
        verify_report(stage, rows, snapshot, counts)
        unchanged(source, snapshot)
        publish(stage, destination)
        return {'output': str(destination), 'spec_version': SPEC_VERSION, **counts}
    finally:
        cleanup(stage, destination)


def restore(input_path, output_path, max_input_bytes=104857600, max_uncompressed_bytes=536870912):
    source, destination = checked_paths(input_path, output_path)
    snapshot = snapshot_file(source, max_input_bytes)
    archive, _ = validate_archive(snapshot, max_uncompressed_bytes)
    archive.close()
    original, run = restore_bytes(snapshot)
    stage = None
    try:
        stage = stage_for(destination)
        with stage.open('wb') as stream:
            stream.write(original)
        unchanged(source, snapshot)
        publish(stage, destination)
        return {'output': str(destination), 'sha256': run['sha256'], 'byte_count': len(original)}
    finally:
        cleanup(stage, destination)
