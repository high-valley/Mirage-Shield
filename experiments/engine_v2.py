"""Second, isolated research model: independent streams, shuffled labels, public-only defenders."""
from dataclasses import dataclass
import hashlib
import math
import random

POLICIES=('none','fixed_A','fixed_B','fixed_C','fixed_D','fixed_anchor','risk','predictive','belief','gated','robust')
AGENTS=('random','learning','sweep','persistent','reverse','switching')
REWARD={'decoy':-1.2,'hint':.35,'empty':-.18,'target':3.}

@dataclass(frozen=True)
class Config:
    weights: tuple=(1.,1.,1.,1.)
    budget: int=16
    hint: float=.24
    epsilon: float=.16
    learning_rate: float=.48
    switch_delay: int=0
    linked: bool=False
    shuffle_labels: bool=True
    stream: str='mt19937'
    def __post_init__(self):
        if len(self.weights)!=4 or any(not math.isfinite(x) or x<=0 for x in self.weights): raise ValueError('weights')
        if type(self.budget)!=int or self.budget<1: raise ValueError('budget')
        if type(self.switch_delay)!=int or self.switch_delay<0: raise ValueError('switch_delay')
        if any(not math.isfinite(v) or not 0<=v<=1 for v in (self.hint,self.epsilon,self.learning_rate)): raise ValueError('probability')
        if self.stream not in ('mt19937','sha256'): raise ValueError('stream')

class HashRandom:
    """Counter-based SHA-256 stream, for sensitivity checking against MT19937."""
    def __init__(self,key): self.key=key; self.counter=0
    def random(self):
        value=hashlib.sha256(self.key+self.counter.to_bytes(8,'big')).digest()
        self.counter+=1
        return (int.from_bytes(value[:8],'big')>>11)/(1<<53)

def stream(seed,purpose,family='mt19937'):
    key=hashlib.sha256(f'mirage-v2:{seed}:{purpose}'.encode()).digest()
    return random.Random(int.from_bytes(key,'big')) if family=='mt19937' else HashRandom(key)

def shuffle(values,r):
    values=list(values)
    for i in range(len(values)-1,0,-1):
        j=int(r.random()*(i+1)); values[i],values[j]=values[j],values[i]
    return values

def weighted(u,weights):
    x=u*sum(weights)
    for i,w in enumerate(weights):
        x-=w
        if x<0:return i
    return len(weights)-1

@dataclass(frozen=True)
class World:
    target: int
    importance: tuple
    anchor: int
    offset: int
    labels: tuple
    draws: tuple

def make_world(seed,c):
    labels=tuple(shuffle(range(4),stream(seed,'labels',c.stream))) if c.shuffle_labels else tuple(range(4))
    importance=tuple(shuffle((1,2,3,4),stream(seed,'importance',c.stream)))
    prior=importance if c.linked else c.weights
    target=weighted(stream(seed,'target',c.stream).random(),prior)
    anchor=labels[int(stream(seed,'anchor',c.stream).random()*4)]
    offset=int(stream(seed,'agent_offset',c.stream).random()*4)
    channels=[stream(seed,name,c.stream) for name in ('explore','choice','noise')]
    draws=tuple(tuple(r.random() for r in channels) for _ in range(c.budget))
    physical_importance=[0]*4
    for i,label in enumerate(labels):physical_importance[label]=importance[i]
    return World(labels[target],tuple(physical_importance),anchor,offset,labels,draws)

@dataclass(frozen=True)
class Public:
    """Only permitted inputs to defenses. No seed, target, agent type or future draws."""
    anchor: int
    importance: tuple
    labels: tuple
    switch_delay: int

class Defender:
    def __init__(self,policy,public,threshold=.9):
        if policy not in POLICIES: raise ValueError('policy')
        self.policy=policy; self.public=public; self.threshold=threshold
        self.current=public.anchor; self.scores=[0.]*4; self.possible=[True]*4
        self.history=[]
        # Mixture of memoryless random, nominal learner and all cyclic/block offsets.
        self.models=[('random',0),('learning',0)]+[(kind,offset) for kind in ('cycle','block') for offset in range(4)]
        self.mass=[.4,.4]+[.025]*8

    def probabilities(self,model):
        kind,offset=model; t=len(self.history); order=self.public.labels
        if kind=='random':return [.25]*4
        if kind=='learning':
            top=max(self.scores); best=[i for i,v in enumerate(self.scores) if abs(v-top)<1e-12]
            return [.16/4+(.84/len(best) if i in best else 0) for i in range(4)]
        p=[0.]*4; p[order[(offset+(t if kind=='cycle' else t//4))%4]]=1.
        return p

    def choose(self):
        p=self.policy; public=self.public
        if p=='none': return -1
        if p.startswith('fixed_') and p!='fixed_anchor':return 'ABCD'.index(p[-1])
        if p=='fixed_anchor':return public.anchor
        if p=='risk':return max(public.labels,key=lambda i:public.importance[i])
        order=public.labels
        if p=='predictive':
            best=max(order,key=lambda i:self.scores[i])
            return best if self.scores[best]-self.scores[public.anchor]>.1 else public.anchor
        # Empty/hint is an exact negative in this toy model. Never infer exclusion from a decoy.
        belief=[float(x) for x in self.possible]
        if p in ('belief','robust') and (p=='belief' or self.mass[1]>=self.threshold):
            if public.switch_delay:return public.anchor
            top=max(self.scores); choices=[i for i in order if abs(self.scores[i]-top)<1e-12]
            prediction=[.04+(.84/len(choices) if i in choices else 0) for i in range(4)]
        else:
            # If switching incurs outage, retain anchor; no free instantaneous moves assumed.
            if public.switch_delay:return public.anchor
            certainty=sum(w for w,m in zip(self.mass,self.models) if m[0] in ('cycle','block'))
            if certainty<self.threshold or len(self.history)<2:return public.anchor
            prediction=[0.]*4
            for weight,model in zip(self.mass,self.models):
                for i,value in enumerate(self.probabilities(model)):prediction[i]+=weight*value
        value=[belief[i]*prediction[i] for i in range(4)]
        best=max([self.current]+[i for i in order if i!=self.current],key=lambda i:value[i])
        if value[best]>value[self.current]+1e-12:self.current=best
        return self.current

    def observe(self,entry,feedback):
        if self.policy not in ('predictive','belief','gated','robust'):return
        if feedback in ('empty','hint'):self.possible[entry]=False
        if self.policy in ('gated','robust'):
            likelihood=[w*self.probabilities(m)[entry] for w,m in zip(self.mass,self.models)]
            total=sum(likelihood)
            self.mass=[w/total for w in likelihood] if total else [.1]*10
        self.scores[entry]+=.48*(REWARD[feedback]-self.scores[entry])
        self.history.append((entry,feedback))

def run(seed,policy,agent,c=Config(),threshold=.9,trace=False,world=None):
    if agent not in AGENTS:raise ValueError('agent')
    world=make_world(seed,c) if world is None else world
    defender=Defender(policy,Public(world.anchor,world.importance,world.labels,c.switch_delay),threshold)
    scores=[0.]*4; moves=decoys=0; previous=-1; cooldown=0; steps=[]
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
        feedback='target' if hit else 'decoy' if trapped else 'hint' if noise<c.hint else 'empty'
        if agent=='learning':scores[entry]+=c.learning_rate*(REWARD[feedback]-scores[entry])
        defender.observe(entry,feedback);decoys+=trapped
        if trace:steps.append(dict(entry=entry,decoy=active,feedback=feedback,desired=desired,possible=list(defender.possible)))
        if hit:return dict(success=True,moves=moves,decoys=decoys,turns=t+1,steps=steps)
    return dict(success=False,moves=moves,decoys=decoys,turns=c.budget,steps=steps)
