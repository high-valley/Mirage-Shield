import json
from experiments.engine import Config, run
rows=[]
for bias in ('uniform','A','D'):
 for linked in (False,True):
  for agent in ('random','learning'):
   for policy in ('none','fixed','adaptive','risk','guard','cautious'):
    for seed in (0,1,42,20261024,4294967295):
     rows.append(dict(bias=bias,linked=linked,agent=agent,policy=policy,seed=seed,result=run(seed,policy,agent,Config(bias=bias,linked=linked),legacy=True,trace=True)))
print(json.dumps(rows))
