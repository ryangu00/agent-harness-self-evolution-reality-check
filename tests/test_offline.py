"""Offline behavioral checks. All temporary writes stay beneath TMPDIR."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import advisory_diagnosis as diagnosis
import consumption_guard as guard
import knob_invariants as invariants
import ledger_collect as collector
import power_baseline as baseline
import power_table_and_icc as power
import routing_audit as audit
from common import atomic_json, freeze, now, parse_time


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, script, *args, env=None):
        runner = '/bin/bash' if script.endswith('.sh') else sys.executable
        return subprocess.run([runner,str(ROOT/'scripts'/script),*map(str,args)], capture_output=True, text=True,
                              env=env or dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), cwd=ROOT)

    def healthy(self):
        stamp = now().isoformat()
        (self.root/'heartbeat').write_text(stamp)
        atomic_json(self.root/'paused.json', {'_ts':stamp,'proposals':{'paused':False}})
        atomic_json(self.root/'baseline-latest.json', {'ts':stamp})

    def test_all_script_selftests(self):
        for script in ['power_baseline.py','power_table_and_icc.py','ledger_collect.py',
                       'consumption_guard.py','advisory_diagnosis.py','knob_invariants.py','routing_audit.py']:
            with self.subTest(script=script):
                result = self.cli(script,'--selftest')
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                self.assertIn('selftest PASSED',result.stdout)

    def test_reader_all_uncertain_states(self):
        path = self.root/'paused.json'
        def read():
            return self.cli('is_paused.sh','proposals',path)
        self.assertEqual(read().returncode,0)
        path.write_text('{')
        self.assertEqual(read().returncode,0)
        for age in [dt.timedelta(days=3,seconds=1),dt.timedelta(seconds=-1)]:
            atomic_json(path, {'_ts':(now()-age).isoformat(),'proposals':{'paused':False}})
            self.assertEqual(read().returncode,0)
        atomic_json(path, {'_ts':now().isoformat()})
        self.assertEqual(read().returncode,0)
        atomic_json(path, {'_ts':now().isoformat(),'proposals':{'paused':'false'}})
        self.assertEqual(read().returncode,0)
        atomic_json(path, {'_ts':now().isoformat(),'proposals':{'paused':False}})
        self.assertEqual(read().returncode,1)

    def test_content_time_precedes_mtime_and_future_ignored(self):
        old = now()-dt.timedelta(days=40)
        path = self.root/'labels.jsonl'
        path.write_text(json.dumps({'ts':old.isoformat()})+'\n')
        config = {'lines':{'labels':{'kind':'jsonl-ts','paths':['labels.jsonl']}}}
        self.assertTrue(guard.evaluate(config,self.root)['labels']['paused'])
        path.write_text(json.dumps({'ts':(now()+dt.timedelta(days=3)).isoformat()})+'\n')
        self.assertTrue(guard.evaluate(config,self.root)['labels']['paused'])

    def test_future_mtime_ignored(self):
        path = self.root/'watermark'
        path.write_text('1')
        stamp = (now()+dt.timedelta(days=3)).timestamp()
        os.utime(path,(stamp,stamp))
        config = {'lines':{'labels':{'kind':'mtime','paths':['watermark']}}}
        self.assertTrue(guard.evaluate(config,self.root)['labels']['paused'])

    def test_marker_bad_date_archive_and_immediate_consume(self):
        result = self.cli('consumption_guard.py','--config',ROOT/'configs/consumption.json','--state-dir',self.root)
        self.assertEqual(result.returncode,0,result.stderr)
        archive=self.root/'evidence/archive'
        archive.mkdir(parents=True)
        (archive/'old.md').write_text('APPROVED 2026-99-99\nAPPROVED '+now().date().isoformat()+'\n')
        config=json.loads((ROOT/'configs/consumption.json').read_text())
        self.assertFalse(guard.evaluate(config,self.root)['proposals']['paused'])
        result=self.cli('consumption_guard.py','--config',ROOT/'configs/consumption.json','--state-dir',self.root,'--consume','promotion')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(json.loads((self.root/'paused.json').read_text())['promotion']['paused'])

    def test_collect_dedup_prepend_unknown_and_future(self):
        stamp = now()
        rows=[{'ts':stamp.isoformat(),'rework':None}, {'ts':'bad','rework':'false'},
              {'ts':(stamp+dt.timedelta(days=2)).isoformat(),'rework':True}]
        path=self.root/'tasks.jsonl'
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows+[rows[0]]))
        config={'sources':[{'name':'tasks','path':'tasks.jsonl','kind_mapper':'task'}]}
        out=self.root/'state'
        status=collector.run(config,self.root,out)
        self.assertEqual(status['appended'],3)
        self.assertEqual(status['identical_lines_collapsed'],{'tasks':1})
        self.assertEqual((status['unknown_ts'],status['future_ts']),(1,1))
        events=[json.loads(r) for r in (out/'events.jsonl').read_text().splitlines()]
        self.assertIsNone(events[1]['rework'])
        path.write_text(json.dumps({'ts':stamp.isoformat(),'rework':False})+'\n'+path.read_text())
        self.assertEqual(collector.run(config,self.root,out)['appended'],1)
        self.assertEqual(collector.run(config,self.root,out)['appended'],0)

    def test_missing_and_bad_sources_do_not_refresh_heartbeat(self):
        source=self.root/'source.jsonl'
        source.write_text(json.dumps({'ts':now().isoformat(),'event':'trigger'})+'\n')
        config={'sources':[dict(name='advice',path=source.name,kind_mapper='trigger',gate_produced=True)]}
        out=self.root/'state'
        collector.run(config,self.root,out)
        before=(out/'heartbeat').stat().st_mtime_ns
        events=[json.loads(r) for r in (out/'events.jsonl').read_text().splitlines()]
        self.assertTrue(events[0]['gate_produced'])
        source.write_text(source.read_text()+'not json\n0\n')
        self.assertEqual(collector.run(config,self.root,out)['degraded'],['advice'])
        self.assertEqual((out/'heartbeat').stat().st_mtime_ns,before)
        source.unlink()
        self.assertEqual(collector.run(config,self.root,out)['degraded'],['advice'])
        self.assertEqual((out/'heartbeat').stat().st_mtime_ns,before)

    def test_bad_ratio_threshold(self):
        source=self.root/'source.jsonl'
        valid=json.dumps({'ts':now().isoformat(),'rework':False})+'\n'
        source.write_text(valid*19+'invalid\n')
        config=[dict(name='tasks',path=source.name,kind_mapper='task')]
        self.assertFalse(collector.collect(config,self.root)[1]['degraded'])
        source.write_text(source.read_text()+'invalid\n')
        self.assertTrue(collector.collect(config,self.root)[1]['degraded'])

    def test_baseline_empty_weeks_and_invalid_labels(self):
        anchor=parse_time('2026-09-22T12:00:00Z')
        start=baseline.calendar_weeks(anchor,8)[0][1].isoformat()
        rows=[dict(kind='task',ts=start,rework=x) for x in [True,False,None,'false']]
        rows += [dict(kind='task',ts='bad',rework=True),dict(kind='task',ts='2026-10-03T00:00:00Z',rework=True)]
        report=baseline.build(rows,now=anchor)
        self.assertEqual(report['pooled']['labeled'],2)
        self.assertEqual(report['pooled']['unknown_label'],2)
        self.assertEqual(report['pooled']['rework_rate'],0.5)
        self.assertEqual(report['excluded'],dict(unknown_ts=1,future_ts=1))
        self.assertEqual(sum(r['tasks']==0 for r in report['weekly'].values()),7)
        self.assertIsNone(baseline.build([],now=anchor)['weeks_needed_per_arm'])

    def test_freeze_refuses_and_preserves_forced_backup(self):
        path=self.root/'baseline.json'
        freeze(path,{'before':True})
        with self.assertRaises(FileExistsError):
            freeze(path,{'after':True})
        self.assertEqual(json.loads(path.read_text()),{'before':True})
        freeze(path,{'after':True},force=True)
        backups=list(self.root.glob('baseline.json.prev-*'))
        self.assertEqual(len(backups),1)
        self.assertEqual(json.loads(backups[0].read_text()),{'before':True})

    def test_icc_and_power_guards(self):
        self.assertEqual([power.n_per_arm(.3713,e) for e in [.05,.1,.15,.2]],[1419,341,145,77])
        with self.assertRaises(ValueError): power.n_per_arm(.05,.05)
        with self.assertRaises(ValueError): power.icc_anova({'one':[True]})
        with self.assertRaises(ValueError): power.icc_anova({'one':[0,0],'two':[0,0]})

    def test_advice_receiver_not_sibling(self):
        sessions=self.root/'sessions'
        (sessions/'example').mkdir(parents=True)
        def row(content,stamp='2026-09-22T12:00:00Z'):
            return json.dumps({'timestamp':stamp,'message':{'content':content}})+'\n'
        (sessions/'example.jsonl').write_text(row([{'type':'tool_use','name':'search'}]))
        (sessions/'example/child.jsonl').write_text(row('ADVICE')+row([{'type':'tool_use','name':'work'}],'2026-09-22T12:00:01Z'))
        result=diagnosis.diagnose([dict(session='example',ts='2026-09-22T12:00:00Z')],sessions,'ADVICE',['search'])
        self.assertEqual(result['counts'],{'ignored':1})
        self.assertNotIn('example',json.dumps(result))

    def test_advice_segment_stops_at_next_receipt(self):
        def row(content): return json.dumps(dict(timestamp='2026-09-22T12:00:00Z',message={'content':content}))+'\n'
        (self.root/'example.jsonl').write_text(row('ADVICE')+row([dict(type='tool_use',name='work')])+row('ADVICE')+row([dict(type='tool_use',name='search')]))
        result=diagnosis.diagnose([dict(session='example',ts='2026-09-22T12:00:00Z')],self.root,'ADVICE',['search'])
        self.assertEqual(result['counts'],{'ignored':1})

    def test_invariants_changed_check_cannot_freeze(self):
        for name in ['limits.conf','rules.txt','registration.json']:
            (self.root/name).write_bytes((ROOT/'fixtures'/name).read_bytes())
        args=['--config',ROOT/'configs/invariants.json','--root',self.root,'--state-dir',self.root/'state']
        self.assertEqual(self.cli('knob_invariants.py',*args,'--freeze').returncode,0)
        frozen=self.root/'state/knobs-frozen.json'
        old=frozen.read_bytes()
        (self.root/'limits.conf').write_text('THRESHOLD = 2\nRESOURCE = 3\n')
        self.assertEqual(self.cli('knob_invariants.py',*args,'--check','--freeze','--force').returncode,1)
        self.assertEqual(frozen.read_bytes(),old)
        (self.root/'limits.conf').write_text('unknown format\n')
        self.assertEqual(self.cli('knob_invariants.py',*args,'--check').returncode,2)

    def test_invariants_environment_override(self):
        config=json.loads((ROOT/'configs/invariants.json').read_text())
        before=invariants.snapshot(config,ROOT/'fixtures')
        from unittest.mock import patch
        with patch.dict(os.environ,{'HARNESS_TRIGGER_THRESHOLD':'2'}):
            after=invariants.snapshot(config,ROOT/'fixtures')
        self.assertEqual(invariants.changed(before,after),['default_threshold'])

    def test_watchdog_missing_stale_future_and_delivery(self):
        env=dict(os.environ)
        env.pop('HARNESS_NOTIFY_COMMAND',None)
        result=self.cli('watchdog.sh','--state-dir',self.root,env=env)
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads((self.root/'watchdog-last.json').read_text())['notify_rc'],-1)
        self.healthy()
        self.assertEqual(self.cli('watchdog.sh','--state-dir',self.root,'--dry-run').returncode,0)
        old=now()-dt.timedelta(days=8)
        os.utime(self.root/'heartbeat',(old.timestamp(),old.timestamp()))
        self.assertEqual(self.cli('watchdog.sh','--state-dir',self.root,'--dry-run').returncode,1)
        self.healthy()
        atomic_json(self.root/'paused.json',{'_ts':(now()+dt.timedelta(days=1)).isoformat()})
        self.assertEqual(self.cli('watchdog.sh','--state-dir',self.root,'--dry-run').returncode,1)

    def test_real_drills_restore_inputs_and_skip_placeholders(self):
        self.healthy()
        before=(self.root/'heartbeat').read_bytes(),(self.root/'heartbeat').stat().st_mtime_ns
        baseline_before=(self.root/'baseline-latest.json').read_bytes()
        result=self.cli('drill.sh','all','--state-dir',self.root,'--no-discord')
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertEqual(result.stdout.splitlines(),['drill[outage] result=PASS','drill[metrics] result=PASS','drill[badchange] result=SKIP','drill[concurrent] result=SKIP'])
        self.assertEqual(((self.root/'heartbeat').read_bytes(),(self.root/'heartbeat').stat().st_mtime_ns),before)
        self.assertEqual((self.root/'baseline-latest.json').read_bytes(),baseline_before)
        rows=[json.loads(x) for x in (self.root/'drills.jsonl').read_text().splitlines()]
        self.assertTrue(all(r['notify_rc'] is None for r in rows))

    def test_unhealthy_start_cannot_pass_drill(self):
        result=self.cli('drill.sh','outage','--state-dir',self.root,'--no-discord')
        self.assertEqual(result.returncode,1)
        self.assertIn('result=FAIL',result.stdout)

    def test_routing_handlers_and_judge_contract(self):
        config=json.loads((ROOT/'configs/audit.json').read_text())
        self.assertEqual(audit.classify('agent',{'model':'lower-tier'},config),'subscription-sub-agent')
        self.assertEqual(audit.classify('shell',{'command':'MODE=fixture cheap-run job'},config),'cheap-dispatch')
        self.assertEqual(audit.classify('workflow-agent',{'delegated':True},config),'workflow-cheap-dispatch')
        with self.assertRaises(ValueError): audit.audit([{'handler':'orchestration'}],lambda a,p:{'items':[]})
        self.assertIn('PENDULUM-2',audit.pendulums(90,0,3,2,0))
        self.assertNotIn('PENDULUM-2',audit.pendulums(90,0,3,2,1))

    def test_trend_trigger_does_not_cross_rule_versions(self):
        path=self.root/'trend.jsonl'
        low=dict(adherence=14,waste=43)
        self.assertFalse(audit.log_trend(path,low,'rules-a'))
        self.assertFalse(audit.log_trend(path,low,'rules-a'))
        self.assertFalse(audit.log_trend(path,low,'rules-b'))
        self.assertFalse(audit.log_trend(path,low,'rules-b'))
        self.assertTrue(audit.log_trend(path,low,'rules-b'))

    def test_producer_pause_offsets_no_fuel_and_rotation(self):
        lessons,outcomes=self.root/'lessons.txt',self.root/'outcomes.jsonl'
        lessons.write_text('synthetic\n')
        outcomes.write_text('{}\n')
        cmd=['--state-dir',self.root,lessons,outcomes]
        self.assertIn('paused',self.cli('proposals_producer.sh',*cmd).stdout)
        self.assertFalse((self.root/'producer-offsets.json').exists())
        self.healthy()
        self.assertIn('appended',self.cli('proposals_producer.sh',*cmd).stdout)
        self.assertIn('no new fuel',self.cli('proposals_producer.sh',*cmd).stdout)
        lessons.write_text('new synthetic text\n')
        self.assertIn('appended',self.cli('proposals_producer.sh',*cmd).stdout)
        lessons.write_text('x')
        self.assertIn('appended',self.cli('proposals_producer.sh',*cmd).stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
