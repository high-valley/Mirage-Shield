import hashlib,json,unittest
from pathlib import Path
from experiments.engine import wilson
class ResultTests(unittest.TestCase):
 def test_frozen_and_complete(self):
  root=Path('experiments');lock=json.loads((root/'results/frozen.json').read_text())
  for name,key in [('engine.py','engine_sha256'),('plan.json','plan_sha256')]:
   self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),lock[key])
  for phase,total in [('development',54),('holdout',140)]:
   data=json.loads((root/f'results/{phase}.json').read_text());self.assertEqual(len(data['rows']),total)
   self.assertEqual(data['margin'],lock['margin'])
   for r in data['rows']:
    self.assertEqual(r['n'],10000);self.assertEqual(r['reach_rate'],r['reached']/r['n'])
    self.assertEqual(r['ci95'],wilson(r['reached'],r['n']))
    self.assertLessEqual(r['mean_decoys'],r['mean_turns'])
    self.assertEqual(r['seed_start'],31000000 if phase=='development' else 91000000)
