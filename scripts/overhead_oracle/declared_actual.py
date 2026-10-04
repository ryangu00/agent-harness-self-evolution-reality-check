#!/usr/bin/env python3
"""Compare normalized route enums without exporting row text or identities."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ENUM = {'main', 'main-self', 'coding-lane', 'cheap', 'subscription-sub-agent', 'workflow', 'unknown'}
ALIASES = {'main-inline':'main', 'review-lane':'coding-lane', 'verifier':'subscription-sub-agent', 'cheap-wrapper':'cheap'}


def normalize(value):
    if not isinstance(value, str):
        return 'unknown'
    value = re.sub(r'\([^)]*\)', '', value.lower()).split('+')[0]
    value = re.split(r'->|/|,', value, maxsplit=1)[0].strip()
    value = ALIASES.get(value, value)
    return value if value in ENUM else 'unknown'


def build(ledger, since=None):
    groups = {'same': [], 'differ': [], 'unknown': []}
    pairs, spelling = Counter(), 0
    unparsable = 0
    for line in Path(ledger).read_text().splitlines():
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('row must be object')
        except ValueError:
            unparsable += 1
            continue
        if since and str(row.get('ts',''))[:10] < since:
            continue
        declared, actual = normalize(row.get('declared')), normalize(row.get('actual'))
        if declared == 'unknown' or actual == 'unknown':
            category = 'unknown'
        elif declared == actual:
            category = 'same'
        else:
            category = 'differ'
            pairs[declared+'->'+actual] += 1
        if category == 'same' and row.get('declared') != row.get('actual'):
            spelling += 1
        groups[category].append(row.get('rework'))
    result = dict(total=sum(map(len, groups.values())), unparsable=unparsable, spelling_normalized=spelling,
                  differ_by_pair=dict(pairs), rework_rate={})
    for name, labels in groups.items():
        labelled = [x for x in labels if isinstance(x, bool)]
        result[name] = len(labels)
        result['rework_rate'][name] = sum(labelled)/len(labelled) if labelled else None
    return {'summary':result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--since')
    args = parser.parse_args()
    Path(args.out).write_text(json.dumps(build(args.ledger, args.since), indent=2)+'\n')


if __name__ == '__main__':
    main()
