import os
from pathlib import Path
import tempfile
from .models import NormalizationError


def checked_paths(input_path, output_path):
    source, destination = Path(input_path).resolve(), Path(output_path).absolute()
    if source == destination.resolve() or destination.exists() or destination.is_symlink():
        raise NormalizationError('OUTPUT_EXISTS', 'Вход и выход совпадают либо выход уже существует; перезапись запрещена.', 3)
    if source.suffix.lower() != '.xlsx' or destination.suffix.lower() != '.xlsx':
        raise NormalizationError('INPUT_INVALID', 'Вход и выход должны иметь расширение .xlsx.')
    if not source.is_file():
        raise NormalizationError('IO_ERROR', 'Входной файл не найден.', 3)
    return source, destination


def stage_for(destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.normalize-', suffix='.xlsx', dir=destination.parent)
    os.close(fd)
    return Path(name)


def publish(stage, destination):
    # Both operations are atomic and refuse an existing name, including a race.
    if os.name == 'nt':
        os.rename(stage, destination)
    else:
        os.link(stage, destination)
        stage.unlink()


def cleanup(stage, destination):
    if stage is not None and stage.parent.resolve() == destination.parent.resolve() and stage.name.startswith('.normalize-'):
        stage.unlink(missing_ok=True)
