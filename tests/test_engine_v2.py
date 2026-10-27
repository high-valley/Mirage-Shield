from dataclasses import replace,fields
from fractions import Fraction
import unittest
from experiments.engine_v2 import Config,Public,Defender,POLICIES,AGENTS,make_world,run,stream
from experiments.analysis_v2 import optimal_random_reach

class SecondEngineTests(unittest.TestCase):
 def test_exact_random_optimum_matches_fixed(self):
  for possible in range(1,5):
   for turns in (0,1,2,4,16,27):
    fixed=Fraction(possible-1,possible)*(1-Fraction(3,4)**turns)
    self.assertEqual(optimal_random_reach(possible,turns),fixed)
 def test_public_input_excludes_secrets(self):
  self.assertEqual({f.name for f in fields(Public)}, {'anchor','importance','labels','switch_delay'})
 def test_streams_deterministic_separate_and_bounded(self):
  for family in ('mt19937','sha256'):
   a=stream(123,'a',family);b=stream(123,'a',family);c=stream(123,'b',family)
   aa=[a.random() for _ in range(20)];bb=[b.random() for _ in range(20)];cc=[c.random() for _ in range(20)]
   self.assertEqual(aa,bb);self.assertNotEqual(aa,cc);self.assertTrue(all(0<=x<1 for x in aa))
 def test_label_permutation_covariance(self):
  c=Config();mapping=(2,0,3,1)
  for seed in range(8):
   w=make_world(seed,c);importance=[0]*4
   for i in range(4):importance[mapping[i]]=w.importance[i]
   rotated=replace(w,target=mapping[w.target],anchor=mapping[w.anchor],labels=tuple(mapping[i] for i in w.labels),importance=tuple(importance))
   for p in ('none','fixed_anchor','risk','predictive','belief','gated','robust'):
    for agent in AGENTS:
     a=run(seed,p,agent,c,trace=True,world=w);b=run(seed,p,agent,c,trace=True,world=rotated)
     for key in ('success','moves','decoys','turns'):self.assertEqual(a[key],b[key],(seed,p,agent,key))
     for x,y in zip(a['steps'],b['steps']):
      self.assertEqual(mapping[x['entry']],y['entry']);self.assertEqual(-1 if x['decoy']==-1 else mapping[x['decoy']],y['decoy'])
 def test_random_fixed_reference_monte_carlo(self):
  n=10000;observed=sum(run(700000+i,'fixed_anchor','random')['success'] for i in range(n))/n
  self.assertLess(abs(observed-float(optimal_random_reach(4,16))),.015)
 def test_protected_negative_is_not_target_exclusion(self):
  d=Defender('robust',Public(0,(1,2,3,4),(0,1,2,3),0))
  d.observe(0,'decoy');self.assertTrue(d.possible[0]);d.observe(1,'empty');self.assertFalse(d.possible[1])
 def test_latency_fallback_exact(self):
  for seed in range(12):
   for agent in AGENTS:
    c=Config(switch_delay=2)
    baseline=run(seed,'fixed_anchor',agent,c)
    for p in ('belief','gated','robust'):self.assertEqual(run(seed,p,agent,c),baseline)
 def test_nominal_model_probabilities(self):
  d=Defender('robust',Public(0,(1,2,3,4),(3,1,0,2),0))
  for entry,feedback in ((2,'empty'),(0,'decoy'),(3,'hint')):
   for m in d.models:self.assertAlmostEqual(sum(d.probabilities(m)),1)
   d.observe(entry,feedback);self.assertAlmostEqual(sum(d.mass),1)
 def test_trace_has_one_decoy_and_budget(self):
  for p in POLICIES:
   for agent in AGENTS:
    c=Config(budget=7,switch_delay=1);r=run(17,p,agent,c,trace=True)
    self.assertLessEqual(r['turns'],7);self.assertLessEqual(r['moves'],r['turns']-1)
    for step in r['steps']:
     self.assertIn(step['decoy'],range(-1,4))
     if step['feedback']=='target':self.assertNotEqual(step['entry'],step['decoy'])
 def test_invalid_config(self):
  for kwargs in ({'budget':1.2},{'weights':(1,2)},{'weights':(1,2,3,float('nan'))},{'epsilon':float('nan')},{'stream':'unknown'}):
   with self.assertRaises(ValueError):Config(**kwargs)
