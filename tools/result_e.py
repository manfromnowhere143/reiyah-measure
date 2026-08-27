"""Result E: is the measured dependence real, or is it shared scene difficulty?

Result D reports a marginal lift of c = 1.59 at score >= 0.3. That number is
attackable, and the attack is obvious: range, occlusion and object size make an
object hard for BOTH channels at once. Two detectors failing on the same hard
objects would produce marginal association with no interesting common cause.

This is the test that decides whether Result D survives. We stratify on the
observable difficulty covariates and ask whether dependence remains WITHIN
strata.

Two estimators, because they answer slightly different questions:

  c_stratified   sum of observed joint misses across strata, over the sum of
                 within-stratum expected joint misses. This is the direct
                 analogue of the RSS lift, pooled correctly. It is the number
                 that belongs against Corollary 3.

  MH odds ratio  Mantel-Haenszel common odds ratio, the standard tool for
                 conditional association in stratified 2x2 tables, with the
                 CMH chi-square test of the null of conditional independence.

Strata: class x range band x annotated camera visibility. Thin strata are kept
visible and excluded from the extremum rather than silently dropped.

Usage: python3 tools/result_e.py gt_val_cache.json matched_mapillary.json matched_megvii.json
"""
import json
import math
import sys
from collections import defaultdict

THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5]
MIN_STRATUM = 30

gt = json.load(open(sys.argv[1]))
cam_raw = json.load(open(sys.argv[2]))["matched_at_2m"]
lid_raw = json.load(open(sys.argv[3]))["matched_at_2m"]
cam = {}
lid = {}
for src, dst in ((cam_raw, cam), (lid_raw, lid)):
    for _c, m in src.items():
        for k, v in m.items():
            dst[int(k)] = v


def band(d):
    return "0-20" if d < 20 else ("20-30" if d < 30 else ("30-40" if d < 40 else "40-50"))


def analyse(pool, thr, key_fn, label):
    """Stratified analysis over `pool` at score threshold `thr`."""
    cells = defaultdict(lambda: [0, 0, 0, 0])   # a=both miss, b=cam miss only,
    for i in pool:                              # c=lid miss only, d=neither miss
        cm = cam.get(i, -1.0) < thr
        lm = lid.get(i, -1.0) < thr
        k = key_fn(gt[i])
        if cm and lm:
            cells[k][0] += 1
        elif cm:
            cells[k][1] += 1
        elif lm:
            cells[k][2] += 1
        else:
            cells[k][3] += 1

    obs = exp = 0.0
    mh_num = mh_den = 0.0
    chi_num = chi_var = 0.0
    used = dropped = 0
    for k, (a, b, c, d) in cells.items():
        n = a + b + c + d
        if n < MIN_STRATUM:
            dropped += n
            continue
        used += n
        cam_miss = (a + b) / n
        lid_miss = (a + c) / n
        obs += a
        exp += cam_miss * lid_miss * n
        mh_num += a * d / n
        mh_den += b * c / n
        e_a = (a + b) * (a + c) / n
        chi_num += a - e_a
        if n > 1:
            chi_var += ((a + b) * (c + d) * (a + c) * (b + d)) / (n * n * (n - 1))

    c_strat = obs / exp if exp > 0 else float("nan")
    mh_or = mh_num / mh_den if mh_den > 0 else float("nan")
    cmh = (abs(chi_num) - 0.5) ** 2 / chi_var if chi_var > 0 else float("nan")
    return dict(strata=len(cells), used=used, dropped=dropped, obs=obs, exp=exp,
                c=c_strat, mh_or=mh_or, cmh=cmh)


ALL = list(range(len(gt)))
FULL = ALL
OFFICIAL = [i for i in ALL if gt[i]["nl"] + gt[i]["nr"] > 0]

KEYS = [
    ("class only", lambda g: g["cls"]),
    ("class x range", lambda g: (g["cls"], band(g["dist"]))),
    ("class x range x visibility", lambda g: (g["cls"], band(g["dist"]), g["vis"])),
]

print("=" * 88)
print("RESULT E — does the dependence survive conditioning on scene difficulty?")
print("stratified on observable difficulty covariates; FULL denominator")
print("=" * 88)
print("\nc_strat = sum(observed joint) / sum(within-stratum expected joint)")
print("MH OR   = Mantel-Haenszel common odds ratio; CMH = chi-square, 1 df")
print("null of conditional independence rejected at p<0.001 when CMH > 10.83\n")

for label, fn in KEYS:
    print(f"### stratified by {label}")
    print(f"{'thr':>5}{'strata':>8}{'N used':>10}{'N thin':>8}"
          f"{'obs joint':>11}{'exp joint':>11}{'c_strat':>10}{'MH OR':>9}{'CMH':>12}")
    for thr in THRESHOLDS:
        r = analyse(FULL, thr, fn, label)
        print(f"{thr:>5.1f}{r['strata']:>8}{r['used']:>10,}{r['dropped']:>8,}"
              f"{r['obs']:>11,.0f}{r['exp']:>11,.0f}{r['c']:>10.3f}"
              f"{r['mh_or']:>9.3f}{r['cmh']:>12,.0f}")
    print()

print("### marginal vs conditional, at score >= 0.3, FULL denominator")
marg = analyse(FULL, 0.3, lambda g: "all", "unstratified")
cond = analyse(FULL, 0.3, KEYS[2][1], "full")
print(f"  unstratified lift              c = {marg['c']:.3f}")
print(f"  conditioned on class+range+vis c = {cond['c']:.3f}")
drop = 100 * (marg['c'] - cond['c']) / (marg['c'] - 1) if marg['c'] > 1 else float('nan')
print(f"  {drop:.1f}% of the excess over independence is explained by difficulty")
print(f"  residual excess over independence: {100*(cond['c']-1):.1f}%")

print("\n" + "-" * 88)
print("If c_strat falls to 1.0, the marginal association in Result D was shared")
print("difficulty and nothing more, and Result D's headline should be withdrawn.")
print("If it stays above 1.0 with a large CMH statistic, the two channels fail")
print("together beyond what their common inputs explain, and RSS Definition 32's")
print("independence assumption fails on evidence rather than on argument.")
print("-" * 88)
