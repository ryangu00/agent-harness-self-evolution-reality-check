#!/usr/bin/env python3
"""Freeze named effective parameters and hashes; check before re-freezing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from common import atomic_json, freeze, now, state_argument


def digest(data):
    return hashlib.sha256(data).hexdigest()[:16]


def snapshot(config, root):
    knobs, files, missing = {}, {}, []
    for spec in config['knobs']:
        try:
            text = (root/spec['file']).read_text()
            match = re.search(spec['regex'], text, re.M | re.S)
            if not match or not match.group(1):
                raise ValueError('required extraction failed')
            default = match.group(1)
            value = os.environ.get(spec.get('env', ''), default)
            knobs[spec['name']] = {'default': default, 'effective': value}
        except (OSError, ValueError, IndexError):
            missing.append(spec['name'])
    for spec in config.get('hashes', []):
        try:
            value = digest((root/spec['file']).read_bytes())
        except OSError:
            value = None
            if spec.get('required', True):
                missing.append(spec['name'])
        if spec.get('required', True):
            knobs[spec['name']] = value
        else:
            files[spec['name']] = value
    return dict(ts=now().isoformat(timespec='seconds'), knobs=knobs, files=files, missing=missing)


def changed(reference, current):
    return sorted(k for k in reference['knobs'].keys() | current['knobs'].keys()
                  if reference['knobs'].get(k) != current['knobs'].get(k))


def selftest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'limits.conf').write_text('THRESHOLD = 3\nRESOURCE = 2\n')
        (root/'rules.txt').write_text('synthetic rules\n')
        (root/'registration.json').write_text('{}\n')
        config = dict(knobs=[dict(name='threshold',file='limits.conf',regex=r'THRESHOLD = (\d+)')],
                      hashes=[dict(name='rules',file='rules.txt'),dict(name='registration',file='registration.json')])
        before = snapshot(config, root)
        assert not before['missing']
        (root/'limits.conf').write_text('THRESHOLD = 2\nRESOURCE = 3\n')
        assert changed(before, snapshot(config, root)) == ['threshold']
    print('knob-invariants selftest PASSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--root', type=Path, default=Path('.'))
    for flag in ('snapshot','check','freeze','force','selftest'):
        parser.add_argument('--'+flag, action='store_true')
    state_argument(parser)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.config:
        parser.error('--config is required')
    current = snapshot(json.loads(args.config.read_text()), args.root)
    if current['missing']:
        print('BLOCKED: missing required fields: '+ ', '.join(current['missing']))
        return 2
    frozen = args.state_dir/'knobs-frozen.json'
    if args.check:
        try:
            reference = json.loads(frozen.read_text())
        except (OSError, ValueError):
            print('BLOCKED: no readable frozen snapshot')
            return 2
        diff = changed(reference, current)
        if diff:
            print('CHANGED: '+', '.join(diff))
            return 1
        if reference.get('files') != current['files']:
            print('NOTE: informational file hashes changed')
        print('CLEAN: named parameters and required hashes match')
    if args.freeze:
        try:
            freeze(frozen, current, args.force)
        except FileExistsError:
            print('REFUSED: frozen snapshot already exists')
            return 3
    if args.snapshot or args.freeze:
        atomic_json(args.state_dir/'knobs-current.json', current)
        print('snapshot written')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
