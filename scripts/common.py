"""Shared local state and timestamp helpers; standard library only."""
import datetime as dt
import json
import os
from pathlib import Path
import tempfile


def now():
    return dt.datetime.now().astimezone()


def parse_time(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
            return dt.datetime.fromtimestamp(float(value)).astimezone()
        parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else parsed.astimezone()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(data, out, indent=2, ensure_ascii=True)
            out.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def freeze(path, data, force=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and force:
        # Exclusive backup: a second forced freeze must not replace the first backup.
        backup = path.with_name(path.name + '.prev-' + now().strftime('%Y%m%d%H%M%S%f'))
        with backup.open('xb') as out:
            out.write(path.read_bytes())
        path.unlink()
    with path.open('x') as out:
        json.dump(data, out, indent=2, ensure_ascii=True)
        out.write('\n')


def state_argument(parser):
    parser.add_argument('--state-dir', type=Path, default=Path(os.environ.get('HARNESS_STATE_DIR', '.work/state')))


def config_paths(config, field, root):
    return [Path(root) / p for p in config.get(field, [])]
