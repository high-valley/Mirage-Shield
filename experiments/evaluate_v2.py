"""Reproducible second study, no external dependencies or network access."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import platform
import time
from .engine import wilson, paired_ci
from .engine_v2 import Config, POLICIES, make_world, run
ROOT=Path(__file__).resolve().parent
HASH_FILES=('engine_v2.py','evaluate_v2.py','plan_v2.json')

def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in HASH_FILES}
def config(condition):return Config(**{k:tuple(v) if k=='weights' else v for k,v in condition.items() if k!='name'})
def write(path,data):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.replace(path)

def batch(condition,agent,n,start,threshold,policies=POLICIES,blocks=2):
    c=config(condition);out={p:[] for p in policies}
    for i in range(n):
        world=make_world(start+i,c)
        for p in policies:out[p].append(run(start+i,p,agent,c,threshold,world=world))
    rows=[]
    anchor=out['fixed_anchor']
    fixed_mean=[sum(out['fixed_'+letter][i]['success'] for letter in 'ABCD')/4 for i in range(n)] if 'fixed_A' in out else None
    for policy,runs in out.items():
        bits=[int(r['success']) for r in runs];reached=sum(bits)
        differences=[bit-int(base['success']) for bit,base in zip(bits,anchor)]
        row=dict(condition=condition['name'],config=asdict(c),agent=agent,policy=policy,n=n,seed_start=start,
                 reached=reached,reach_rate=reached/n,ci95=wilson(reached,n),delta_anchor=sum(differences)/n,
                 delta_anchor_ci95=paired_ci(differences),mean_moves=sum(r['moves'] for r in runs)/n,
                 mean_decoys=sum(r['decoys'] for r in runs)/n,mean_turns=sum(r['turns'] for r in runs)/n)
        row['cost_reach_plus_001_moves']=row['reach_rate']+.01*row['mean_moves']
        row['blocks']=[dict(n=len(bits[j*n//blocks:(j+1)*n//blocks]),reach_rate=sum(bits[j*n//blocks:(j+1)*n//blocks])/(n//blocks),
                            delta_anchor=sum(differences[j*n//blocks:(j+1)*n//blocks])/(n//blocks)) for j in range(blocks)]
        if fixed_mean is not None:
            d=[bit-base for bit,base in zip(bits,fixed_mean)]
            row.update(fixed_mean_reach=sum(fixed_mean)/n,delta_fixed_mean=sum(d)/n,delta_fixed_mean_ci95=paired_ci(d))
        rows.append(row)
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('development','holdout'),required=True)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results_v2');args=parser.parse_args()
    plan=json.loads((ROOT/'plan_v2.json').read_text());out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    freeze=out/'frozen.json';n=plan['n'];started=time.monotonic()
    if args.phase=='development':
        if freeze.exists() or (out/'holdout.json').exists():raise SystemExit('Frozen study exists; use a new output directory for reproduction.')
        trials=[]
        for threshold in plan['thresholds']:
            rows=[]
            for condition in plan['development']:
                for agent in plan['development_agents']:
                    rows.extend(batch(condition,agent,n,plan['development_seed'],threshold,('fixed_anchor','robust'),plan['replication_blocks']))
            robust=[r for r in rows if r['policy']=='robust']
            trial=dict(threshold=threshold,eligible=all(r['delta_anchor']<=.01 for r in robust),mean_reach=sum(r['reach_rate'] for r in robust)/len(robust),cells=robust)
            trials.append(trial)
            print('threshold',threshold,'eligible',trial['eligible'],'mean',trial['mean_reach'],flush=True)
        eligible=[t for t in trials if t['eligible']]
        selected=min(eligible,key=lambda t:(t['mean_reach'],-t['threshold'])) if eligible else None
        threshold=selected['threshold'] if selected else .95
        locked=dict(selected_policy='robust' if selected else 'fixed_anchor',threshold=threshold,hashes=hashes(),trials=trials)
        write(freeze,locked)
    else:
        locked=json.loads(freeze.read_text())
        if locked['hashes']!=hashes():raise SystemExit('Frozen sources changed.')
        if (out/'holdout.json').exists():raise SystemExit('Holdout already recorded; do not overwrite.')
        threshold=locked['threshold']
    rows=[]
    conditions=plan[args.phase];agents=plan[args.phase+'_agents']
    seed=plan[args.phase+'_seed']
    for j,condition in enumerate(conditions):
        # Separate namespaces per condition and agent, unlike the first study.
        for k,agent in enumerate(agents):
            rows.extend(batch(condition,agent,n,seed+j*1000000+k*100000,threshold,blocks=plan['replication_blocks']))
        print(args.phase,condition['name'],'done',flush=True)
    # Conservative simultaneous bounds valid for independent bounded per-episode draws;
    # PRNG samples are deterministic approximations of that sampling model.
    family_size=sum(r['policy']!='fixed_anchor' for r in rows)+len(rows)
    radius=math.sqrt(2*math.log(2*family_size/.05)/n)
    for row in rows:
        for label in ('anchor','fixed_mean'):
            delta=row['delta_'+label]
            row['delta_'+label+'_simultaneous95']=[max(-1,delta-radius),min(1,delta+radius)]
        if row['policy']=='fixed_anchor':row['delta_anchor_simultaneous95']=[0.,0.]
    result=dict(phase=args.phase,n=n,python=platform.python_version(),hashes=hashes(),threshold=threshold,
                selected_policy=locked['selected_policy'],simultaneous_family_size=family_size,simultaneous_radius=radius,
                rows=rows,episodes=len(rows)*n,seconds=round(time.monotonic()-started,3))
    write(out/(args.phase+'.json'),result)
    print(args.phase,'episodes',result['episodes'],'seconds',result['seconds'],flush=True)
if __name__=='__main__':main()
