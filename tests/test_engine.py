import unittest
from experiments.engine import *

class EngineTests(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(run(123,'adaptive','learning',trace=True),run(123,'adaptive','learning',trace=True))
    def test_no_defense_exhaustive(self):
        for seed in range(100):
            self.assertTrue(run(seed,'none','sweep',Config(budget=4))['success'])
    def test_fixed_exact_protection(self):
        c=Config(budget=4)
        for seed in range(100):
            target,_=scenario(seed,c)
            self.assertEqual(run(seed,'fixed','sweep',c)['success'],target!=0)
    def test_policy_invariants(self):
        for p in POLICIES:
            for a in AGENTS:
                r=run(42,p,a,trace=True)
                self.assertLessEqual(r['turns'],16)
                self.assertLessEqual(r['decoys'],r['turns'])
                self.assertLessEqual(r['moves'],r['turns']-1)
                for s in r['steps']:
                    self.assertIn(s['decoy'],range(-1,4))
                    if s['feedback']=='target': self.assertNotEqual(s['entry'],s['decoy'])
    def test_latency_can_only_remove_fixed_protection_on_switch(self):
        for seed in range(40):
            for a in AGENTS:
                self.assertEqual(run(seed,'fixed',a),run(seed,'fixed',a,Config(switch_delay=2)))
    def test_history_prediction_moves_away_from_decoy(self):
        self.assertEqual(decoy('predictive',[(0,'decoy')],[1,2,3,4],[-.576,0,0,0]),1)
        self.assertEqual(decoy('adaptive',[(0,'decoy')],[1,2,3,4],[-.576,0,0,0]),0)
    def test_intervals(self):
        lo,hi=wilson(0,10000); self.assertAlmostEqual(lo,0); self.assertGreater(hi,0)
        self.assertEqual(paired_ci([0]*100),[0,0])
    def test_invalid(self):
        with self.assertRaises(ValueError): Config(budget=0)
        with self.assertRaises(ValueError): run(1,'oops','random')

if __name__=='__main__': unittest.main()
