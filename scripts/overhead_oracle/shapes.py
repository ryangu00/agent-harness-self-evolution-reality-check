#!/usr/bin/env python3
"""Aggregate a goal inventory; never emit titles, excerpts, paths or IDs."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from declared_actual import normalize


def section_lines(text, word):
    lines, active = [], False
    for line in text.splitlines():
        if re.match(r'^\s*#{1,6}\s*'+word+r'\b', line, re.I) or re.match(r'^\s*'+word+r'\s*:', line, re.I):
            active = True
            continue
        if active and (re.match(r'^\s*#{1,6}\s+', line) or re.match(r'^\s*[A-Za-z_][\w -]*\s*:', line)):
            active = False
        if active:
            lines.append(line)
    return lines


def inventory(goals, routing):
    statuses, routes, completed = Counter(), Counter(), Counter()
    tasks = goals_count = done_criteria = changes = 0
    shape_rows = [m.group(1).strip() for line in Path(routing).read_text().splitlines()
                  if (m := re.match(r'^\s*\|\s*\*\*(.+?)\*\*', line))]
    for path in sorted(Path(goals).glob('*.md')):
        text = path.read_text()
        goals_count += 1
        match = re.search(r'^\s*status\s*:\s*(.*?)\s*$', text, re.I | re.M)
        status = re.sub(r'\s*#.*$', '', match.group(1)).strip().lower() if match else 'unknown'
        status = status if status in ('done','in_progress','blocked','parked','unknown') else 'unknown'
        statuses[status] += 1
        tasks += sum(bool(re.match(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)', line)) for line in section_lines(text, 'tasks'))
        for match in re.finditer(r'route\s*:\s*([^\s,;)}\]]+)', text, re.I):
            routes[normalize(match.group(1).strip('` '))] += 1
        changes += sum(line.startswith('  - ') for line in section_lines(text, 'changelog'))
        done_criteria += bool(re.search('done_criteria', text, re.I))
        if status == 'done':
            # Reader-owned metadata; historical shape assignments are not supplied.
            found = re.search(r'^shape:\s*(.+)$', text, re.M)
            if found and found.group(1).strip() in shape_rows:
                completed[found.group(1).strip()] += 1
    return dict(contains_text=False, goals=goals_count, tasks=tasks, shape_rows=len(shape_rows),
                shapes_with_five_completed_precedents=sum(n >= 5 for n in completed.values()),
                summary=dict(status=dict(statuses), routes=dict(routes), done_count=done_criteria, changelog_entries=changes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('goals','routing','out'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    Path(args.out).write_text(json.dumps(inventory(args.goals,args.routing), indent=2)+'\n')


if __name__ == '__main__':
    main()
