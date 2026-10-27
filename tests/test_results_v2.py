import hashlib,json,math,unittest
from pathlib import Path
from experiments.engine import wilson
from experiments.engine_v2 import POLICIES
from experiments.evaluate_v2 import hashes
ROOT=Path('experiments')
class SecondResultTests(unittest.TestCase):
 def test_complete_frozen_study(self):
  folder=ROOT/'results_v2'
  self.assertTrue((folder/'holdout.json').exists(),'Full study results must be committed')
  locked=json.loads((folder/'frozen.json').read_text());self.assertEqual(locked['hashes'],hashes())
  plan=json.loads((ROOT/'plan_v2.json').read_text());eligible=[t for t in locked['trials'] if t['eligible']]
  selected=min(eligible,key=lambda t:(t['mean_reach'],-t['threshold'])) if eligible else None
  self.assertEqual(locked['selected_policy'],'robust' if selected else 'fixed_anchor')
  if selected:self.assertEqual(locked['threshold'],selected['threshold'])
  for trial in locked['trials']:
   self.assertEqual(trial['eligible'],all(r['delta_anchor']<=.01 for r in trial['cells']))
  seeds={}
  for phase in ('development','holdout'):
   data=json.loads((folder/(phase+'.json')).read_text());self.assertEqual(data['hashes'],hashes())
   self.assertEqual(len(data['rows']),len(plan[phase])*len(plan[phase+'_agents'])*len(POLICIES))
   self.assertEqual(data['episodes'],len(data['rows'])*10000)
   unique=set()
   for r in data['rows']:
    key=(r['condition'],r['agent'],r['policy']);self.assertNotIn(key,unique);unique.add(key)
    self.assertEqual(r['n'],10000);self.assertEqual(r['reach_rate'],r['reached']/10000)
    self.assertEqual(r['ci95'],wilson(r['reached'],10000))
    self.assertAlmostEqual(sum(b['reach_rate']*b['n'] for b in r['blocks'])/10000,r['reach_rate'])
    self.assertEqual(sum(b['n'] for b in r['blocks']),10000)
    self.assertLessEqual(r['mean_decoys'],r['mean_turns']);self.assertLessEqual(r['mean_moves'],r['mean_turns']-1+1e-9)
    anchor=next(b for b in data['rows'] if b['condition']==r['condition'] and b['agent']==r['agent'] and b['policy']=='fixed_anchor')
    self.assertAlmostEqual(r['delta_anchor'],r['reach_rate']-anchor['reach_rate'])
    fixed=[b['reach_rate'] for b in data['rows'] if b['condition']==r['condition'] and b['agent']==r['agent'] and b['policy'] in ('fixed_A','fixed_B','fixed_C','fixed_D')]
    self.assertAlmostEqual(r['fixed_mean_reach'],sum(fixed)/4)
    for label in ('anchor','fixed_mean'):
     lo,hi=r['delta_'+label+'_simultaneous95'];self.assertLessEqual(lo,r['delta_'+label]);self.assertGreaterEqual(hi,r['delta_'+label])
    if r['config']['switch_delay'] and r['policy'] in ('belief','gated','robust'):
     self.assertEqual(r['reached'],anchor['reached']);self.assertEqual(r['mean_moves'],0)
    if r['policy']=='fixed_anchor':
     start=r['seed_start'];seeds.setdefault(phase,set()).update(range(start,start+r['n']))
   family=len(data['rows'])+sum(r['policy']!='fixed_anchor' for r in data['rows'])
   self.assertEqual(data['simultaneous_family_size'],family)
   self.assertAlmostEqual(data['simultaneous_radius'],math.sqrt(2*math.log(2*family/.05)/10000))
  self.assertFalse(seeds['development'] & seeds['holdout'])
