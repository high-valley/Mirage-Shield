"""python -m experiments.evaluate --phase development, then --phase holdout."""
import argparse, hashlib, json, platform
from dataclasses import asdict
from pathlib import Path
from .engine import AGENTS, POLICIES, Config, run, wilson, paired_ci
ROOT=Path(__file__).resolve().parent

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def evaluate(name,c,agents,n,seed,margin,legacy=False):
    rows=[]
    for agent in agents:
        outcomes={p:[run(seed+i,p,agent,c,margin=margin,legacy=legacy) for i in range(n)] for p in POLICIES}
        base=outcomes['fixed']
        for policy, runs in outcomes.items():
            hits=sum(r['success'] for r in runs)
            ds=[int(r['success'])-int(b['success']) for r,b in zip(runs,base)]
            rows.append(dict(condition=name,config=asdict(c),agent=agent,policy=policy,n=n,seed_start=seed,
                reached=hits,reach_rate=hits/n,ci95=wilson(hits,n),delta_fixed=sum(ds)/n,
                delta_ci95=paired_ci(ds),mean_moves=sum(r['moves'] for r in runs)/n,
                mean_decoys=sum(r['decoys'] for r in runs)/n,mean_turns=sum(r['turns'] for r in runs)/n))
    return rows

def main():
    p=argparse.ArgumentParser(); p.add_argument('--phase',choices=['development','holdout'],required=True); args=p.parse_args()
    plan=json.loads((ROOT/'plan.json').read_text()); n=plan['n']; out=ROOT/'results'; out.mkdir(exist_ok=True)
    lockpath=out/'frozen.json'
    if args.phase=='development':
        if lockpath.exists(): raise SystemExit('Frozen selection exists; do not overwrite after holdout.')
        trials=[]
        for margin in plan['margins']:
            score=0
            for bias in ('uniform','A','D'):
                for agent in ('learning','random'):
                    score+=sum(run(plan['development_seed']+i,'predictive',agent,Config(bias=bias),margin=margin)['success'] for i in range(n))
            trials.append(dict(margin=margin,reach_rate=score/(6*n)))
        chosen=min(trials,key=lambda t:(t['reach_rate'],-t['margin']))['margin']
        lock=dict(margin=chosen,trials=trials,engine_sha256=digest(ROOT/'engine.py'),plan_sha256=digest(ROOT/'plan.json'))
        lockpath.write_text(json.dumps(lock,indent=2)+'\n')
        rows=[]
        for bias in ('uniform','A','D'):
            rows+=evaluate('development_'+bias,Config(bias=bias),('random','learning'),n,plan['development_seed'],chosen)
        # Faithful old RNG for all six original policies, for diagnosis, not tuning.
        rows+= [r for r in evaluate('legacy_uniform',Config(),('random','learning'),n,plan['development_seed'],chosen,True) if r['policy']!='predictive']
    else:
        lock=json.loads(lockpath.read_text())
        if lock['engine_sha256']!=digest(ROOT/'engine.py') or lock['plan_sha256']!=digest(ROOT/'plan.json'): raise SystemExit('Frozen engine/plan changed')
        rows=[]
        for condition in plan['holdout']:
            values=dict(condition); name=values.pop('name')
            rows+=evaluate(name,Config(**values),AGENTS,n,plan['holdout_seed'],lock['margin'])
    result=dict(phase=args.phase,python=platform.python_version(),engine_sha256=digest(ROOT/'engine.py'),plan_sha256=digest(ROOT/'plan.json'),margin=lock['margin'],rows=rows)
    (out/(args.phase+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(args.phase, 'rows=',len(rows),'episodes=',sum(r['n'] for r in rows),'margin=',lock['margin'],flush=True)
if __name__=='__main__': main()
