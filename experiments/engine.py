"""Offline toy environment. Standard library only; no networking capabilities."""
from dataclasses import dataclass
import math

POLICIES = ('none', 'fixed', 'adaptive', 'risk', 'guard', 'cautious', 'predictive')
AGENTS = ('random', 'learning', 'sweep', 'persistent')

class RNG:
    def __init__(self, seed): self.seed = seed & 0xffffffff
    def __call__(self):
        self.seed = (1664525 * self.seed + 1013904223) & 0xffffffff
        return self.seed / 4294967296

def weighted(rand, weights):
    x = rand() * sum(weights)
    for i, w in enumerate(weights):
        x -= w
        if x < 0: return i
    return len(weights)-1

@dataclass(frozen=True)
class Config:
    bias: str = 'uniform'
    linked: bool = False
    budget: int = 16
    hint: float = .24
    learning_rate: float = .48
    epsilon: float = .16
    switch_delay: int = 0
    def __post_init__(self):
        if self.bias not in ('uniform', 'A', 'B', 'D'): raise ValueError('bias')
        if self.budget < 1 or self.switch_delay < 0: raise ValueError('budget/delay')
        if any(not 0 <= v <= 1 for v in (self.hint, self.learning_rate, self.epsilon)): raise ValueError('probability')

def scenario(seed, c):
    r = RNG(seed); importance = [1,2,3,4]
    for i in range(3,0,-1):
        j = int(r()*(i+1)); importance[i], importance[j] = importance[j], importance[i]
    weights = list(importance) if c.linked else [1]*4
    if c.bias != 'uniform':
        weights = [1]*4; weights['ABCD'.index(c.bias)] = 5
    return weighted(r, weights), importance

def decoy(mode, history, importance, estimate, margin=.0):
    if mode == 'none': return -1
    if mode == 'fixed': return 0
    if mode == 'risk': return importance.index(max(importance))
    if mode == 'predictive':
        # Estimate observable learner scores; no access to hidden target or agent type.
        candidate = estimate.index(max(estimate))
        return candidate if estimate[candidate]-estimate[0] > margin else 0
    if mode == 'guard':
        count = [sum(h[0]==i for h in history[-6:]) for i in range(4)]
        candidate = count.index(max(count))
        return candidate if len(history)>=5 and candidate!=0 and count[candidate]>=5 else 0
    w = [sum((.78 if mode=='cautious' else .82)**(len(history)-1-j)
             for j,h in enumerate(history) if h[0]==i) for i in range(4)]
    candidate = w.index(max(w))
    if mode == 'cautious':
        return candidate if len(history)>=6 and candidate!=0 and w[candidate]-w[0]>1.8 and w[candidate]>2.8 else 0
    return candidate

def run(seed, policy, agent, c=Config(), *, legacy=False, margin=0., trace=False):
    if policy not in POLICIES or agent not in AGENTS: raise ValueError('policy/agent')
    target, importance = scenario(seed, c)
    r = RNG(seed ^ 0x9e3779b9); scores=[0.]*4; estimate=[0.]*4; history=[]
    moves=0; lures=0; previous=-1; cooldown=0; success=False; steps=[]
    for turn in range(c.budget):
        d=decoy(policy,history,importance,estimate,margin)
        if turn and d!=previous: moves+=1; cooldown=c.switch_delay
        previous=d
        active=d if cooldown==0 else -1
        cooldown=max(0,cooldown-1)
        # Fair mode: fixed draws per turn and purpose, even after policy divergence.
        if not legacy: explore, choice, noise = r(),r(),r()
        if agent == 'sweep': entry=turn%4
        elif agent == 'persistent': entry=(seed+turn//4)%4
        elif legacy:
            if agent=='random' or r()<c.epsilon: entry=int(r()*4)
            else:
                choices=[i for i,x in enumerate(scores) if x==max(scores)]
                entry=choices[int(r()*len(choices))]
        elif agent=='random' or explore<c.epsilon: entry=int(choice*4)
        else:
            choices=[i for i,x in enumerate(scores) if x==max(scores)]
            entry=choices[int(choice*len(choices))]
        trapped=active==entry; hit=not trapped and entry==target
        feedback='decoy' if trapped else 'target' if hit else 'hint' if (r() if legacy else noise)<c.hint else 'empty'
        reward={'decoy':-1.2,'target':3,'hint':.35,'empty':-.18}[feedback]
        if agent=='learning': scores[entry]=max(-3,min(4,scores[entry]+c.learning_rate*(reward-scores[entry])))
        # Nominal model is frozen at v1.2 parameters, even in held-out conditions.
        estimate[entry]=max(-3,min(4,estimate[entry]+.48*(reward-estimate[entry])))
        lures+=trapped; history.append((entry,feedback))
        if trace: steps.append(dict(entry=entry,decoy=active,feedback=feedback,scores=scores.copy()))
        if hit: success=True; break
    return dict(success=success,decoys=lures,moves=moves,turns=len(history),steps=steps)

def wilson(k,n):
    z=1.959963984540054; p=k/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]

def paired_ci(deltas):
    n=len(deltas); mean=sum(deltas)/n
    se=math.sqrt(sum((x-mean)**2 for x in deltas)/(n-1)/n)
    return [mean-1.959963984540054*se,mean+1.959963984540054*se]
