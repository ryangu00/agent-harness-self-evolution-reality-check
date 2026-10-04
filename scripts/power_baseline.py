#!/usr/bin/env python3
"""Pooled task baseline, complete calendar weeks, Wilson interval and power."""
import argparse
import datetime as dt
import json
import math
import random
from pathlib import Path
from common import atomic_json, freeze, now as current_time, parse_time, state_argument
from power_table_and_icc import n_per_arm, raw_n_per_arm


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(max(0, center - half), 4), round(min(1, center + half), 4)]


def calendar_weeks(now, weeks):
    if weeks <= 0:
        raise ValueError('weeks must be positive')
    monday = (now - dt.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    result = []
    for i in range(weeks, 0, -1):
        start = monday - dt.timedelta(weeks=i)
        year, week, _ = start.isocalendar()
        result.append((f'{year}-W{week:02d}', start, start + dt.timedelta(weeks=1)))
    return result


def build(rows, weeks=8, now=None, effect=0.05):
    now = now or current_time()
    calendar = calendar_weeks(now, weeks)
    start, end = calendar[0][1], calendar[-1][2]
    selected, unknown, future = [], 0, 0
    for row in rows:
        stamp = parse_time(row.get('ts'))
        if stamp is None:
            unknown += 1
        elif row.get('future') or stamp > now:
            future += 1
        elif start <= stamp < end:
            selected.append((stamp, row))
    tasks = [r for _, r in selected if r.get('kind') == 'task']
    yes = sum(r.get('rework') is True for r in tasks)
    no = sum(r.get('rework') is False for r in tasks)
    labelled = yes + no
    p = round(yes / labelled, 4) if labelled else None
    pooled = dict(tasks=len(tasks), labeled=labelled, unknown_label=len(tasks)-labelled,
                  rework=yes, rework_rate=p, rework_ci95_wilson=wilson(yes, labelled))
    weekly = {}
    for label, left, right in calendar:
        group = [r for stamp, r in selected if left <= stamp < right and r.get('kind') == 'task']
        rework = sum(r.get('rework') is True for r in group)
        count = sum(isinstance(r.get('rework'), bool) for r in group)
        weekly[label] = dict(tasks=len(group), labeled=count, rework_rate=round(rework/count, 4) if count else None)
    values = [v['rework_rate'] for v in weekly.values() if v['rework_rate'] is not None]
    boot = None
    if len(values) >= 2:
        rng = random.Random(0)
        means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(1000))
        boot = dict(weekly_mean=round(sum(values)/len(values), 4),
                    ci95_of_weekly_mean=[round(means[25], 4), round(means[975], 4)],
                    n_weeks=len(values), note='Interval of the weekly mean, not a prediction band')
    per_week = labelled / weeks
    n = n_per_arm(p, effect) if p is not None and p > effect and per_week > 0 else None
    return dict(ts=now.isoformat(timespec='seconds'),
                window=dict(weeks=weeks, start=start.isoformat(), end=end.isoformat(), complete_calendar_weeks=True),
                excluded=dict(unknown_ts=unknown, future_ts=future), pooled=pooled, weekly=weekly,
                weekly_bootstrap=boot, labeled_tasks_per_week=round(per_week, 1), min_effect_rework=effect,
                n_per_arm=n, weeks_needed_per_arm=math.ceil(raw_n_per_arm(p, effect)/per_week) if n else None,
                weeks_needed_note='Independent tasks; alpha .05 two-sided; power .8' if n else 'not estimable')


def selftest():
    anchor = parse_time('2026-09-22T12:00:00Z')
    calendar = calendar_weeks(anchor, 8)
    rows = []
    for _, start, _ in calendar:
        rows.extend(dict(kind='task', ts=start.isoformat(), rework=i < 6) for i in range(20))
        rows.append(dict(kind='task', ts=start.isoformat(), rework=None))
    rows.extend([dict(kind='task', ts=None, rework=True),
                 dict(kind='task', ts=(anchor + dt.timedelta(days=1)).isoformat(), rework=True)])
    baseline = build(rows, now=anchor)
    assert baseline['pooled']['labeled'] == 160
    assert baseline['pooled']['unknown_label'] == 8
    assert baseline['pooled']['rework_rate'] == 0.3
    assert baseline['excluded'] == dict(unknown_ts=1, future_ts=1)
    assert len(baseline['weekly']) == 8
    assert build([], now=anchor)['weeks_needed_per_arm'] is None
    assert n_per_arm(0.3713, 0.05) == 1419
    print('power-baseline selftest PASSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path)
    parser.add_argument('--weeks', type=int, default=8)
    parser.add_argument('--now', type=parse_time)
    parser.add_argument('--effect', type=float, default=0.05)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--table', action='store_true')
    parser.add_argument('--selftest', action='store_true')
    state_argument(parser)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.events:
        parser.error('--events is required')
    rows = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        parser.error('events must be JSON objects')
    baseline = build(rows, args.weeks, args.now, args.effect)
    if args.freeze:
        try:
            freeze(args.state_dir / ('baseline-frozen-' + baseline['ts'][:10] + '.json'), baseline, args.force)
        except FileExistsError:
            print('REFUSED: frozen baseline already exists')
            return 3
    atomic_json(args.state_dir / 'baseline-latest.json', baseline)
    print(json.dumps(baseline, indent=2))
    if args.table:
        p = baseline['pooled']['rework_rate']
        for effect in (0.05, 0.10, 0.15, 0.20):
            print(f'effect={effect:.2f} n_per_arm={n_per_arm(p, effect) if p is not None and p > effect else "not estimable"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
