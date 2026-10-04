#!/usr/bin/env python3
"""Collect configured sources into a content-keyed append-only event ledger."""
import argparse
from collections import Counter
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import re
import tempfile
from common import atomic_json, now, parse_time, state_argument


def collect(sources, root, since_days=60, at=None):
    at = at or now()
    cutoff = at - dt.timedelta(days=since_days)
    future = at + dt.timedelta(minutes=5)
    events, status, duplicates, seen = [], {}, Counter(), set()
    for spec in sources:
        name, path = spec['name'], root / spec['path']
        st = status[name] = dict(exists=path.is_file(), lines=0, bad=0)
        if not st['exists']:
            continue
        try:
            content = path.read_text()
        except (OSError, UnicodeError):
            st.update(lines=1, bad=1)
            continue
        if spec.get('format') == 'snapshot':
            match = re.search(spec['timestamp_pattern'], content)
            raw_rows = [(content, {'ts': match.group(1) if match else None})]
        else:
            raw_rows = []
            for raw in content.splitlines():
                if not raw.strip():
                    continue
                st['lines'] += 1
                try:
                    row = json.loads(raw)
                    if not isinstance(row, dict):
                        raise ValueError('source row must be an object')
                except ValueError:
                    st['bad'] += 1
                    continue
                raw_rows.append((raw, row))
        for raw, row in raw_rows:
            mapper = spec['kind_mapper']
            kind = mapper if isinstance(mapper, str) else mapper.get(row.get(spec.get('kind_field', 'event')))
            if kind is None:
                continue
            stamp = parse_time(row.get('ts'))
            is_future = bool(stamp and stamp > future)
            if stamp and not is_future and stamp < cutoff:
                continue
            key = name + ':' + hashlib.sha1(raw.encode()).hexdigest()[:20]
            if key in seen:
                duplicates[name] += 1
                continue
            seen.add(key)
            event = dict(src=name, kind=kind, denom=spec.get('denom', kind), key=key,
                         ts=stamp.isoformat(timespec='seconds') if stamp else None, future=is_future)
            if kind == 'task':
                event['rework'] = row.get('rework') if isinstance(row.get('rework'), bool) else None
            if spec.get('gate_produced'):
                event['gate_produced'] = True
            for field in spec.get('fields', []):
                event[field] = row.get(field)
            events.append(event)
    degraded = [name for name, st in status.items() if not st['exists'] or (st['lines'] and st['bad']/st['lines'] > 0.05)]
    return events, dict(ts=at.isoformat(timespec='seconds'), sources=status, degraded=degraded,
                        identical_lines_collapsed=dict(duplicates),
                        unknown_ts=sum(e['ts'] is None for e in events), future_ts=sum(e['future'] for e in events))


def run(config, root, output, since_days=60, at=None):
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.events.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # Include source reads in the lock; no overlapping read-append transactions.
        events, status = collect(config['sources'], root, since_days, at)
        ledger = output / 'events.jsonl'
        seen = set()
        if ledger.exists():
            for line in ledger.read_text().splitlines():
                if line.strip():
                    seen.add(json.loads(line)['key'])
        new = [e for e in events if e['key'] not in seen]
        with ledger.open('a') as out:
            for event in new:
                event['_collected_at'] = now().isoformat(timespec='seconds')
                out.write(json.dumps(event) + '\n')
        status.update(appended=len(new), total=len(seen) + len(new))
        atomic_json(output / 'collect-status.json', status)
        if not status['degraded']:
            (output / 'heartbeat').write_text(now().isoformat(timespec='seconds') + '\n')
    return status


def selftest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / 'tasks.jsonl'
        source.write_text(json.dumps({'ts': now().isoformat(), 'rework': None}) + '\n')
        config = {'sources': [dict(name='tasks', path='tasks.jsonl', kind_mapper='task')]}
        assert run(config, root, root/'state')['appended'] == 1
        assert run(config, root, root/'state')['appended'] == 0
        before = (root/'state/heartbeat').read_bytes()
        source.unlink()
        assert run(config, root, root/'state')['degraded'] == ['tasks']
        assert (root/'state/heartbeat').read_bytes() == before
    print('ledger-collect selftest PASSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--source-root', type=Path, default=Path('.'))
    parser.add_argument('--since-days', type=int, default=60)
    parser.add_argument('--now', type=parse_time)
    parser.add_argument('--selftest', action='store_true')
    state_argument(parser)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.config:
        parser.error('--config is required')
    status = run(json.loads(args.config.read_text()), args.source_root, args.state_dir, args.since_days, args.now)
    print(json.dumps(status, indent=2))
    return 1 if status['degraded'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
