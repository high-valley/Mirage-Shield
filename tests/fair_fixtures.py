import json
from experiments.engine import *
rows=[]
for bias in ('uniform','A','D'):
 for linked in (False,True):
  for agent in AGENTS:
   for policy in POLICIES:
    for seed in (0,1,42,20261024,4294967295):
     rows.append(dict(bias=bias,linked=linked,agent=agent,policy=policy,seed=seed,result=run(seed,policy,agent,Config(bias=bias,linked=linked),margin=.1,trace=True)))
print(json.dumps(rows))
