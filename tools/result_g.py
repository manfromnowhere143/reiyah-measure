"""Result G: what the measured coefficient actually costs, in evidence.

Two errors of ours to fix, both in how the number is USED rather than how it
was computed.

ERROR ONE: which coefficient belongs in Corollary 3.

Result E concluded "quote 1.16, not 1.59". That is wrong for this purpose.
RSS Corollary 3 bounds the SYSTEM-LEVEL probability of a safety-critical
mistake, integrated over the operating distribution. A deployed vehicle does
not condition on range; objects arrive at whatever range they arrive at. The
quantity that enters the bound is therefore the MARGINAL lift.

The conditional lift is still worth having. It answers a different question --
whether the channels fail together beyond what shared observable difficulty
explains -- and 73% of the marginal excess turning out to be difficulty is a
real finding about mechanism. It is just not the number Corollary 3 consumes.

ERROR TWO: how a change in c propagates to required evidence.

Saying "c = 1.587, so the reduction is overstated by 59%" treats the evidence
requirement as linear in c. It is not.

    P[safety-critical mistake]  <=  6 c p^2

To hit a target P with coefficient c you need per-subsystem error rate

    p = sqrt( P / (6c) )

and validating a subsystem to error rate p takes on the order of 1/p examples.
So required evidence scales as

    N  ~  1/p  =  sqrt( 6c / P )        i.e.  N  proportional to  sqrt(c)

The cost of dependence is the SQUARE ROOT of the lift, not the lift.
"""
import math

TARGET = 1e-9          # RSS's worked example: 10^-9 per hour
MARGINAL = {0.1: 2.271, 0.2: 1.878, 0.3: 1.587, 0.4: 1.363, 0.5: 1.239}
CONDITIONAL = {0.1: 1.365, 0.2: 1.245, 0.3: 1.156, 0.4: 1.091, 0.5: 1.052}


def n_examples(c, target=TARGET):
    """Order-of-magnitude examples per subsystem to license the bound."""
    p = math.sqrt(target / (6.0 * c))
    return 1.0 / p


base = n_examples(1.0)
print("=" * 86)
print("RESULT G — the evidence cost of the measured dependence")
print("RSS Corollary 3:  P <= 6 c p^2   ->   N ~ sqrt(6c/P)   ->   N proportional to sqrt(c)")
print("=" * 86)
print(f"\nRSS's own worked example, target P = 1e-9, assuming independence (c = 1):")
print(f"  examples per subsystem = {base:,.0f}   (the paper says 'order of 10^5')")

print(f"\n{'score':>6}{'marginal c':>12}{'N required':>14}{'vs c=1':>10}"
      f"{'extra evidence':>16}")
for thr in sorted(MARGINAL):
    c = MARGINAL[thr]
    n = n_examples(c)
    print(f"{thr:>6.1f}{c:>12.3f}{n:>14,.0f}{n/base:>10.3f}{100*(n/base-1):>15.1f}%")

print(f"\nFor comparison, the CONDITIONAL coefficient (Result E). This is not the")
print(f"quantity Corollary 3 consumes, but it bounds how much of the cost is")
print(f"attributable to dependence beyond observable difficulty:")
print(f"\n{'score':>6}{'cond. c':>12}{'N required':>14}{'vs c=1':>10}{'extra evidence':>16}")
for thr in sorted(CONDITIONAL):
    c = CONDITIONAL[thr]
    n = n_examples(c)
    print(f"{thr:>6.1f}{c:>12.3f}{n:>14,.0f}{n/base:>10.3f}{100*(n/base-1):>15.1f}%")

print("\n" + "-" * 86)
c3 = MARGINAL[0.3]
print(f"At a representative operating point (score >= 0.3), the measured marginal")
print(f"lift is {c3:.3f}. Because required evidence scales as sqrt(c), that is")
print(f"{math.sqrt(c3):.3f}x more examples per subsystem, or {100*(math.sqrt(c3)-1):.0f}% more --")
print(f"not the {100*(c3-1):.0f}% a linear reading would suggest.")
print()
print("This is a SMALLER consequence than we implied two results ago, and it is")
print("the correct one. Corollary 3's shortcut is not destroyed by the measured")
print("dependence. It is understated by about a quarter.")
print()
print("Whether a quarter matters is an engineering judgement, not a statistical")
print("one. At RSS's own worked target it is the difference between roughly")
print(f"{base:,.0f} and {n_examples(c3):,.0f} examples per subsystem.")
print("-" * 86)
