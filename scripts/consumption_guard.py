#!/usr/bin/env python3
"""Stop production when consumption evidence expires; configuration is JSON."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from common import atomic_json, now, parse_time, state_argument


def mtime(path, at):
    try:
        stamp = dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        return stamp if stamp <= at + dt.timedelta(minutes=5) else None
    except OSError:
        return None


def evidence(spec, root, at):
    candidates = []
    for relative in spec['paths']:
        path = root / relative
        if spec['kind'] == 'mtime':
            candidates.append(mtime(path, at))
        elif spec['kind'] == 'jsonl-ts':
            try:
                stamps = []
                for line in path.read_text().splitlines():
                    try:
                        stamp = parse_time(json.loads(line).get('ts'))
                    except (ValueError, AttributeError):
                        continue
                    if stamp:
                        stamps.append(stamp)
                # Preserve the source's fallback when no content timestamp parses.
                candidates.append(max(stamps) if stamps else mtime(path, at))
            except OSError:
                pass
        elif spec['kind'] == 'marker':
            files = sorted(path.glob(spec.get('glob', '*'))) if path.is_dir() else [path]
            for file in files:
                if not file.is_file():
                    continue
                for match in re.finditer(spec['pattern'], file.read_text()):
                    stamp = parse_time(match.group(1))
                    if stamp:
                        candidates.append(stamp)
        else:
            raise ValueError('unknown evidence kind')
    # No future evidence can resume a line accidentally.
    return [s for s in candidates if s and s <= at + dt.timedelta(minutes=5)]


def evaluate(config, root, at=None):
    at = at or now()
    threshold = config.get('threshold_days', 14)
    state = {'_ts': at.isoformat(timespec='seconds'), '_threshold_days': threshold}
    for name, spec in config['lines'].items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise ValueError('line names must be simple labels')
        candidates = evidence(spec, root, at)
        touch = mtime(root / 'consumed' / name, at)
        if touch:
            candidates.append(touch)
        last = max(candidates) if candidates else None
        days = (at - last).days if last else None
        state[name] = dict(paused=days is None or days >= spec.get('threshold_days', threshold),
                           last_consumed=last.isoformat(timespec='seconds') if last else None, days=days)
    return state


def selftest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config = {'threshold_days': 14, 'lines': {'proposals': {'kind': 'marker',
                  'paths': ['proposals.md'], 'pattern': r'APPROVED (\d{4}-\d\d-\d\d)'}}}
        (root / 'proposals.md').write_text('APPROVED 2026-99-99\nAPPROVED 2026-01-02\n')
        assert evaluate(config, root)['proposals']['paused']
        cfg = root / 'config.json'
        cfg.write_text(json.dumps(config))
        base = [sys.executable, __file__, '--config', str(cfg), '--state-dir', str(root)]
        subprocess.run(base, check=True, capture_output=True)
        reader = [ '/bin/bash', str(Path(__file__).with_name('is_paused.sh')), 'proposals', str(root / 'paused.json')]
        assert subprocess.run(reader, capture_output=True).returncode == 0
        subprocess.run(base + ['--consume', 'proposals'], check=True, capture_output=True)
        assert subprocess.run(reader, capture_output=True).returncode == 1
    print('consumption-guard selftest PASSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--consume')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--selftest', action='store_true')
    state_argument(parser)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.config:
        parser.error('--config is required')
    config = json.loads(args.config.read_text())
    # Validate the whole config before writing consumption evidence.
    evaluate(config, args.state_dir)
    if args.consume:
        if args.consume not in config['lines']:
            parser.error('unknown line')
        touch = args.state_dir / 'consumed' / args.consume
        touch.parent.mkdir(parents=True, exist_ok=True)
        touch.write_text(now().isoformat() + '\n')
    state = evaluate(config, args.state_dir)
    if not args.status or args.consume:
        atomic_json(args.state_dir / 'paused.json', state)
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    main()
