#!/usr/bin/env python3
"""Offline action classification, pluggable judgement and audit predicates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tempfile
from common import now, state_argument

# This is a public interface skeleton, not the original judge prompt.
JUDGE_PROMPT = '''Apply the reader-supplied routing rules to each numbered action.
Return items with n, tier (CHEAP or MAIN), verdict (OK, WASTE or RISK), reason.
WASTE means independent delegable work done inline. RISK means inappropriate
cheap-lane execution. Subscription sub-agents are not offloads. Dispatch setup,
reading one's dispatched output, acceptance, and small integration diagnostics
are orchestration exceptions. Do not infer policy from a handler alone.
'''


def classify(tool, inputs, config):
    if tool in config['shell_tools']:
        command = str(inputs.get('command', ''))
        pattern = r'(?:^|[\s;&|])(?:'+'|'.join(re.escape(x) for x in config['dispatch_commands'])+r')\b'
        return 'cheap-dispatch' if re.search(pattern, command) else 'executor-did-it-inline'
    if tool in config['agent_tools']:
        return 'subscription-sub-agent'
    if tool in config['workflow_tools']:
        return 'orchestration'
    if tool == config['workflow_agent_tool']:
        return 'workflow-cheap-dispatch' if inputs.get('delegated') else 'workflow-inline-generation'
    return 'executor-did-it-inline'


def parse(path, config, last=60):
    actions = []
    for line in path.read_text().splitlines():
        row = json.loads(line)
        message = row.get('message') or {}
        if row.get('type') != 'assistant' and message.get('role') != 'assistant':
            continue
        content = message.get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                actions.append({'handler': classify(block.get('name'), block.get('input') or {}, config)})
    return actions[-last:]


def pendulums(adherence, cheap_dispatch, waste, inline_workflow_agents=0, workflow_dispatch=0):
    warnings = []
    if adherence >= 80 and cheap_dispatch == 0 and waste > 0:
        warnings.append('PENDULUM')
    if inline_workflow_agents >= 2 and cheap_dispatch + workflow_dispatch == 0:
        warnings.append('PENDULUM-2')
    return warnings


def audit(actions, judge):
    result = judge(actions, JUDGE_PROMPT)
    items = result['items']
    if len(items) != len(actions) or {item.get('n') for item in items} != set(range(1, len(actions)+1)):
        raise ValueError('judge must return exactly one verdict per action')
    counts = Counter()
    for item in items:
        if item.get('verdict') not in ('OK','WASTE','RISK') or item.get('tier') not in ('CHEAP','MAIN'):
            raise ValueError('invalid judge enum')
        action = actions[item['n']-1]
        verdict = 'WASTE' if action['handler'] == 'workflow-inline-generation' else item['verdict']
        counts[verdict] += 1
    handlers = Counter(a['handler'] for a in actions)
    adherence = round(100*(len(actions)-counts['WASTE']-counts['RISK'])/len(actions), 1) if actions else None
    summary = dict(total=len(actions), adherence=adherence, waste=counts['WASTE'], risk=counts['RISK'],
                   cheap_dispatch=handlers['cheap-dispatch'], workflow_dispatch=handlers['workflow-cheap-dispatch'])
    summary['warnings'] = pendulums(adherence, summary['cheap_dispatch'], summary['waste'],
                                   handlers['workflow-inline-generation'], summary['workflow_dispatch']) if actions else []
    return summary


def log_trend(path, row, rule_hash):
    path.parent.mkdir(parents=True, exist_ok=True)
    history = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    stored = dict(row, ts=now().isoformat(timespec='seconds'), rule_hash=rule_hash)
    with path.open('a') as out:
        out.write(json.dumps(stored)+'\n')
    tail = (history+[stored])[-3:]
    # The historical trigger did not know rule versions. Do not cross versions here.
    return (len(tail) == 3 and all(r.get('rule_hash') == rule_hash and
            r.get('adherence') is not None and r['adherence'] < 60 for r in tail))


def selftest():
    actions = [{'handler':'subscription-sub-agent'} for _ in range(30)]
    def stub(actions, prompt):
        return {'items':[dict(n=i, tier='CHEAP', verdict='WASTE' if i <= 3 else 'OK', reason='synthetic')
                         for i in range(1,len(actions)+1)]}
    result = audit(actions, stub)
    assert result['adherence'] == 90 and result['waste'] == 3 and result['warnings'] == ['PENDULUM']
    assert 'PENDULUM-2' in pendulums(14,0,43,43,0)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'trend.jsonl'
        low = dict(result, adherence=14)
        assert not log_trend(path, low, 'synthetic')
        assert not log_trend(path, low, 'synthetic')
        assert log_trend(path, low, 'synthetic')
    print('routing-audit selftest PASSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transcript', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--judge-fixture', type=Path)
    parser.add_argument('--last', type=int, default=60)
    parser.add_argument('--selftest', action='store_true')
    state_argument(parser)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not all((args.transcript, args.config, args.judge_fixture)):
        parser.error('--transcript, --config and --judge-fixture are required')
    config = json.loads(args.config.read_text())
    fixture = json.loads(args.judge_fixture.read_text())
    actions = parse(args.transcript, config, args.last)
    result = audit(actions, lambda actions, prompt: fixture)
    rule_hash = hashlib.sha256((JUDGE_PROMPT+json.dumps(config, sort_keys=True)).encode()).hexdigest()
    result['structural_trigger'] = log_trend(args.state_dir/'trend.jsonl', result, rule_hash)
    result['judge'] = 'synthetic fixture; no API call'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
