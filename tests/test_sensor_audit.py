import hashlib,json,unittest
from pathlib import Path
from experiments.engine_v2 import POLICIES,AGENTS,Config,run as original
from experiments.sensor_audit import run,hashes
class SensorAuditTests(unittest.TestCase):
 def test_zero_error_preserves_frozen_engine(self):
  for seed in range(6):
   for policy in POLICIES:
    for agent in AGENTS:
     a=original(seed,policy,agent,threshold=.8,trace=True);b=run(seed,policy,agent,threshold=.8,error_rate=0,trace=True)
     for key in ('success','moves','decoys','turns'):self.assertEqual(a[key],b[key])
     for x,y in zip(a['steps'],b['steps']):
      for key in x:self.assertEqual(x[key],y[key])
     self.assertEqual(b['errors'],0)
 def test_full_error_only_changes_observation(self):
  for seed in range(10):
   r=run(seed,'fixed_anchor','random',error_rate=1,trace=True)
   for s in r['steps']:
    expected='target' if s['true_feedback']=='target' else 'empty' if s['true_feedback']=='decoy' else 'decoy'
    self.assertEqual(s['feedback'],expected)
   self.assertEqual(r['success'],original(seed,'fixed_anchor','random')['success'])
 def test_recorded_audit_frozen_complete(self):
  folder=Path('experiments/results_sensor');f=json.loads((folder/'frozen.json').read_text());self.assertEqual(f['hashes'],hashes())
  data=json.loads((folder/'audit.json').read_text());self.assertEqual(data['hashes'],hashes())
  self.assertEqual(len(data['rows']),396);self.assertEqual(data['episodes'],3960000)
  seen=set()
  for r in data['rows']:
   key=(r['base_condition'],r['agent'],r['policy'],r['error_rate']);self.assertNotIn(key,seen);seen.add(key)
   self.assertLessEqual(r['mean_errors'],r['mean_turns'])
   self.assertEqual(r['n'],10000);self.assertEqual(r['reach_rate'],r['reached']/10000)
   if r['error_rate']==0:self.assertEqual(r['delta_noiseless'],0);self.assertEqual(r['mean_errors'],0)
   if r['policy']=='fixed_anchor':self.assertEqual(r['delta_anchor'],0)
  for base in ('uniform','importance_linked'):
   rr=[r for r in data['rows'] if r['base_condition']==base and r['agent']=='random' and r['policy']=='fixed_anchor']
   self.assertEqual(len({r['reached'] for r in rr}),1)
  prior=[]
  for phase in ('development','holdout'):
   old=json.loads((Path('experiments/results_v2')/(phase+'.json')).read_text())
   prior.extend({(r['seed_start'],r['seed_start']+r['n']) for r in old['rows']})
  for r in data['rows']:
   low,high=r['seed_start'],r['seed_start']+r['n']
   self.assertTrue(all(high<=a or low>=b for a,b in prior))
