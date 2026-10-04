#!/usr/bin/env python3
"""Create artificial offline inputs. These are not historical observations."""
import argparse
import datetime as dt
import json
from pathlib import Path


def generate(root):
    root.mkdir(parents=True, exist_ok=True)
    def write(name, value):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    def jsonl(name, rows):
        write(name, ''.join(json.dumps(row)+'\n' for row in rows))
    start = dt.datetime(2026,8,24,tzinfo=dt.timezone.utc)
    tasks = [dict(kind='task', ts=(start+dt.timedelta(days=i)).isoformat(), rework=(i%3==0), group='group-'+str(i//3),
                  declared='main', actual='main' if i%3 else 'cheap') for i in range(12)]
    tasks.append(dict(kind='task',ts=start.isoformat(),rework=None,group='group-unknown'))
    jsonl('tasks.jsonl', tasks)
    jsonl('gates.jsonl', [dict(ts=start.isoformat(),event=e) for e in ('block','override','write')])
    jsonl('advice.jsonl', [dict(ts=start.isoformat(),event='trigger')])
    jsonl('probes.jsonl', [dict(ts=start.isoformat(),ok=True)])
    write('inventory.md', '# inventory '+start.isoformat()+'\n')
    write('limits.conf', 'THRESHOLD = 3\nRESOURCE = 2\n')
    write('rules.txt', 'Synthetic rule: preserve the measurement boundary.\n')
    write('registration.json', '{"hooks": ["synthetic-hook"]}\n')
    write('lessons.txt', 'Synthetic producer input.\n')
    write('routing.md', '| Shape | Route |\n|---|---|\n| **alpha** (criterion) | main |\n| **beta** (criterion) | cheap |\n| **gamma** | coding-lane |\n')
    write('goals/done.md', '# Synthetic goal\nstatus: done\nshape: alpha\ndone_criteria:\ntasks:\n  - route: main\n  - route: cheap\nchangelog:\n  - complete\n')
    write('goals/active.md', '# Synthetic goal\nstatus: in_progress\ntasks:\n  - route: coding-lane\n')
    write('goals/unknown.md', '# Synthetic goal\ntasks:\n  - route: unknown\n')
    blocks = {
        'text':[dict(type='text',text='synthetic text must not be exported')],
        'work':[dict(type='tool_use',name='shell',input=dict(command='echo fixture'))],
        'plan':[dict(type='tool_use',name='write',input=dict(file_path='synthetic/plans/example.md'))],
        'route':[dict(type='tool_use',name='read',input=dict(file_path='synthetic/routing.md'))],
        'review':[dict(type='tool_use',name='shell',input=dict(command='review-command'))],
        'question':[dict(type='tool_use',name='question',input={})],
        'closeout':[dict(type='tool_use',name='write',input=dict(file_path='synthetic/worklog.md'))]
    }
    for name, buckets in [('first',['text','work','plan','route','review','question','closeout','text']),
                          ('second',['route','review','closeout','plan','text','work'])]:
        jsonl('sessions/'+name+'.jsonl', [dict(type='assistant',sessionId='synthetic-identity',message=dict(
            model='synthetic-model',usage={'output_tokens':i+1}, content=blocks[b])) for i,b in enumerate(buckets)])
    jsonl('audit.jsonl',[dict(type='assistant',message={'content':[dict(type='tool_use',name='agent',input={})]}) for _ in range(30)])
    write('judge.json',json.dumps({'items':[dict(n=i,tier='CHEAP',verdict='WASTE' if i<=3 else 'OK',reason='fixture') for i in range(1,31)]},indent=2)+'\n')
    stamp = '2026-09-22T12:00:00Z'
    jsonl('triggers.jsonl',[dict(session='example',ts=stamp,event='trigger')])
    jsonl('advisory/example.jsonl',[dict(timestamp='2026-09-22T12:00:01Z',message={'content':[dict(type='tool_use',name='search') ]})])
    jsonl('advisory/example/child.jsonl',[dict(timestamp=stamp,message={'content':'ADVICE'}),
        dict(timestamp='2026-09-22T12:00:01Z',message={'content':[dict(type='tool_use',name='search')]})])
    print('synthetic fixtures written')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    generate(parser.parse_args().out)
