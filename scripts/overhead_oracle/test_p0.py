"""Three synthetic tests for aggregate-only measurement."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from make_fixtures import generate
import oracle
import shapes
import declared_actual


class P0Test(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        # Generator output is incidental; assertions concern the actual artifacts.
        from contextlib import redirect_stdout
        import io
        with redirect_stdout(io.StringIO()):
            generate(self.root)
        self.config=json.loads((ROOT/'configs/oracle.json').read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def private_free(self,data):
        raw=json.dumps(data)
        for marker in ['synthetic-identity','synthetic-model','synthetic/plans/',
                       'synthetic text must not be exported',str(self.root)]:
            self.assertNotIn(marker,raw)
        self.assertNotIn('per_model',data)
        self.assertNotIn('by_session',data)

    def test_oracle(self):
        data=oracle.analyze(self.root/'sessions',2,self.config)
        self.assertEqual(data['assistant_turns'],14)
        self.assertEqual({b:r['turns'] for b,r in data['buckets'].items()},
                         {'plan-writing':2,'routing':2,'review':2,'question':1,'closeout':2,'text-only':3,'work':2})
        self.assertEqual(data['overhead_window']['turns'],2)
        self.assertAlmostEqual(data['share']['turns'],11/14)
        direct=oracle.analyze(self.root/'sessions',0,self.config)
        self.assertEqual(direct['overhead_window']['turns'],0)
        shares=[oracle.analyze(self.root/'sessions',w,self.config)['share']['turns'] for w in (0,2,6,12)]
        self.assertEqual(shares,sorted(shares))
        self.private_free(data)
        source=self.root/'sessions/first.jsonl'
        source.write_text(source.read_text()+'invalid\n')
        self.assertEqual(oracle.analyze(self.root/'sessions',2,self.config)['lines_skipped'],1)

    def test_shapes(self):
        data=shapes.inventory(self.root/'goals',self.root/'routing.md')
        self.assertEqual(data['shape_rows'],3)
        self.assertFalse(data['contains_text'])
        self.assertEqual((data['goals'],data['tasks']),(3,4))
        self.assertEqual(data['summary']['status'],{'in_progress':1,'done':1,'unknown':1})
        self.assertEqual(data['summary']['done_count'],1)
        self.private_free(data)
        self.assertNotIn('Synthetic goal',json.dumps(data))
        for i in range(5):
            (self.root/'goals'/('repeat-'+str(i)+'.md')).write_text('status: done\nshape: alpha\n')
        self.assertEqual(shapes.inventory(self.root/'goals',self.root/'routing.md')['shapes_with_five_completed_precedents'],1)

    def test_declared_actual(self):
        rows=[dict(ts='2026-09-22',declared='main-inline',actual='main',rework=True),
              dict(ts='2026-09-22',declared='main',actual='cheap',rework=False),
              dict(ts='2026-09-22',declared='unrecognized',actual='unrecognized',rework=None),
              dict(ts='2026-09-22',declared='main',actual='main',rework=None)]
        ledger=self.root/'comparison.jsonl'
        ledger.write_text(''.join(json.dumps(r)+'\n' for r in rows)+'invalid\n')
        result=declared_actual.build(ledger)['summary']
        self.assertEqual((result['same'],result['differ'],result['unknown']),(2,1,1))
        self.assertEqual(result['rework_rate'],{'same':1.0,'differ':0.0,'unknown':None})
        self.assertEqual(result['spelling_normalized'],1)
        self.assertEqual(result['unparsable'],1)
        self.private_free(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
