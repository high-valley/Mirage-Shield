"""Frozen v2 algorithms under corrupted shared responses. Offline, no tuning."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from .engine import wilson,paired_ci
from .engine_v2 import AGENTS,POLICIES,Config,Defender,Public,REWARD,make_world,stream
ROOT=Path(__file__).resolve().parent
FILES=('engine_v2.py','sensor_audit.py','plan_sensor_audit.json','results_v2/frozen.json')

def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}

def run(seed,policy,agent,c=Config(),threshold=.8,error_rate=0.,trace=False,world=None):
    if agent not in AGENTS or not 0<=error_rate<=1:raise ValueError('agent/error_rate')
    world=make_world(seed,c) if world is None else world
    defender=Defender(policy,Public(world.anchor,world.importance,world.labels,c.switch_delay),threshold)
    sensor=stream(seed,'sensor_error',c.stream)
    scores=[0.]*4;moves=decoys=errors=0;previous=-1;cooldown=0;steps=[]
    for t,(explore,choice,noise) in enumerate(world.draws):
        desired=defender.choose()
        if t and desired!=previous:moves+=1;cooldown=c.switch_delay
        previous=desired;active=desired if not cooldown else -1;cooldown=max(0,cooldown-1)
        if agent in ('sweep','reverse','persistent') or agent=='switching' and t<c.budget//2:
            position=(world.offset+(t//4 if agent=='persistent' else -t if agent=='reverse' else t))%4
            entry=world.labels[position]
        elif agent in ('random','switching') or explore<c.epsilon:entry=world.labels[int(choice*4)]
        else:
            best=max(scores);choices=[i for i in world.labels if abs(scores[i]-best)<1e-12]
            entry=choices[int(choice*len(choices))]
        trapped=entry==active;hit=entry==world.target and not trapped
        truth='target' if hit else 'decoy' if trapped else 'hint' if noise<c.hint else 'empty'
        corrupt=sensor.random()<error_rate and not hit
        feedback=('empty' if truth=='decoy' else 'decoy') if corrupt else truth
        errors+=corrupt
        if agent=='learning':scores[entry]+=c.learning_rate*(REWARD[feedback]-scores[entry])
        defender.observe(entry,feedback);decoys+=trapped
        if trace:steps.append(dict(entry=entry,decoy=active,feedback=feedback,true_feedback=truth,desired=desired,possible=list(defender.possible)))
        if hit:return dict(success=True,moves=moves,decoys=decoys,turns=t+1,errors=errors,steps=steps)
    return dict(success=False,moves=moves,decoys=decoys,turns=c.budget,errors=errors,steps=steps)

def main():
    plan=json.loads((ROOT/'plan_sensor_audit.json').read_text());folder=ROOT/'results_sensor';folder.mkdir(exist_ok=True)
    if (folder/'frozen.json').exists() or (folder/'audit.json').exists():raise SystemExit('Audit already frozen; preserve results.')
    locked=json.loads((ROOT/'results_v2/frozen.json').read_text());threshold=locked['threshold']
    snapshot=dict(hashes=hashes(),threshold=threshold,selected_policy=locked['selected_policy'])
    (folder/'frozen.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    n=plan['n'];rows=[]
    for j,name in enumerate(plan['conditions']):
        c=Config(linked=name=='importance_linked')
        for k,agent in enumerate(plan['agents']):
            start=plan['seed']+j*1000000+k*100000
            samples={e:{p:[] for p in POLICIES} for e in plan['error_rates']}
            for i in range(n):
                world=make_world(start+i,c)
                for error_rate in plan['error_rates']:
                    for policy in POLICIES:
                        samples[error_rate][policy].append(run(start+i,policy,agent,c,threshold,error_rate,world=world))
            for error_rate,outcomes in samples.items():
                fixed_mean=[sum(outcomes['fixed_'+letter][i]['success'] for letter in 'ABCD')/4 for i in range(n)]
                for policy,runs in outcomes.items():
                    bits=[int(r['success']) for r in runs];hits=sum(bits)
                    row=dict(condition=name+'_error_'+str(error_rate),base_condition=name,agent=agent,policy=policy,
                             error_rate=error_rate,config=asdict(c),n=n,seed_start=start,reached=hits,reach_rate=hits/n,ci95=wilson(hits,n),
                             mean_moves=sum(r['moves'] for r in runs)/n,mean_decoys=sum(r['decoys'] for r in runs)/n,
                             mean_turns=sum(r['turns'] for r in runs)/n,mean_errors=sum(r['errors'] for r in runs)/n)
                    for comparator,base in (('anchor',[int(r['success']) for r in outcomes['fixed_anchor']]),
                                            ('fixed_mean',fixed_mean),('noiseless',[int(r['success']) for r in samples[0.][policy]])):
                        d=[b-a for b,a in zip(bits,base)]
                        row['delta_'+comparator]=sum(d)/n;row['delta_'+comparator+'_ci95']=paired_ci(d)
                    rows.append(row)
            print(name,agent,'done',flush=True)
    family=len(rows)*3;radius=math.sqrt(2*math.log(2*family/.05)/n)
    for r in rows:
        for key in ('anchor','fixed_mean','noiseless'):
            d=r['delta_'+key];r['delta_'+key+'_simultaneous95']=[max(-1,d-radius),min(1,d+radius)]
    if snapshot['hashes']!=hashes():raise SystemExit('Audit sources changed while running.')
    result=dict(**snapshot,rows=rows,episodes=len(rows)*n,simultaneous_family_size=family,simultaneous_radius=radius)
    (folder/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('sensor audit',result['episodes'],'episodes',flush=True)
if __name__=='__main__':main()
