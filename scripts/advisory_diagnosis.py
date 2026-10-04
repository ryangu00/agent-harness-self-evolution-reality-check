#!/usr/bin/env python3
"""Attribute advice to its receiving transcript, including nested transcripts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
from common import atomic_json, now, parse_time, state_argument


def read_events(path, marker):
    events = []
    for raw in path.read_text().splitlines():
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        stamp = parse_time(obj.get('timestamp'))
        if not stamp:
            continue
        if marker in raw:
            events.append((stamp.timestamp(), 'advice', ''))
        content = (obj.get('message') or {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use':
                events.append((stamp.timestamp(), 'use', block.get('name', '')))
            elif block.get('type') == 'tool_result' and block.get('is_error'):
                events.append((stamp.timestamp(), 'error', ''))
    return events


def diagnose(triggers, sessions, marker, search_tools, window=15):
    rows = []
    for trigger in triggers:
        stamp = parse_time(trigger.get('ts'))
        # Synthetic or reader-owned lookup keys never appear in the output.
        session = str(trigger.get('session', ''))
        if not session or Path(session).name != session or session in ('.', '..'):
            rows.append({'verdict': 'no-transcript'})
            continue
        top = sessions / (session + '.jsonl')
        paths = ([top] if top.is_file() else []) + sorted((sessions/session).rglob('*.jsonl'))
        if not paths or not stamp:
            rows.append({'verdict': 'no-transcript'})
            continue
        t = stamp.timestamp()
        receivers = []
        for path in paths:
            events = read_events(path, marker)
            marks = [e for e in events if e[1] == 'advice' and -5 <= e[0] - t <= 30]
            if marks:
                receivers.append((events, min(marks, key=lambda e: abs(e[0]-t))))
        if len(receivers) != 1:
            rows.append({'verdict': 'unresolved-receiver'})
            continue
        events, advice = receivers[0]
        # Count after actual receipt, never a sibling's search or a pre-advice call.
        start_index = events.index(advice) + 1
        segment = []
        for event in events[start_index:]:
            if event[1] == 'advice':
                break
            if event[0] >= advice[0]:
                segment.append(event)
        uses = [e for e in segment if e[1] == 'use']
        positions = [i for i, e in enumerate(uses, 1) if e[2] in search_tools]
        inside = bool(positions and positions[0] <= window)
        verdict = 'complied-in-window' if inside else 'late' if positions else 'ignored' if uses else 'ended-at-trigger'
        rows.append(dict(verdict=verdict, tool_calls_after=len(uses), searched_in_window=inside,
                         searched_later=bool(positions), first_search_position=positions[0] if positions else None,
                         errors_after=sum(e[1] == 'error' for e in segment)))
    counts = Counter(r['verdict'] for r in rows)
    return dict(ts=now().isoformat(timespec='seconds'), triggers=len(rows), window=window,
                with_transcript=sum(r['verdict'] not in ('no-transcript', 'unresolved-receiver') for r in rows),
                counts=dict(counts), complied_in_window=counts['complied-in-window'],
                definition='Any search in the receiving agent window; upper bound, not a causal effect', rows=rows)


def selftest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        cases = [('early', ['search']), ('late', ['work']*20+['fetch']),
                 ('ignored', ['work']), ('ended', []), ('nested', ['search'])]
        for name, tools in cases:
            target = root / (name + '.jsonl')
            if name == 'nested':
                (root/name).mkdir()
                target = root/name/'child.jsonl'
                (root/(name+'.jsonl')).write_text('')
            lines = [dict(timestamp='2026-09-22T12:00:00Z', message={'content': 'ADVICE'})]
            lines.extend(dict(timestamp='2026-09-22T12:00:01Z', message={'content':[dict(type='tool_use', name=tool)]}) for tool in tools)
            target.write_text('\n'.join(json.dumps(r) for r in lines)+'\n')
        triggers = [dict(session=s, ts='2026-09-22T12:00:00Z') for s in ['early','late','ignored','ended','missing','nested']]
        report = diagnose(triggers, root, 'ADVICE', ['search','fetch'])
        assert report['complied_in_window'] == 2
        assert report['counts'] == {'complied-in-window':2,'late':1,'ignored':1,'ended-at-trigger':1,'no-transcript':1}
    print('advisory-diagnosis selftest PASSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--triggers', type=Path)
    parser.add_argument('--sessions', type=Path)
    parser.add_argument('--marker')
    parser.add_argument('--search-tool', action='append')
    parser.add_argument('--window', type=int, default=15)
    parser.add_argument('--selftest', action='store_true')
    state_argument(parser)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not all((args.triggers, args.sessions, args.marker, args.search_tool)):
        parser.error('--triggers, --sessions, --marker and --search-tool are required')
    triggers = [json.loads(line) for line in args.triggers.read_text().splitlines() if line.strip()]
    report = diagnose(triggers, args.sessions, args.marker, args.search_tool, args.window)
    atomic_json(args.state_dir/'diagnosis.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
