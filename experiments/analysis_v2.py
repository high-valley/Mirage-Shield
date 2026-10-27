"""Exact small-state benchmark for an independent, uniformly random explorer."""
from fractions import Fraction
from functools import lru_cache

@lru_cache(None)
def optimal_random_reach(possible,turns):
    """Bayesian DP: static uniform target, perfect decoy, no switching outage.

    State is the number of entrances still possibly containing the target.
    Any hint/empty from an unprotected entrance excludes it exactly.
    Defender can protect a possible entrance or a known-safe one (if available).
    Return minimum probability of reaching the target within remaining turns.
    """
    if not 1<=possible<=4 or turns<0:raise ValueError('state')
    if not turns or possible==1:return Fraction(0)
    k=possible
    keep=Fraction(5-k,4)*optimal_random_reach(k,turns-1)
    eliminate=Fraction((k-1)**2,4*k)*optimal_random_reach(k-1,turns-1)
    hit=Fraction(k-1,4*k)
    protect_possible=keep+eliminate+hit
    if k==4:return protect_possible
    protect_safe=(Fraction(4-k,4)*optimal_random_reach(k,turns-1)
                  +Fraction(k-1,4)*optimal_random_reach(k-1,turns-1)+Fraction(1,4))
    return min(protect_possible,protect_safe)

if __name__=='__main__':
    t=16;fixed=Fraction(3,4)*(1-Fraction(3,4)**t)
    print('uniform random, 16 turns: exact fixed=',float(fixed),'optimal=',float(optimal_random_reach(4,t)))
